# ============================================================
#  install_native.ps1
#  Instala y arranca el stack TFG-Health-Control sin Docker
#  Requiere: Windows 10/11 o Windows Server, PowerShell 5+
#  Ejecutar como Administrador
# ============================================================

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

# ── Colores ─────────────────────────────────────────────────
function Write-Step  { param($msg) Write-Host "`n[>>] $msg" -ForegroundColor Cyan }
function Write-OK    { param($msg) Write-Host "[ OK] $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "[ERR] $msg" -ForegroundColor Red; exit 1 }

# ── Versiones ────────────────────────────────────────────────
$INFLUX_VERSION  = "2.7.11"
$GRAFANA_VERSION = "10.4.0"
$INFLUX_URL  = "https://dl.influxdata.com/influxdb/releases/influxdb2-$INFLUX_VERSION-windows-amd64.zip"
$GRAFANA_URL = "https://dl.grafana.com/oss/release/grafana-$GRAFANA_VERSION.windows-amd64.msi"

$INFLUX_DIR  = "C:\influxdb"
$GRAFANA_DIR = "C:\grafana"
$PROJECT_DIR = Split-Path -Parent $PSScriptRoot   # raiz del repo

# ── .env ─────────────────────────────────────────────────────
$ENV_FILE = Join-Path $PROJECT_DIR ".env"
if (-not (Test-Path $ENV_FILE)) {
    Write-Warn ".env no encontrado — copiando desde .env.example"
    $example = Join-Path $PROJECT_DIR ".env.example"
    if (Test-Path $example) { Copy-Item $example $ENV_FILE }
    else { Write-Fail ".env.example tampoco existe. Crea el .env manualmente." }
}

# Cargar variables del .env en el proceso actual
foreach ($line in Get-Content $ENV_FILE) {
    if ($line -match '^\s*([^#][^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

$INFLUX_TOKEN  = $env:INFLUXDB_ADMIN_TOKEN
$INFLUX_ORG    = $env:INFLUXDB_ORG
$INFLUX_BUCKET = $env:INFLUXDB_BUCKET
$INFLUX_USER   = $env:INFLUXDB_ADMIN_USER
$INFLUX_PASS   = $env:INFLUXDB_ADMIN_PASSWORD

# ────────────────────────────────────────────────────────────
# 1. PYTHON
# ────────────────────────────────────────────────────────────
Write-Step "Comprobando Python..."
try {
    $pyVer = python --version 2>&1
    Write-OK "Python encontrado: $pyVer"
} catch {
    Write-Warn "Python no encontrado. Descargando instalador..."
    $pyInstaller = "$env:TEMP\python-installer.exe"
    Invoke-WebRequest "https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe" -OutFile $pyInstaller
    Start-Process $pyInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
    Write-OK "Python instalado. Puede que necesites reiniciar PowerShell."
}

# ────────────────────────────────────────────────────────────
# 2. INFLUXDB
# ────────────────────────────────────────────────────────────
Write-Step "Instalando InfluxDB $INFLUX_VERSION..."

if (-not (Test-Path "$INFLUX_DIR\influxd.exe")) {
    $zipPath = "$env:TEMP\influxdb.zip"
    Write-Host "  Descargando..."
    Invoke-WebRequest $INFLUX_URL -OutFile $zipPath
    Expand-Archive $zipPath -DestinationPath "C:\" -Force
    # El zip extrae en influxdb2-<version>-windows-amd64, renombrar
    $extracted = Get-ChildItem "C:\" -Directory | Where-Object { $_.Name -like "influxdb2-*" } | Select-Object -First 1
    if ($extracted) { Rename-Item $extracted.FullName $INFLUX_DIR }
    Write-OK "InfluxDB extraido en $INFLUX_DIR"
} else {
    Write-OK "InfluxDB ya instalado en $INFLUX_DIR"
}

# Arrancar influxd si no está corriendo
$influxProc = Get-Process influxd -ErrorAction SilentlyContinue
if (-not $influxProc) {
    Write-Host "  Arrancando influxd..."
    Start-Process "$INFLUX_DIR\influxd.exe" -WindowStyle Minimized
    Start-Sleep -Seconds 5
    Write-OK "influxd arrancado"
} else {
    Write-OK "influxd ya estaba corriendo"
}

# Setup inicial (solo si no hay datos)
Write-Host "  Configurando InfluxDB (org / bucket / token)..."
try {
    & "$INFLUX_DIR\influx.exe" setup `
        --username $INFLUX_USER `
        --password $INFLUX_PASS `
        --org     $INFLUX_ORG `
        --bucket  $INFLUX_BUCKET `
        --token   $INFLUX_TOKEN `
        --force   2>&1 | Out-Null
    Write-OK "InfluxDB configurado"
} catch {
    Write-Warn "Setup de InfluxDB omitido (probablemente ya estaba configurado)"
}

# ────────────────────────────────────────────────────────────
# 3. GRAFANA
# ────────────────────────────────────────────────────────────
Write-Step "Instalando Grafana $GRAFANA_VERSION..."

$grafanaSvc = Get-Service "Grafana" -ErrorAction SilentlyContinue
if (-not $grafanaSvc) {
    $msiPath = "$env:TEMP\grafana.msi"
    Write-Host "  Descargando Grafana..."
    Invoke-WebRequest $GRAFANA_URL -OutFile $msiPath
    Write-Host "  Instalando (esto tarda ~1 minuto)..."
    Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /quiet" -Wait
    Write-OK "Grafana instalado"
} else {
    Write-OK "Grafana ya instalado"
}

# Arrancar servicio Grafana
Start-Service "Grafana" -ErrorAction SilentlyContinue
Write-OK "Servicio Grafana arrancado → http://localhost:3000"

# ────────────────────────────────────────────────────────────
# 4. DEPENDENCIAS PYTHON
# ────────────────────────────────────────────────────────────
Write-Step "Instalando dependencias Python..."

Set-Location $PROJECT_DIR

Write-Host "  shared library..."
pip install -e shared -q

Write-Host "  API..."
pip install -r api\requirements.txt -q

Write-Host "  server-agent..."
pip install -r agents\server-agent\requirements.txt -q

if (Test-Path "agents\siemens-agent\requirements.txt") {
    Write-Host "  siemens-agent..."
    pip install -r agents\siemens-agent\requirements.txt -q
}

Write-OK "Dependencias instaladas"

# ────────────────────────────────────────────────────────────
# 5. SCRIPTS DE ARRANQUE
# ────────────────────────────────────────────────────────────
Write-Step "Creando scripts de arranque..."

$startApi = @"
@echo off
cd /d "$PROJECT_DIR"
for /f "tokens=1,2 delims==" %%a in (.env) do set %%a=%%b
uvicorn api.src.main:app --host 0.0.0.0 --port 8000 --reload
"@

$startAgent = @"
@echo off
cd /d "$PROJECT_DIR"
for /f "tokens=1,2 delims==" %%a in (.env) do set %%a=%%b
python -m agents.server-agent.src.main
"@

$startSiemens = @"
@echo off
cd /d "$PROJECT_DIR"
for /f "tokens=1,2 delims==" %%a in (.env) do set %%a=%%b
set API_URL=http://localhost:8000
python -m agents.siemens-agent.src.main
"@

$startApi     | Out-File "$PROJECT_DIR\start_api.bat"     -Encoding ascii
$startAgent   | Out-File "$PROJECT_DIR\start_agent.bat"   -Encoding ascii
$startSiemens | Out-File "$PROJECT_DIR\start_siemens.bat" -Encoding ascii

Write-OK "Creados: start_api.bat, start_agent.bat, start_siemens.bat"

# ────────────────────────────────────────────────────────────
# RESUMEN
# ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  Instalacion completada" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  InfluxDB  → http://localhost:8086"
Write-Host "  Grafana   → http://localhost:3000  (admin / $env:GF_SECURITY_ADMIN_PASSWORD)"
Write-Host "  API       → ejecuta start_api.bat"
Write-Host "  Agente    → ejecuta start_agent.bat"
Write-Host ""
Write-Host "Para arrancar todo junto ejecuta cada .bat en una ventana separada."
Write-Host ""
