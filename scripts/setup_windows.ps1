#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Instala y arranca el stack TFG Health Control en Windows Server/10/11
    sin Docker Desktop.

.DESCRIPTION
    1. Descarga e instala Python 3.12 (si no existe)
    2. Descarga e instala InfluxDB 2.7 (si no existe)
    3. Instala Grafana via winget o MSI (si no existe)
    4. Genera .env con URLs localhost
    5. Instala dependencias Python (shared, api, server-agent, siemens-agent)
    6. Crea servicios Windows (NSSM) o scripts de arranque para cada proceso
    7. Inicializa InfluxDB (org, bucket, token)

.NOTES
    Ejecutar desde la raiz del repositorio como Administrador:
        Set-ExecutionPolicy Bypass -Scope Process -Force
        .\scripts\setup_windows.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ─── Rutas ────────────────────────────────────────────────────────────────────
$REPO_ROOT   = Split-Path -Parent $PSScriptRoot
$INFLUX_DIR  = "C:\influxdb"
$INFLUX_EXE  = "$INFLUX_DIR\influxd.exe"
$INFLUXCLI   = "$INFLUX_DIR\influx.exe"
$NSSM_DIR    = "C:\nssm"
$NSSM_EXE    = "$NSSM_DIR\nssm.exe"
$DATA_DIR    = "$REPO_ROOT\data"
$ENV_FILE    = "$REPO_ROOT\.env"
$LOG_DIR     = "$REPO_ROOT\logs"

# ─── Valores por defecto (puedes editar antes de ejecutar) ────────────────────
$INFLUX_ORG      = "gea"
$INFLUX_BUCKET   = "health_status"
$INFLUX_USER     = "admin"
$INFLUX_PASSWORD = "Admin1234!"          # min 8 chars
$INFLUX_TOKEN    = "tfg-secret-token-change-me"
$GF_ADMIN_PASS   = "Admin1234!"
$POLL_INTERVAL   = "60"
$LOG_LEVEL       = "INFO"
$SNMP_COMMUNITY  = "public"

# ─── Helpers ──────────────────────────────────────────────────────────────────
function Write-Step { param($msg) Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK   { param($msg) Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "    [WARN] $msg" -ForegroundColor Yellow }

function Test-Command { param($cmd) return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

function Wait-Port {
    param($port, $seconds = 30)
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $tcp.Connect("127.0.0.1", $port)
            $tcp.Close()
            return $true
        } catch { Start-Sleep -Milliseconds 500 }
    }
    return $false
}

# ─── 0. Crear directorios ─────────────────────────────────────────────────────
Write-Step "Creando directorios de trabajo"
foreach ($d in @($DATA_DIR, $LOG_DIR, $INFLUX_DIR, $NSSM_DIR)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
}
Write-OK "data/, logs/, C:\influxdb, C:\nssm listos"

# ─── 1. Python 3.12 ───────────────────────────────────────────────────────────
Write-Step "Comprobando Python"
$pythonOk = $false
foreach ($candidate in @("python", "python3", "py")) {
    if (Test-Command $candidate) {
        $ver = & $candidate --version 2>&1
        if ($ver -match "3\.(1[0-9]|[2-9]\d)") { $pythonOk = $true; $PYTHON = $candidate; break }
    }
}

if (-not $pythonOk) {
    Write-Warn "Python 3.10+ no encontrado. Descargando Python 3.12..."
    $pyUrl = "https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe"
    $pyInstaller = "$env:TEMP\python-3.12.9-amd64.exe"
    Invoke-WebRequest -Uri $pyUrl -OutFile $pyInstaller -UseBasicParsing
    Start-Process -FilePath $pyInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH","User")
    $PYTHON = "python"
    Write-OK "Python 3.12 instalado"
} else {
    Write-OK "Python encontrado: $PYTHON ($ver)"
}

