# TFG — Control System Health Status

Real-time, vendor-neutral health monitoring system for industrial OT environments.
Developed for **GEA Process Engineering** as a Final Degree Project (PFG) at Universidad Francisco de Vitoria.

## Architecture

```
[Windows Servers / ESXi VMs / PLCs / Switches]
          │  (SNMP / WinRM / pyVmomi / OPC UA / EtherNet-IP)
          ▼
[Python Agent Containers]  ──►  [InfluxDB :8086]
                                       ▲
                            [FastAPI :8000]   [Grafana :3000]
```

## Components

| Component | Description |
|---|---|
| `server-agent` | Monitors Windows servers (SNMP/WinRM) and VMware ESXi hosts/VMs |
| `siemens-agent` | Monitors Siemens S7-1500 PLCs via OPC UA / Snap7 |
| `rockwell-agent` | Monitors Rockwell L6X PLCs via EtherNet/IP (Pylogix) |
| `network-agent` | Monitors industrial switches via SNMP, LLDP, Profinet DCP |
| `api` | FastAPI REST service — abstraction layer over InfluxDB |
| `infra/influxdb` | InfluxDB 2.x — time-series storage |
| `infra/grafana` | Grafana — dashboards and alerting |

## Quick Start

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env with your credentials

# 2. Start infrastructure only (first run)
docker compose up influxdb grafana

# 3. Verify InfluxDB at http://localhost:8086
# Verify Grafana at http://localhost:3000

# 4. Start all services
docker compose up -d

# 5. Check connectivity to targets
python scripts/test_connectivity.py
```

## Development

```bash
# Run server-agent standalone (outside Docker)
cd agents/server-agent
pip install -r requirements.txt
pip install -e ../../shared
python -m src.main

# Run API standalone
cd api
pip install -r requirements.txt
pip install -e ../shared
uvicorn src.main:app --reload
```

## Project Phases

- [x] Phase 1: Server/VM monitoring (Windows SNMP/WinRM + VMware ESXi)
- [ ] Phase 2: Siemens PLC agent (OPC UA + Snap7 + PLCSIM)
- [ ] Phase 3: Rockwell PLC agent (Pylogix / EtherNet-IP)
- [ ] Phase 4: Network monitoring (SNMP + LLDP + Profinet DCP)
- [ ] Phase 5: Alerting, PDF reporting, Codex integration

## Documentation

- `docs/TFG - Control System Health Status.docx` — Technical specification
- `docs/Anteproyecto.docx` — Preliminary project (university submission)
