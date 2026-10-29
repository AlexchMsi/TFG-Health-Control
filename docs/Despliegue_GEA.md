# Checklist de despliegue — VM en red de GEA (posiblemente sin Internet)

Guía para desplegar el stack de Control System Health Status en una máquina virtual
dentro de la red del cliente, monitorizando estaciones de ingeniería Windows,
VMware y PLCs Siemens / servidores SCADA OPC UA reales.

## 1. Preparación offline (en la máquina de desarrollo, CON Internet)

```bash
# 1. Construir todas las imágenes
docker compose build

# 2. Precargar el modelo de Ollama en el volumen (una sola vez)
docker compose up -d ollama
docker exec ollama ollama pull llama3.1:8b

# 3. Exportar imágenes (incluye las de terceros)
docker save -o ftg-images.tar \
  ftg-api ftg-server-agent ftg-siemens-agent ftg-scada-agent ftg-recommendation-agent \
  influxdb:2.7 grafana/grafana-oss:10.4.0 ollama/ollama:0.30.7 alpine:3.19

# 4. Exportar el volumen de Ollama con el modelo precargado (~5 GB)
docker run --rm -v ftg_ollama_data:/data -v "$PWD":/backup alpine:3.19 \
  tar czf /backup/ollama_data.tar.gz -C /data .
```

Llevar a la VM: `ftg-images.tar`, `ollama_data.tar.gz`, el repositorio (o un zip) y un `.env` preparado.

## 2. Instalación en la VM de GEA (SIN Internet)

```bash
docker load -i ftg-images.tar

# Restaurar el modelo de Ollama antes del primer arranque
docker volume create ftg_ollama_data
docker run --rm -v ftg_ollama_data:/data -v "$PWD":/backup alpine:3.19 \
  tar xzf /backup/ollama_data.tar.gz -C /data

cp .env.example .env   # y editar credenciales/tokens
docker compose up -d
```

Nota: `recommendation-agent` tolera el fallo del `ollama pull` (modo offline) y usa
el modelo precargado del volumen. Si el volumen está vacío y no hay Internet, el
agente registrará errores en cada análisis pero no afecta al resto del stack.

## 3. Puertos que debe permitir el firewall (desde la VM hacia los equipos)

| Destino | Puerto | Protocolo | Uso |
|---|---|---|---|
| Estaciones de ingeniería Windows | 161/UDP | SNMP | server-agent (método snmp) |
| Estaciones de ingeniería Windows | 5985 (o 5986 TLS) | WinRM | server-agent (método winrm) |
| vCenter / ESXi | 443/TCP | HTTPS (vSphere API) | server-agent (método vmware) |
| PLC Siemens | 102/TCP | S7Comm | siemens-agent (snap7) |
| PLC / gateway OPC UA | 4840/TCP (o el configurado) | OPC UA | siemens-agent (opcua) y scada-agent |

Y hacia la propia VM (desde los puestos de operación): 3000 (Grafana), 8000 (API/UI), opcionalmente 8086 (InfluxDB).

En las estaciones Windows: habilitar SNMP con `scripts/INSTALAR_SNMP.bat` (como
Administrador) o `scripts/enable_snmp_target.ps1 -MonitoringServerIP <ip-de-la-VM>`.
La regla de firewall debe permitir UDP 161 desde la IP/subred de la VM.

## 4. Verificación de conectividad (SIEMPRE desde el contenedor, no solo desde la VM)

Ver `pruebas.txt` para el procedimiento completo. Resumen:

```bash
# Desde la VM
Test-NetConnection -ComputerName <IP_PLC> -Port 4840
Test-NetConnection -ComputerName <IP_PLC> -Port 102

# Desde el contenedor (la red de Docker puede diferir)
docker exec siemens-agent python -c "import socket; socket.create_connection(('<IP_PLC>',4840),5); print('OK')"
docker exec server-agent python3 scripts/test_connectivity.py   # si aplica
```

## 5. Alta de targets

Vía UI (`http://<vm>:8000/ui`) o API (`POST /config/targets`). Los agentes
sincronizan cada 30 s. Desde la corrección del ConfigPoller (2026-10-30), un
`PUT /config/targets/{id}` que cambie la config **sí** se propaga al job en ≤30 s
(el temporizador del intervalo se reinicia al aplicar el cambio).

## 6. Semántica de métricas (tras las correcciones de 2026-10-30)

- `reachable` (siemens_plc_health): 1 = la conexión OPC UA/S7 funcionó. Un PLC
  **en STOP sigue siendo reachable**; el modo de operación está en `cpu_state`.
  Las alertas de "PLC parado" deben basarse en `cpu_state`, no en `reachable`.
- `cpu_state` vía OPC UA deriva del estado del **servidor OPC UA**, no
  necesariamente del modo físico de la CPU (coinciden en S7-1500 nativo;
  pendiente de validar con hardware real).
- `esxi_health`: un fallo total de conexión a vCenter/ESXi escribe un punto con
  `reachable=0` y `last_error_text` (source_id `esxi-<host-configurado>`).

## 7. Limitaciones conocidas (pendientes)

- La UI no expone toda la configuración WinRM (lista de servicios críticos sin
  conectar con el script remoto).
- La API no tiene autenticación; las credenciales de targets se guardan y
  devuelven sin separación. No exponer el puerto 8000 fuera de la red de gestión.
- Validación con PLC/SCADA reales pendiente (hasta ahora validado contra
  simulador OPC UA local: `scripts/opcua_sim_server.py`).
