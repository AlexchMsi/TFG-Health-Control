# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- **Infra:** Docker Compose — InfluxDB 2.7, Grafana 10.4, Python agents, FastAPI
- **Storage:** InfluxDB (time-series). Measurements: `server_health`, `disk_health`, `service_health`, `esxi_health`, `vm_health`, `siemens_plc_health`
- **Config store:** SQLite (`data/config.db`) via SQLModel — CRUD for monitoring targets (NOT time-series)
- **API:** FastAPI (`api/`), queries InfluxDB via Flux language + manages targets via SQLite
- **Dashboards:** Grafana auto-provisioned from `infra/grafana/provisioning/` and `infra/grafana/dashboards/`

## Common commands

```bash
# Stack
cp .env.example .env
docker compose up influxdb grafana -d      # infra only (first run, wait ~15s)
docker compose up -d                       # full stack
docker compose logs -f server-agent        # tail agent logs
docker compose build server-agent          # rebuild one image after code change

# Pre-flight checks
python scripts/test_connectivity.py        # TCP/DNS reachability for all targets
python scripts/discover_opcua.py --host 10.0.0.1 --port 4840
python scripts/discover_snap7.py --host 10.0.0.1 --rack 0 --slot 1

# Run agents/API locally (outside Docker)
cd agents/server-agent && pip install -e ../../shared && pip install -r requirements.txt
python -m src.main

cd agents/siemens-agent && pip install -e ../../shared && pip install -r requirements.txt
API_URL=http://localhost:8000 python -m src.main   # must set API_URL — default is http://api:8000 (Docker hostname)

cd api && pip install -e ../shared && pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000

# Add a monitoring target at runtime (no restart needed)
curl -X POST http://localhost:8000/config/targets \
  -H "Content-Type: application/json" \
  -d '{"id":"planta-a-plc-01","plant":"Valencia","agent_type":"siemens","display_name":"PLC L1","config":{"collection_method":"auto","opcua_url":"opc.tcp://10.0.0.1:4840","snap7_host":"10.0.0.1","snap7_rack":0,"snap7_slot":1}}'
```

Services: InfluxDB → `:8086`, Grafana → `:3000`, API → `:8000` (Swagger at `/docs`)

## Architecture

### Data flow

```
Target (IP/protocol) → Collector.collect() → *Metric dataclass → AgentScheduler._write() → InfluxWriter.write_point() → InfluxDB
```

Every agent follows this exact pattern. The `*Metric` dataclass is the contract between collector and writer — no raw dicts passed between them.

### Shared library (`shared/`)
Installed as an editable package (`pip install -e`) inside every container and locally. Key invariants:
- `shared/influx/writer.py` — `InfluxWriter` is the **only** place that writes to InfluxDB. Uses `SYNCHRONOUS` write mode and `WritePrecision.S` (seconds). **Do not use `WritePrecision.SECONDS`** — that constant does not exist in `influxdb-client`.
- `shared/models/` — `BaseMetric` → `WindowsServerMetric`, `ESXiHostMetric`, `VMMetric`, `SiemensPlcMetric`. Always use dataclasses, not dicts.
- `shared/config/settings.py` — `Settings` (Pydantic BaseSettings, reads `.env`). All agents and the API share this.
- `shared/config/poller.py` — `ConfigPoller`: polls `/config/targets?agent_type=<type>` every 30 s, dynamically adds/removes APScheduler jobs.
- `shared/utils/logging.py` — `configure_logging(level)`: call this first in every agent's `main()`. Silences noisy third-party loggers (pysnmp, pyVmomi, urllib3).

### Dynamic configuration (Phase 2+)
Agents no longer read a static `targets.yaml`. Instead:
1. `POST /config/targets` (from Codex or curl) registers a new target in SQLite
2. `ConfigPoller` inside each agent detects the new target within ≤30 s
3. A new APScheduler job is created — collection starts immediately
4. `DELETE /config/targets/{id}` stops collection within one poll cycle

