# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- **Infra:** Docker Compose — InfluxDB 2.7, Grafana 10.4, Python agents, FastAPI
- **Storage:** InfluxDB (time-series). Measurements: `server_health`, `disk_health`, `service_health`, `esxi_health`, `vm_health`
- **API:** FastAPI (`api/`), queries InfluxDB via Flux language
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
# server-agent
cd agents/server-agent
pip install -r requirements.txt
pip install -e ../../shared
python -m src.main

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
- `shared/models/` — dataclasses: `BaseMetric` → `WindowsServerMetric`, `ESXiHostMetric`, `VMMetric`
- `shared/config/settings.py` — `Settings` (Pydantic BaseSettings, reads `.env`)

### Agents (`agents/<name>/`)
Each agent is a stateless Docker container: **poll → normalize → write to InfluxDB**.

- Entry point: `src/main.py` → builds `InfluxWriter` + `AgentScheduler`
- `src/scheduler.py` — one `APScheduler` job per target in `config/targets.yaml`. Key constraints: `max_instances=1` (no overlap), `jitter=5`
- `src/collectors/` — one class per protocol, all extend `AbstractCollector`. **`collect()` must never raise** — on failure return a metric with `reachable=False`
- Target list and poll intervals configured in `agents/<name>/config/targets.yaml`

**server-agent collectors:**
| File | Protocol | Use case |
|---|---|---|
| `windows_snmp.py` | SNMPv2c / HOST-RESOURCES-MIB | Primary Windows path — no agent required on target |
| `windows_winrm.py` | WinRM + PowerShell | Enhanced path — service status, NTP offset |
| `vmware.py` | pyVmomi / vSphere API | ESXi hosts + VMs + snapshots |

### API (`api/src/`)
- `main.py` — FastAPI app with lifespan; stores `InfluxDBClient` in `app.state.influx`
- `routers/` — thin HTTP layer, delegates to `services/influx_query.py`
- `services/influx_query.py` — all Flux queries. Uses `pivot()` to reshape time-series into row-per-asset format for REST responses

### Grafana provisioning
- Datasource and dashboard providers are loaded automatically on container start from `infra/grafana/provisioning/`
- Dashboard JSON files live in `infra/grafana/dashboards/`. The `${DS_INFLUXDB}` template variable must be present in every dashboard JSON.

## Adding a new agent (Phase 2+)

1. Create `agents/<name>/` with `Dockerfile`, `requirements.txt`, `config/targets.yaml`, `src/`
2. Add models to `shared/models/` if needed
3. Implement collector extending `AbstractCollector` — `collect()` never raises
4. Add write logic in scheduler (pattern: tags = low-cardinality identifiers, fields = numeric/string values)
5. Uncomment the service block in `docker-compose.yml`
6. Add a Grafana dashboard JSON to `infra/grafana/dashboards/`

## Planned phases

| Phase | Agent | Key libraries |
|---|---|---|
| 2 | `siemens-agent` | `asyncua==1.0.6`, `python-snap7==1.3` (+ native snap7 lib in Dockerfile) |
| 3 | `rockwell-agent` | `pylogix==0.9.3` |
| 4 | `network-agent` | `pysnmp`, `scapy==2.5.0` — needs `NET_BROADCAST` Docker capability for Profinet DCP multicast |
| 5 | Alerting + reporting | Grafana Alerting → email/Teams, `weasyprint` for PDF, `/export/report` FastAPI endpoint |
