#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Prepara un servidor Windows para ser monitorizado por el agente SNMP del TFG.
    Ejecutar una sola vez en cada servidor objetivo (por el equipo de IT/OT).

.DESCRIPTION
    1. Instala el feature SNMP de Windows (si no está instalado)
    2. Configura la community string "public" (solo lectura)
    3. Abre el firewall para el servidor de monitorización
    4. Arranca y fija el servicio SNMP en inicio automático

.PARAMETER MonitoringServerIP
    IP del servidor donde corre el agente (default: cualquier IP)

.PARAMETER Community
    SNMP community string (default: public)

.EXAMPLE
    .\enable_snmp_target.ps1 -MonitoringServerIP 10.10.1.50
    .\enable_snmp_target.ps1   # permite cualquier IP (solo para entornos controlados)
#>
param(
    [string]$MonitoringServerIP = "Any",
    [string]$Community = "public"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/4] Verificando feature SNMP..." -ForegroundColor Cyan
$feature = Get-WindowsOptionalFeature -Online -FeatureName "SNMP" -ErrorAction SilentlyContinue
if ($feature -and $feature.State -eq "Enabled") {
    Write-Host "      SNMP ya instalado." -ForegroundColor Green
} else {
    Write-Host "      Instalando SNMP..." -ForegroundColor Yellow
    Add-WindowsCapability -Online -Name "SNMP.Client~~~~0.0.1.0" | Out-Null
    Write-Host "      Instalado." -ForegroundColor Green
}

Write-Host "[2/4] Configurando community '$Community' (read-only)..." -ForegroundColor Cyan
$commPath = "HKLM:\SYSTEM\CurrentControlSet\Services\SNMP\Parameters\ValidCommunities"
if (-not (Test-Path $commPath)) {
    New-Item -Path $commPath -Force | Out-Null
}
New-ItemProperty -Path $commPath -Name $Community -Value 4 -PropertyType DWord -Force | Out-Null

# PermittedManagers vacío = acepta cualquier host (restringir en producción)
$mgrsPath = "HKLM:\SYSTEM\CurrentControlSet\Services\SNMP\Parameters\PermittedManagers"
if (-not (Test-Path $mgrsPath)) {
    New-Item -Path $mgrsPath -Force | Out-Null
}
Write-Host "      Community configurada." -ForegroundColor Green

Write-Host "[3/4] Abriendo firewall UDP 161..." -ForegroundColor Cyan
Remove-NetFirewallRule -DisplayName "SNMP Monitoring Agent" -ErrorAction SilentlyContinue
New-NetFirewallRule `
    -DisplayName "SNMP Monitoring Agent" `
    -Direction Inbound `
    -Protocol UDP `
    -LocalPort 161 `
    -Action Allow `
    -RemoteAddress $MonitoringServerIP | Out-Null
Write-Host "      Regla creada (origen: $MonitoringServerIP)." -ForegroundColor Green

Write-Host "[4/4] Arrancando servicio SNMP..." -ForegroundColor Cyan
Set-Service -Name SNMP -StartupType Automatic
Restart-Service -Name SNMP -Force
$svc = Get-Service SNMP
Write-Host "      Servicio: $($svc.Status)" -ForegroundColor Green

Write-Host ""
Write-Host "Listo. Este servidor es visible para el agente de monitorización." -ForegroundColor Green
Write-Host "Verificar con: snmpget -v2c -c $Community <IP-de-este-servidor> 1.3.6.1.2.1.1.3.0" -ForegroundColor Gray