Config endpoints: `POST/GET/PUT/DELETE /config/targets`. SQLite file: `data/config.db` (volume `./data:/app/data`).

### Agents (`agents/<name>/`)
Each agent is a stateless Docker container: **poll → normalize → write to InfluxDB**.

- `src/main.py` — entry point: `Settings()` → `configure_logging()` → `InfluxWriter()` → `AgentScheduler()` → `ConfigPoller.start()` → block on signal
- `src/scheduler.py` — `add_target(target: dict)` / `remove_target(id: str)` API used by ConfigPoller. APScheduler constraints: `max_instances=1` (prevents overlap if collection is slow), `jitter=5`
- `src/collectors/` — one class per protocol. **`collect()` must never raise** — catch all exceptions and return the metric with `reachable=False` and `last_error_text` set.

**server-agent (Phase 1 — static YAML `config/targets.yaml`):**

Uses `BlockingScheduler` — `scheduler.start()` blocks the main thread. Config is loaded once at startup from `/app/config/targets.yaml` (mounted volume); there is no ConfigPoller. `collection_method` per target in YAML selects `WindowsSNMPCollector` or `WindowsWinRMCollector`.

| File | Protocol | Notes |
|---|---|---|
| `windows_snmp.py` | SNMPv2c HOST-RESOURCES-MIB | Primary path — no agent on target |
| `windows_winrm.py` | WinRM + PowerShell | Enhanced path — services + NTP offset |
| `vmware.py` | pyVmomi vSphere API | ESXi hosts + VMs + snapshot DFS |

The SNMP collector does a single `sysUpTime` GET as a fast reachability check before the expensive table walks. If it times out, the collector raises immediately (returning `reachable=False`) instead of waiting through ~12 OID timeouts (~120 s total). The transport is configured with `timeout=5, retries=1`.

**SNMP library pinning (critical):** `pysnmp-lextudio` must stay at **5.x** (currently `5.0.34`) with `pyasn1==0.5.1`. Version 6.x of pysnmp-lextudio dropped the synchronous `hlapi` API (`CommunityData`, `getCmd`, `nextCmd` were removed from `pysnmp.hlapi`). Version 0.6.x of pyasn1 removed `pyasn1.compat.octets` which pysnmp 5.x needs. Do not upgrade either without rewriting the collector to use the async API.

The server-agent Dockerfile does **not** install system SNMP packages (`libsnmp-dev`, `snmpd`). `pysnmp` is pure Python and needs no system dependencies.

**siemens-agent (Phase 2 — dynamic config via API):**

Uses `BackgroundScheduler` (non-blocking), allowing `ConfigPoller` to also register its `_sync` job on the same APScheduler instance. The `_collect` + `_write` logic lives in `AgentScheduler._collect_and_write()`, not in the collectors themselves. `add_job(..., replace_existing=True)` means re-posting the same target ID updates the job in place without error.

`ConfigPoller` requires two constructor args: `scheduler=` (the `AgentScheduler` domain object with `add_target`/`remove_target`) and `aps_scheduler=scheduler.aps` (the raw `BackgroundScheduler` instance exposed via the `.aps` property).

| File | Protocol | Notes |
|---|---|---|
| `opcua_collector.py` | OPC UA (asyncua) | Primary — Ignition, WinCC, S7-1500 native port 4840 |
| `snap7_collector.py` | S7Comm port 102 (python-snap7) | Fallback — SZL reads, no DB tags needed |

`collection_method` per target: `"opcua"` | `"snap7"` | `"auto"` (OPC UA first, then Snap7).

### InfluxDB measurements schema
Tags are low-cardinality identifiers (used for filtering/grouping). Fields are the numeric/string values.

