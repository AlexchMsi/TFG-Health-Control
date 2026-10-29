# Tutorial — Prueba real en el servidor umbrella

Plan para un día de pruebas en la VM/servidor dentro de la red de GEA.
Orden pensado para aislar fallos: primero el stack solo, luego simulador,
luego equipos reales uno a uno. Si algo falla, sabrás en qué capa está.

---

## 0. La noche antes (en tu PC, con Internet)

Prepara el paquete offline por si umbrella no tiene Internet:

```bash
cd C:\Universidad\ftg
git pull origin develop
docker compose build

# Exportar imágenes (~6-8 GB)
docker save -o ftg-images.tar ftg-api ftg-server-agent ftg-siemens-agent ftg-scada-agent ftg-recommendation-agent influxdb:2.7 grafana/grafana-oss:10.4.0 ollama/ollama:0.30.7 alpine:3.19

# Exportar el volumen de Ollama con el modelo ya descargado (~5 GB)
docker run --rm -v ftg_ollama_data:/data -v "%cd%":/backup alpine:3.19 tar czf /backup/ollama_data.tar.gz -C /data .
```

**Llevar**: `ftg-images.tar`, `ollama_data.tar.gz`, zip del repo (rama develop), y los
valores de tu `.env` (token de InfluxDB, contraseña de Grafana). En un USB o unidad de red.

---

## 1. Requisitos en umbrella (5 min)

```powershell
docker --version          # Docker instalado y corriendo
docker compose version    # Compose v2
```
- RAM libre ≥ 8 GB (Ollama con llama3.1:8b necesita ~6 GB; si umbrella va justo,
  puedes arrancar sin IA: `docker compose up -d influxdb grafana api server-agent siemens-agent scada-agent`).
- Puertos 3000, 8000, 8086 libres.

## 2. Desplegar (10-15 min)

**Con Internet:**
```bash
git clone -b develop https://github.com/AlexchMsi/TFG-Health-Control.git ftg && cd ftg
cp .env.example .env    # editar: token Influx, contraseña Grafana
docker compose build && docker compose up -d
```

**Sin Internet:**
```bash
docker load -i ftg-images.tar
docker volume create ftg_ollama_data
docker run --rm -v ftg_ollama_data:/data -v "$PWD":/backup alpine:3.19 tar xzf /backup/ollama_data.tar.gz -C /data
cd ftg && cp .env.example .env   # editar valores
docker compose up -d
```

**Comprobar:**
```bash
docker compose ps        # influxdb y ollama "healthy", el resto "Up"
curl http://localhost:8000/health/
```
Abrir `http://localhost:8000/ui` → deben verse las 3 pestañas (Targets / Estado / Recomendaciones IA)
y `http://localhost:3000` (Grafana, 3 dashboards provisionados).

## 3. Smoke test con simuladores — SIN tocar equipos reales (15 min)

Valida que el stack entero funciona en umbrella antes de depender de permisos OT:

```bash
docker run -d --name opcua-sim --network ftg_ot-health-net -v ./scripts:/sim ftg-siemens-agent python /sim/opcua_sim_server.py
```

Desde la **UI → Targets → + Añadir target**:
1. Tipo `siemens`, método OPC UA, URL `opc.tcp://opcua-sim:4840`.
2. Tipo `scada`, URL `opc.tcp://opcua-sim:4840`, tags:
   ```
   Temperature,ns=2;s=Temperature
   Pressure,ns=2;s=Pressure
   PumpRunning,ns=2;s=PumpRunning
   ```
3. Tipo `server`, método SNMP, host `snmpd-sim`, puerto `1161`.

Esperar ~1 min → pestaña **Estado**: PLC con conexión OK y CPU RUN, tags GOOD con
valores cambiantes, servidor sim OK. **Si esto funciona, el stack está bien** y
cualquier fallo posterior será de red/firewall/credenciales con los equipos reales.

## 4. Primera estación de ingeniería por SNMP (20 min)

En la estación (como Administrador):
```powershell
# Opción rápida (doble clic): scripts\INSTALAR_SNMP.bat
# Opción producción, limitando el origen a umbrella:
scripts\enable_snmp_target.ps1 -MonitoringServerIP <IP_de_umbrella>
netstat -an | findstr ":161"     # debe mostrar UDP 0.0.0.0:161
```

