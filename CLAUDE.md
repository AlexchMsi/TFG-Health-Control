# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- **Infra:** Docker Compose — InfluxDB 2.7, Grafana 10.4, Python agents, FastAPI
- **Storage:** InfluxDB (time-series). Measurements: `server_health`, `disk_health`, `service_health`, `esxi_health`, `vm_health`, `siemens_plc_health`
- **Config store:** SQLite (`data/config.db`) via SQLModel — CRUD for monitoring targets (NOT time-series)
- **API:** FastAPI (`api/`), queries InfluxDB via Flux language + manages targets via SQLite
- **Dashboards:** Grafana auto-provisioned from `infra/grafana/provisioning/` and `infra/grafana/dashboards/`

## Running the stack

```bash
cp .env.example .env          # configure credentials
docker compose up influxdb grafana          # infra only (first run)
docker compose up -d                        # full stack
python scripts/test_connectivity.py        # pre-flight check for all targets
```

Services: InfluxDB → `:8086`, Grafana → `:3000`, API → `:8000`

## Running agents/API locally (outside Docker)

```bash
# server-agent (Phase 1 — static YAML config)
cd agents/server-agent
pip install -r requirements.txt
pip install -e ../../shared
python -m src.main

# siemens-agent (Phase 2 — dynamic config via API)
cd agents/siemens-agent
pip install -r requirements.txt
pip install -e ../../shared
API_URL=http://localhost:8000 python -m src.main

# API
cd api
pip install -r requirements.txt
pip install -e ../shared
uvicorn src.main:app --reload --port 8000
```

## Architecture

### Shared library (`shared/`)
Installed as an editable package (`pip install -e`) inside every container and local dev environment. Contains:
- `shared/influx/writer.py` — `InfluxWriter`: the only place that writes to InfluxDB. Uses `SYNCHRONOUS` mode so write errors surface immediately.
- `shared/models/` — dataclasses: `BaseMetric` → `WindowsServerMetric`, `ESXiHostMetric`, `VMMetric`, `SiemensPlcMetric`
- `shared/config/settings.py` — `Settings` (Pydantic BaseSettings, reads `.env`)
- `shared/config/poller.py` — `ConfigPoller`: polls `/config/targets?agent_type=<type>` every 30 s, dynamically adds/removes APScheduler jobs

### Dynamic configuration (Phase 2+)
Agents no longer read a static `targets.yaml`. Instead:
1. `POST /config/targets` (from Codex or curl) registers a new target in SQLite
2. `ConfigPoller` inside each agent detects the new target within ≤30 s
3. A new APScheduler job is created — collection starts immediately
4. `DELETE /config/targets/{id}` stops collection within one poll cycle

Config endpoints:
- `POST   /config/targets` — register target
- `GET    /config/targets?agent_type=siemens` — list (agents poll this)
- `GET    /config/targets/{id}` — get one
- `PUT    /config/targets/{id}` — update config / enable / disable
- `DELETE /config/targets/{id}` — remove

SQLite file: `data/config.db` (mounted as Docker volume `./data:/app/data`).

### Agents (`agents/<name>/`)
Each agent is a stateless Docker container: **poll → normalize → write to InfluxDB**.

- Entry point: `src/main.py` → builds `InfluxWriter` + `AgentScheduler` + `ConfigPoller`
- `src/scheduler.py` — `add_target(target)` / `remove_target(id)` API used by ConfigPoller. Key constraints: `max_instances=1` (no overlap), `jitter=5`
- `src/collectors/` — one class per protocol. **`collect()` must never raise** — on failure return a metric with `reachable=False`

**server-agent collectors (Phase 1 — static YAML):**
| File | Protocol | Use case |
|---|---|---|
| `windows_snmp.py` | SNMPv2c / HOST-RESOURCES-MIB | Primary Windows path — no agent required on target |
| `windows_winrm.py` | WinRM + PowerShell | Enhanced path — service status, NTP offset |
| `vmware.py` | pyVmomi / vSphere API | ESXi hosts + VMs + snapshots |

**siemens-agent collectors (Phase 2 — dynamic config):**
| File | Protocol | Use case |
|---|---|---|
| `opcua_collector.py` | OPC UA (asyncua) | Primary path — Ignition, WinCC, S7-1500 native |
| `snap7_collector.py` | S7Comm port 102 (python-snap7) | Fallback path — SZL reads, no DB tags needed |

Collection method selection (per target `config.collection_method`):
- `"opcua"` — OPC UA only
- `"snap7"` — Snap7 only
- `"auto"` — try OPC UA first, fall back to Snap7 if unreachable

### API (`api/src/`)
- `main.py` — FastAPI app with lifespan; stores `InfluxDBClient` in `app.state.influx`; calls `create_db_and_tables()` on startup
- `database.py` — SQLite engine (`data/config.db`), `get_session()` dependency
- `models/target.py` — `Target` SQLModel table + `TargetCreate` / `TargetUpdate` / `TargetRead` schemas
- `routers/config.py` — CRUD for `/config/targets`
- `routers/plcs.py` — `GET /metrics/plcs/siemens`
- `services/influx_query.py` — all Flux queries. Uses `pivot()` to reshape time-series into row-per-asset format

### Grafana provisioning
- Datasource and dashboard providers are loaded automatically on container start from `infra/grafana/provisioning/`
- Dashboard JSON files live in `infra/grafana/dashboards/`. The `${DS_INFLUXDB}` template variable must be present in every dashboard JSON.

## Adding a new agent (Phase 3+)

1. Create `agents/<name>/` with `Dockerfile`, `requirements.txt`, `src/`
2. Add models to `shared/models/` if needed
3. Implement collectors — `collect()` never raises
4. Implement `AgentScheduler` with `add_target()` / `remove_target()` methods
5. Instantiate `ConfigPoller` in `src/main.py` with `agent_type="<name>"`
6. Uncomment the service block in `docker-compose.yml`
7. Add a Grafana dashboard JSON to `infra/grafana/dashboards/`

## Planned phases

| Phase | Agent | Key libraries |
|---|---|---|
| 2 | `siemens-agent` | `asyncua==1.0.6`, `python-snap7==1.3` — DONE |
| 3 | `rockwell-agent` | `pylogix==0.9.3` |
| 4 | `network-agent` | `pysnmp`, `scapy==2.5.0` — needs `NET_BROADCAST` Docker capability for Profinet DCP multicast |
| 5 | Alerting + reporting | Grafana Alerting → email/Teams, `weasyprint` for PDF, `/export/report` FastAPI endpoint |