# ─── 2. InfluxDB 2.7 ─────────────────────────────────────────────────────────
Write-Step "Comprobando InfluxDB"
if (-not (Test-Path $INFLUX_EXE)) {
    Write-Warn "influxd.exe no encontrado en $INFLUX_DIR. Descargando InfluxDB 2.7..."
    $influxUrl = "https://dl.influxdata.com/influxdb/releases/influxdb2-2.7.11-windows-amd64.zip"
    $influxZip = "$env:TEMP\influxdb2.zip"
    Invoke-WebRequest -Uri $influxUrl -OutFile $influxZip -UseBasicParsing
    Expand-Archive -Path $influxZip -DestinationPath $env:TEMP\influx_extract -Force
    # El zip puede tener un subdirectorio
    $extracted = Get-ChildItem "$env:TEMP\influx_extract" -Recurse -Filter "influxd.exe" | Select-Object -First 1
    Copy-Item (Split-Path $extracted.FullName) -Destination $INFLUX_DIR -Recurse -Force
    Write-OK "InfluxDB extraido en $INFLUX_DIR"
} else {
    Write-OK "influxd.exe ya existe en $INFLUX_DIR"
}

# ─── 3. NSSM (para crear servicios Windows) ───────────────────────────────────
Write-Step "Comprobando NSSM (gestor de servicios)"
if (-not (Test-Path $NSSM_EXE)) {
    Write-Warn "NSSM no encontrado. Descargando..."
    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $nssmZip = "$env:TEMP\nssm.zip"
    Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip -UseBasicParsing
    Expand-Archive -Path $nssmZip -DestinationPath "$env:TEMP\nssm_extract" -Force
    $nssmExe = Get-ChildItem "$env:TEMP\nssm_extract" -Recurse -Filter "nssm.exe" |
               Where-Object { $_.FullName -match "win64" } |
               Select-Object -First 1
    if (-not $nssmExe) {
        $nssmExe = Get-ChildItem "$env:TEMP\nssm_extract" -Recurse -Filter "nssm.exe" | Select-Object -First 1
    }
    Copy-Item $nssmExe.FullName -Destination $NSSM_EXE -Force
    Write-OK "NSSM instalado en $NSSM_EXE"
} else {
    Write-OK "NSSM ya disponible"
}