| Measurement | Key tags | Key fields |
|---|---|---|
| `server_health` | source_id, hostname, collection_method | cpu_usage_percent, ram_usage_percent, ram_total_gb, reachable |
| `disk_health` | source_id, drive_letter | total_gb, used_gb, usage_percent |
| `service_health` | source_id, service_name | state (str), is_running (int 0/1) |
| `esxi_health` | source_id, hostname, version | cpu_usage_percent, ram_usage_percent, num_vms, maintenance_mode |
| `vm_health` | source_id, vm_name, esxi_host, guest_os | power_state, cpu_usage_mhz, ram_usage_mb, num_snapshots, oldest_snapshot_age_days |
| `siemens_plc_health` | source_id, plc_name, plant, model, firmware, collection_method | cpu_state (str), cpu_state_code, load_memory_used_percent, work_memory_used_percent, reachable |

`reachable` is always written as `int(bool)` (1/0), never as a Python bool, to satisfy InfluxDB field type consistency.

### API (`api/src/`)
- `main.py` — lifespan: `create_db_and_tables()` (SQLite), then `InfluxDBClient` stored in `app.state.influx`
- `database.py` — SQLite engine, `get_session()` FastAPI dependency
- `models/target.py` — `Target` SQLModel table; `TargetCreate/Update/Read` schemas
- `routers/config.py` — CRUD `/config/targets`
- `routers/servers.py`, `routers/vmware.py`, `routers/plcs.py` — metric query endpoints
- `services/influx_query.py` — all Flux queries. Pattern: `range() → filter() → last() → pivot()` to produce row-per-asset output. Never put Flux strings in routers.

`InfluxQueryService` is instantiated per-request via a `_svc(request)` helper in each router (not a singleton). The Flux `range` window differs by measurement: `-10m` for server queries, `-15m` for VMware and PLC queries — if an agent hasn't written within that window, the `latest` queries return empty.

### Grafana provisioning
Datasource and dashboards auto-load from `infra/grafana/provisioning/` on container start. Dashboard JSON files live in `infra/grafana/dashboards/`. Every dashboard JSON **must** contain `"${DS_INFLUXDB}"` as the datasource uid — Grafana injects the real uid at load time.

### Local development (snmpd-sim)
`docker-compose.yml` includes a `snmpd-sim` service (Alpine + Net-SNMP) that serves as a local SNMP test target on port 1161/udp inside the Docker network. `agents/server-agent/config/targets.yaml` points to `snmpd-sim:1161` for local dev. Linux's `snmpd` does not expose HOST-RESOURCES-MIB CPU/RAM data, so those fields will read 0 — only `reachable=1` and `uptime_seconds` will have real values. This is expected and confirms end-to-end data flow works.

To test against a real Windows target, change `hostname` and `snmp_port: 161` in `targets.yaml`. Windows SNMP service must be enabled (optional feature, requires admin).

## Adding a new agent (Phase 3+)

1. Create `agents/<name>/` with `Dockerfile`, `requirements.txt`, `src/`
2. Add models to `shared/models/` if needed
3. Implement collectors — `collect()` never raises
4. Implement `AgentScheduler` with `add_target(target: dict)` / `remove_target(id: str)`; use `BackgroundScheduler` and expose `.aps` property
5. Instantiate `ConfigPoller` in `src/main.py` with `agent_type="<name>"`, passing both `scheduler=` and `aps_scheduler=scheduler.aps`
6. Uncomment (or add) the service block in `docker-compose.yml`
7. Add a Grafana dashboard JSON to `infra/grafana/dashboards/`

Dockerfile pattern: copy `shared/` → `pip install -e /app/shared/` → copy agent `requirements.txt` → `pip install -r requirements.txt` → copy agent `src/`. No system package installation needed unless the protocol library requires native libs (python-snap7 bundles its own).

## Planned phases

| Phase | Agent | Key libraries |
|---|---|---|
| 2 | `siemens-agent` | `asyncua==1.0.6`, `python-snap7==1.3` — **DONE** |
| 3 | `rockwell-agent` | `pylogix==0.9.3` |
| 4 | `network-agent` | `pysnmp`, `scapy==2.5.0` — needs `NET_BROADCAST` Docker cap for Profinet DCP multicast |
| 5 | Alerting + reporting | Grafana Alerting → email/Teams, `weasyprint` PDF, `/export/report` endpoint |
