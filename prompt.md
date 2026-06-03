# TFG — Control System Health Status
# Project prompt for AI coding agents (OpenCode / Claude Code)

## What this project is

Industrial infrastructure health monitoring system. Agents collect metrics from Windows servers, VMware ESXi hosts, VMs, and industrial PLCs (Siemens, Rockwell). Data flows into InfluxDB and is visualised in Grafana. Targets are managed dynamically via a REST API + Web UI — no restarts needed.

**Repo:** https://github.com/AlexchMsi/TFG-Health-Control  
**Branch:** `develop` (main = stable releases)  
**Author:** Alex Cheng

---

## Stack

| Layer | Technology |
|---|---|
| Time-series DB | InfluxDB 2.7 |
| Dashboards | Grafana 10.4 |
| API | FastAPI + SQLite (SQLModel) |
| Agents | Python 3.12 |
| Infra | Docker Compose |

Services: InfluxDB `:8086`, Grafana `:3000`, API `:8000` (Swagger at `/docs`), Web UI at `/ui`

---

## Quick start

```bash
cp .env.example .env
docker compose up influxdb -d   # wait ~15s
docker compose up -d
# UI → http://localhost:8000/ui
# Grafana → http://localhost:3000
```

---

## Architecture — data flow

```
Target → Collector.collect() → *Metric dataclass → AgentScheduler → InfluxWriter.write_point() → InfluxDB
```

**Never pass raw dicts between collector and writer.** The `*Metric` dataclass is the contract.

---

## Shared library (`shared/`)

Installed as editable package (`pip install -e shared/`) in every container and locally.

- `shared/influx/writer.py` — `InfluxWriter` is the **only** place that writes to InfluxDB. Uses `WritePrecision.S`. **Never use `WritePrecision.SECONDS`** — it does not exist.
- `shared/models/` — `BaseMetric` subclasses: `WindowsServerMetric`, `ESXiHostMetric`, `VMMetric`, `SiemensPlcMetric`. Always dataclasses, never dicts.
- `shared/config/settings.py` — `Settings` (Pydantic BaseSettings, reads `.env`).
- `shared/config/poller.py` — `ConfigPoller`: polls `/config/targets?agent_type=<type>` every 30s, dynamically adds/removes APScheduler jobs.
- `shared/utils/logging.py` — `configure_logging(level)`: call first in every `main()`.

---

## Dynamic target management

1. `POST /config/targets` registers a target in SQLite
2. `ConfigPoller` inside each agent detects it within ≤30s
3. APScheduler job created — collection starts immediately
4. `DELETE /config/targets/{id}` stops collection within one poll cycle

All agents use `BackgroundScheduler` + `ConfigPoller`. No static config files.

---

## Agent pattern (apply to every agent)

```
agents/<name>/
  src/
    main.py        # Settings → configure_logging → InfluxWriter → AgentScheduler → ConfigPoller.start() → block
    scheduler.py   # add_target(dict) / remove_target(str) / .aps property (BackgroundScheduler)
    collectors/    # one class per protocol — collect() NEVER raises, always returns metric with reachable=False on error
  requirements.txt
  Dockerfile
```

`AgentScheduler.add_target` must use `replace_existing=True` and `max_instances=1`.  
`ConfigPoller` constructor requires both `scheduler=` (domain object) and `aps_scheduler=scheduler.aps` (raw APScheduler).

---

## Agents

### server-agent (`agent_type="server"`)
Collects from Windows servers and VMware. `collection_method` determines which collector is used:

| method | class | protocol |
|---|---|---|
| `snmp` | `WindowsSNMPCollector` | SNMPv2c HOST-RESOURCES-MIB |
| `winrm` | `WindowsWinRMCollector` | WinRM + PowerShell |
| `vmware` | `VMwareCollector` | pyVmomi vSphere API |

**SNMP library pinning (critical):** `pysnmp-lextudio==5.0.34` + `pyasn1==0.5.1`. Do NOT upgrade — v6 removed the sync hlapi API, pyasn1 v0.6 removed `pyasn1.compat.octets`.

VMwareCollector config keys: `host`, `user`, `password`, `ignore_ssl` (bool), `collect_hosts` (bool), `collect_vms` (bool).

### siemens-agent (`agent_type="siemens"`)
PLCs Siemens. `collection_method`: `"opcua"` | `"snap7"` | `"auto"` (OPC UA first, Snap7 fallback).