# ─── 4. Grafana ───────────────────────────────────────────────────────────────
Write-Step "Comprobando Grafana"
$grafanaRunning = Get-Service -Name "Grafana" -ErrorAction SilentlyContinue
if (-not $grafanaRunning) {
    # Intentar winget primero
    if (Test-Command winget) {
        Write-Warn "Instalando Grafana via winget..."
        winget install -e --id GrafanaLabs.Grafana --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        Write-OK "Grafana instalado via winget"
    } else {
        $grafanaUrl = "https://dl.grafana.com/oss/release/grafana-10.4.3.windows-amd64.msi"
        $grafanaInstaller = "$env:TEMP\grafana.msi"
        Write-Warn "winget no disponible. Descargando Grafana MSI..."
        Invoke-WebRequest -Uri $grafanaUrl -OutFile $grafanaInstaller -UseBasicParsing
        Start-Process msiexec -ArgumentList "/i `"$grafanaInstaller`" /quiet" -Wait
        Write-OK "Grafana instalado via MSI"
    }
} else {
    Write-OK "Servicio Grafana ya instalado"
}

# ─── 5. Generar .env ──────────────────────────────────────────────────────────
Write-Step "Generando .env"
if (Test-Path $ENV_FILE) {
    Write-Warn ".env ya existe — se sobreescribira con URLs localhost"
}

@"
# Generado por setup_windows.ps1 — $(Get-Date -Format "yyyy-MM-dd HH:mm")
# ── InfluxDB ──────────────────────────────────────────────────────────────────
INFLUXDB_URL=http://localhost:8086
INFLUXDB_ORG=$INFLUX_ORG
INFLUXDB_BUCKET=$INFLUX_BUCKET
INFLUXDB_ADMIN_TOKEN=$INFLUX_TOKEN
INFLUXDB_ADMIN_USER=$INFLUX_USER
INFLUXDB_ADMIN_PASSWORD=$INFLUX_PASSWORD

# ── Grafana ───────────────────────────────────────────────────────────────────
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=$GF_ADMIN_PASS
GF_SERVER_ROOT_URL=http://localhost:3000

# ── Agentes ───────────────────────────────────────────────────────────────────
POLL_INTERVAL_SECONDS=$POLL_INTERVAL
LOG_LEVEL=$LOG_LEVEL
API_URL=http://localhost:8000

# ── SNMP ──────────────────────────────────────────────────────────────────────
SNMP_COMMUNITY=$SNMP_COMMUNITY
SNMP_VERSION=2c

# ── FastAPI ───────────────────────────────────────────────────────────────────
API_HOST=0.0.0.0
API_PORT=8000
"@ | Set-Content -Encoding UTF8 -Path $ENV_FILE

Write-OK ".env escrito en $ENV_FILE"

# ─── 6. Instalar dependencias Python ─────────────────────────────────────────
Write-Step "Instalando shared library"
Set-Location $REPO_ROOT
& $PYTHON -m pip install --quiet --upgrade pip
& $PYTHON -m pip install --quiet -e shared
Write-OK "shared instalada"

Write-Step "Instalando dependencias API"
& $PYTHON -m pip install --quiet -r api\requirements.txt
Write-OK "api deps OK"

Write-Step "Instalando dependencias server-agent"
& $PYTHON -m pip install --quiet -r agents\server-agent\requirements.txt
Write-OK "server-agent deps OK"

if (Test-Path "agents\siemens-agent\requirements.txt") {
    Write-Step "Instalando dependencias siemens-agent"
    & $PYTHON -m pip install --quiet -r agents\siemens-agent\requirements.txt
    Write-OK "siemens-agent deps OK"
}

# ─── 7. Registrar servicio InfluxDB con NSSM ─────────────────────────────────
Write-Step "Registrando servicio InfluxDB"
$influxSvc = Get-Service -Name "InfluxDB" -ErrorAction SilentlyContinue
if (-not $influxSvc) {
    & $NSSM_EXE install InfluxDB $INFLUX_EXE
    & $NSSM_EXE set InfluxDB AppParameters "--bolt-path `"$DATA_DIR\influxd.bolt`" --engine-path `"$DATA_DIR\engine`" --http-bind-address `":8086`""
    & $NSSM_EXE set InfluxDB AppDirectory $INFLUX_DIR
    & $NSSM_EXE set InfluxDB AppStdout "$LOG_DIR\influxdb.log"
    & $NSSM_EXE set InfluxDB AppStderr "$LOG_DIR\influxdb-err.log"
    & $NSSM_EXE set InfluxDB Start SERVICE_AUTO_START
    Write-OK "Servicio InfluxDB creado"
} else {
    Write-OK "Servicio InfluxDB ya existe"
}

# Arrancar InfluxDB
$influxSvc = Get-Service -Name "InfluxDB"
if ($influxSvc.Status -ne "Running") {
    Start-Service InfluxDB
    Write-Warn "Esperando a que InfluxDB levante en :8086..."
    if (-not (Wait-Port 8086 60)) {
        Write-Error "InfluxDB no respondio en 60s. Revisa $LOG_DIR\influxdb-err.log"
    }
}
Write-OK "InfluxDB corriendo en http://localhost:8086"

# ─── 8. Inicializar InfluxDB (solo primera vez) ───────────────────────────────
Write-Step "Inicializando InfluxDB (org, bucket, token)"
$setupCheck = & $INFLUXCLI setup --json 2>&1
if ($setupCheck -notmatch "already") {
    & $INFLUXCLI setup `
        --username  $INFLUX_USER     `
        --password  $INFLUX_PASSWORD `
        --org       $INFLUX_ORG      `
        --bucket    $INFLUX_BUCKET   `
        --token     $INFLUX_TOKEN    `
        --host      http://localhost:8086 `
        --force
    Write-OK "InfluxDB inicializado"
} else {
    Write-OK "InfluxDB ya estaba inicializado"
}

# ─── 9. Registrar servicio API con NSSM ───────────────────────────────────────
Write-Step "Registrando servicio TFG-API"
$apiSvc = Get-Service -Name "TFG-API" -ErrorAction SilentlyContinue

# Localizar uvicorn
$uvicorn = (& $PYTHON -c "import shutil; print(shutil.which('uvicorn') or '')" 2>&1).Trim()
if (-not $uvicorn) { $uvicorn = "$env:LOCALAPPDATA\Programs\Python\Python312\Scripts\uvicorn.exe" }

if (-not $apiSvc) {
    & $NSSM_EXE install TFG-API $uvicorn
    & $NSSM_EXE set TFG-API AppParameters "api.src.main:app --host 0.0.0.0 --port 8000"
    & $NSSM_EXE set TFG-API AppDirectory $REPO_ROOT
    & $NSSM_EXE set TFG-API AppEnvironmentExtra `
        "INFLUXDB_URL=http://localhost:8086" `
        "INFLUXDB_ORG=$INFLUX_ORG" `
        "INFLUXDB_BUCKET=$INFLUX_BUCKET" `
        "INFLUXDB_ADMIN_TOKEN=$INFLUX_TOKEN"
    & $NSSM_EXE set TFG-API AppStdout "$LOG_DIR\api.log"
    & $NSSM_EXE set TFG-API AppStderr "$LOG_DIR\api-err.log"
    & $NSSM_EXE set TFG-API Start SERVICE_AUTO_START
    Write-OK "Servicio TFG-API creado"
} else {
    Write-OK "Servicio TFG-API ya existe"
}

$apiSvc = Get-Service -Name "TFG-API"
if ($apiSvc.Status -ne "Running") {
    Start-Service TFG-API
    Write-Warn "Esperando API en :8000..."
    if (-not (Wait-Port 8000 30)) { Write-Warn "API no respondio en 30s — revisa $LOG_DIR\api-err.log" }
}
Write-OK "API corriendo en http://localhost:8000"

# ─── 10. Registrar servicio server-agent con NSSM ────────────────────────────
Write-Step "Registrando servicio TFG-ServerAgent"
$agentSvc = Get-Service -Name "TFG-ServerAgent" -ErrorAction SilentlyContinue
if (-not $agentSvc) {
    & $NSSM_EXE install TFG-ServerAgent $PYTHON
    & $NSSM_EXE set TFG-ServerAgent AppParameters "-m src.main"
    & $NSSM_EXE set TFG-ServerAgent AppDirectory "$REPO_ROOT\agents\server-agent"
    & $NSSM_EXE set TFG-ServerAgent AppEnvironmentExtra `
        "INFLUXDB_URL=http://localhost:8086" `
        "INFLUXDB_ORG=$INFLUX_ORG" `
        "INFLUXDB_BUCKET=$INFLUX_BUCKET" `
        "INFLUXDB_ADMIN_TOKEN=$INFLUX_TOKEN" `
        "API_URL=http://localhost:8000" `
        "SNMP_COMMUNITY=$SNMP_COMMUNITY" `
        "LOG_LEVEL=$LOG_LEVEL"
    & $NSSM_EXE set TFG-ServerAgent AppStdout "$LOG_DIR\server-agent.log"
    & $NSSM_EXE set TFG-ServerAgent AppStderr "$LOG_DIR\server-agent-err.log"
    & $NSSM_EXE set TFG-ServerAgent Start SERVICE_AUTO_START
    Write-OK "Servicio TFG-ServerAgent creado"
} else {
    Write-OK "Servicio TFG-ServerAgent ya existe"
}

$agentSvc = Get-Service -Name "TFG-ServerAgent"
if ($agentSvc.Status -ne "Running") { Start-Service TFG-ServerAgent }
Write-OK "server-agent arrancado"

# ─── 11. Registrar servicio siemens-agent (opcional) ─────────────────────────
if (Test-Path "$REPO_ROOT\agents\siemens-agent\src\main.py") {
    Write-Step "Registrando servicio TFG-SiemensAgent"
    $siemensSvc = Get-Service -Name "TFG-SiemensAgent" -ErrorAction SilentlyContinue
    if (-not $siemensSvc) {
        & $NSSM_EXE install TFG-SiemensAgent $PYTHON
        & $NSSM_EXE set TFG-SiemensAgent AppParameters "-m src.main"
        & $NSSM_EXE set TFG-SiemensAgent AppDirectory "$REPO_ROOT\agents\siemens-agent"
        & $NSSM_EXE set TFG-SiemensAgent AppEnvironmentExtra `
            "INFLUXDB_URL=http://localhost:8086" `
            "INFLUXDB_ORG=$INFLUX_ORG" `
            "INFLUXDB_BUCKET=$INFLUX_BUCKET" `
            "INFLUXDB_ADMIN_TOKEN=$INFLUX_TOKEN" `
            "API_URL=http://localhost:8000" `
            "LOG_LEVEL=$LOG_LEVEL"
        & $NSSM_EXE set TFG-SiemensAgent AppStdout "$LOG_DIR\siemens-agent.log"
        & $NSSM_EXE set TFG-SiemensAgent AppStderr "$LOG_DIR\siemens-agent-err.log"
        & $NSSM_EXE set TFG-SiemensAgent Start SERVICE_AUTO_START
        Write-OK "Servicio TFG-SiemensAgent creado"
    } else {
        Write-OK "Servicio TFG-SiemensAgent ya existe"
    }
    $siemensSvc = Get-Service -Name "TFG-SiemensAgent"
    if ($siemensSvc.Status -ne "Running") { Start-Service TFG-SiemensAgent }
    Write-OK "siemens-agent arrancado"
}

# ─── 12. Arrancar / verificar Grafana ────────────────────────────────────────
Write-Step "Arrancando Grafana"
$gfSvc = Get-Service -Name "Grafana" -ErrorAction SilentlyContinue
if ($gfSvc) {
    if ($gfSvc.Status -ne "Running") { Start-Service Grafana }
    Write-Warn "Esperando Grafana en :3000..."
    if (Wait-Port 3000 30) { Write-OK "Grafana corriendo en http://localhost:3000" }
    else { Write-Warn "Grafana no respondio — revisa el Visor de Eventos" }
} else {
    Write-Warn "Servicio Grafana no encontrado. Abrelo manualmente desde Start Menu."
}

# ─── 13. Resumen final ────────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
Write-Host "  TFG Health Control — Stack arrancado" -ForegroundColor Magenta
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
Write-Host ""
Write-Host "  InfluxDB  →  http://localhost:8086" -ForegroundColor White
Write-Host "  API       →  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Grafana   →  http://localhost:3000  (admin / $GF_ADMIN_PASS)" -ForegroundColor White
Write-Host ""
Write-Host "  Logs en:  $LOG_DIR" -ForegroundColor Gray
Write-Host ""
Write-Host "  Servicios Windows registrados (Start automatico al reiniciar):" -ForegroundColor Gray
Write-Host "    InfluxDB, TFG-API, TFG-ServerAgent, TFG-SiemensAgent" -ForegroundColor Gray
Write-Host ""
Write-Host "  Para gestionar servicios:" -ForegroundColor Gray
Write-Host "    Get-Service InfluxDB,TFG-API,TFG-ServerAgent" -ForegroundColor Gray
Write-Host "    Stop-Service TFG-API" -ForegroundColor Gray
Write-Host "    Start-Service TFG-API" -ForegroundColor Gray
Write-Host ""
Write-Host "  Siguiente paso — importar dashboards Grafana:" -ForegroundColor Yellow
Write-Host "    http://localhost:3000  → Dashboards → Import → sube los JSON de" -ForegroundColor Yellow
Write-Host "    $REPO_ROOT\infra\grafana\dashboards\" -ForegroundColor Yellow
Write-Host ""