En umbrella, probar desde el contenedor (el tráfico sale de la subred Docker):
```bash
docker exec server-agent python3 -c "
from pysnmp.hlapi import *
for (e,_,_,vb) in getCmd(SnmpEngine(), CommunityData('public'),
    UdpTransportTarget(('<IP_estacion>', 161), timeout=3, retries=0),
    ContextData(), ObjectType(ObjectIdentity('1.3.6.1.2.1.1.3.0'))): print(e or vb)
"
```
Si imprime el uptime → UI → añadir target `server`/SNMP con esa IP.
En ~1 min: Estado → CPU, RAM, discos reales de la estación.

Si falla: firewall de la estación (la regla debe aceptar UDP 161 desde la IP de
umbrella **y/o** la subred de Docker), o VLAN/routing entre umbrella y la estación.

## 5. WinRM — servicios críticos y NTP (opcional, 15 min)

En la estación: `Enable-PSRemoting -Force` (y si no hay dominio,
`Set-Item WSMan:\localhost\Client\TrustedHosts -Value "<IP_umbrella>"` en umbrella no aplica,
es en el cliente; para NTLM local basta usuario administrador local).

UI → añadir target `server`, método **WinRM**: usuario (`DOMINIO\usuario` o local),
contraseña, transporte NTLM, puerto 5985, y la lista de servicios críticos
(uno por línea, nombre del servicio: `W32Time`, `Spooler`, el runtime del SCADA…).
En Estado aparecerán también los servicios y su estado.

## 6. PLC Siemens / SCADA real (cuando haya permiso OT)

**Avisar al responsable OT antes.** Todo es solo lectura, pero se avisa igual.

Conectividad primero, desde el contenedor:
```bash
docker exec siemens-agent python -c "import socket; socket.create_connection(('<IP_PLC>',4840),5); print('OPCUA OK')"
docker exec siemens-agent python -c "import socket; socket.create_connection(('<IP_PLC>',102),5); print('S7 OK')"
```

- **PLC** → UI → target `siemens`, método **Auto**, OPC UA URL `opc.tcp://<IP>:4840`,
  Snap7 host `<IP>` (rack 0, slot 1 para S7-1500).
- **SCADA** → hacen falta los node_ids de los tags. Si no los tienes:
  `python scripts/discover_opcua.py --host <IP> --port 4840` (o pedirlos al integrador).

**Qué validar con el PLC real** (punto clave para la memoria):
- PLC encendido y en RUN → Estado: conexión OK, CPU RUN.
- Si pueden ponerlo en **STOP** desde TIA Portal → debe seguir "conexión OK" con CPU STOP
  (ya no cuenta como inalcanzable). Anotar si el `cpu_state` vía OPC UA refleja el modo
  real de la CPU o el estado del servidor (limitación documentada).
- Desconectar el cable / bloquear puerto → conexión SIN CONEXIÓN con el error visible.

## 7. Pruebas de robustez (evidencias para la memoria, 10 min)

1. **Edición en caliente**: UI → Editar un target (cambiar intervalo) → en los logs
   `docker compose logs --since 2m <agente>` debe salir `ConfigPoller: updating target ... (config changed)` en ≤30 s.
2. **Caída**: parar el simulador (`docker stop opcua-sim`) → Estado: SIN CONEXIÓN en ~1 min. `docker start opcua-sim` → se recupera.
3. **IA**: pestaña Recomendaciones → "Analizar ahora" (1-3 min). Debe mencionar los problemas reales que haya en ese momento.
4. **Captura todo**: pantallazos de UI y Grafana con equipos reales + hora. Es el material de "Resultados" del TFG.

## 8. Si algo falla — tabla rápida

| Síntoma | Causa probable | Comprobación |
|---|---|---|
| Contenedor reiniciándose | Error al arrancar | `docker compose logs <servicio>` |
| umbrella ve el equipo, el contenedor no | Firewall filtra la subred Docker / NAT | test de socket con `docker exec` (arriba) |
| SNMP timeout | Firewall UDP 161 con origen restringido | regla con `-RemoteAddress` correcto |
| OPC UA `BadUserAccessDenied` / `BadSecurity...` | Servidor exige usuario o política de seguridad | probar con usuario/contraseña en el target; anotar política requerida |
| Snap7 conecta pero sin datos | Rack/slot incorrectos o S7-1500 con "protección de acceso" | probar slot 1 y 2; revisar protección en TIA Portal |
| Endpoint `/metrics/...` vacío | El agente no escribe en la ventana de 10-15 min | logs del agente + `docker exec influxdb influx query ...` |
| Ollama no responde / lento | RAM insuficiente | `docker stats ollama`; arrancar sin IA si hace falta |

**No exponer el puerto 8000 fuera de la red de gestión** (API sin autenticación).