| method | library | port |
|---|---|---|
| opcua | asyncua 1.0.6 | 4840 |
| snap7 | python-snap7 1.3 | 102 |

### rockwell-agent (`agent_type="rockwell"`) — Phase 3, not yet implemented
Library: `pylogix==0.9.3`

### network-agent (`agent_type="network"`) — Phase 4, not yet implemented
Library: `pysnmp`, `scapy==2.5.0`. Needs `NET_BROADCAST` Docker capability for Profinet DCP multicast.

---

## InfluxDB measurements schema

| Measurement | Key tags | Key fields |
|---|---|---|
| `server_health` | source_id, hostname, collection_method | cpu_usage_percent, ram_usage_percent, ram_total_gb, reachable |
| `disk_health` | source_id, drive_letter | total_gb, used_gb, usage_percent |
| `service_health` | source_id, service_name | state (str), is_running (int) |
| `esxi_health` | source_id, hostname, version | cpu_usage_percent, ram_usage_percent, num_vms, maintenance_mode |
| `vm_health` | source_id, vm_name, esxi_host, guest_os | power_state, cpu_usage_mhz, ram_usage_mb, num_snapshots |
| `siemens_plc_health` | source_id, plc_name, plant, collection_method | cpu_state, load_memory_used_percent, reachable |

`reachable` is always `int(bool)` — never a Python bool.

---

## API (`api/src/`)

- `main.py` — lifespan: `create_db_and_tables()` → `InfluxDBClient` in `app.state.influx`
- `database.py` — SQLite engine, `get_session()` dependency
- `models/target.py` — `Target` SQLModel table + `TargetCreate/Update/Read` schemas
- `routers/config.py` — CRUD `/config/targets`
- `routers/servers.py`, `vmware.py`, `plcs.py` — metric query endpoints
- `services/influx_query.py` — all Flux queries. **Never put Flux strings in routers.**
- `static/index.html` — Web UI (Tailwind CSS, vanilla JS, no build step)

Flux range windows: `-10m` for servers, `-15m` for VMware and PLCs.

---

## Web UI (`/ui`)

Single HTML file at `api/src/static/index.html`. Supports adding targets of type `server` (SNMP / WinRM / VMware) and `siemens`. Form fields change dynamically based on selected type and method.

---

## Grafana

Dashboards auto-provisioned from `infra/grafana/dashboards/*.json`.  
Every dashboard JSON must use `"${DS_INFLUXDB}"` as datasource uid.

Grafana password is set only on **first volume init** — `GF_SECURITY_ADMIN_PASSWORD` is ignored on restart. To reset: `docker rm -f grafana && docker volume rm ftg_grafana_data && docker compose up grafana -d`

---

## Adding a new agent (checklist)

1. `agents/<name>/` with `Dockerfile`, `requirements.txt`, `src/`
2. Add `*Metric` model to `shared/models/` if needed
3. Collectors: `collect()` never raises — catch all, return metric with `reachable=False`
4. `AgentScheduler`: `add_target` / `remove_target` / `.aps` property, `BackgroundScheduler`
5. `main.py`: `ConfigPoller(agent_type="<name>", scheduler=..., aps_scheduler=scheduler.aps)`
6. Add service block to `docker-compose.yml`
7. Add dashboard JSON to `infra/grafana/dashboards/`
8. Add agent type option to `api/src/static/index.html` UI

---

## Known gotchas

- `host.docker.internal` in Docker on Windows resolves to `192.168.65.254` — Windows SNMP does NOT listen there. Use the LAN IP.
- Docker containers cannot reach VMware Bridged VMs on the same Windows host (hairpin routing blocked by Windows). Non-issue in production with a dedicated monitoring server.
- SNMP on Windows Server needs `Install-WindowsFeature -Name SNMP-Service` (not `Add-WindowsCapability`). May require reboot.
- VMnet0 Bridged on Windows with multiple virtual adapters (Docker, Hyper-V, VPN) may get APIPA — fix by manually selecting the physical adapter in Virtual Network Editor.
- `pysnmp-lextudio` and `pyasn1` versions are pinned — do not upgrade.

---

## Phase status

| Phase | Agent | Status |
|---|---|---|
| 1 | server-agent (SNMP, WinRM, VMware) | Developed — pending production validation |
| 2 | siemens-agent (OPC UA, Snap7) | Developed — pending hardware tests |
| 3 | rockwell-agent (pylogix) | Next |
| 4 | network-agent (pysnmp, scapy) | Planned |
| 5 | Alerting + reporting | Planned |
