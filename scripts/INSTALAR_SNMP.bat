@echo off
:: Solicitar permisos de administrador automaticamente
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Solicitando permisos de administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo ============================================================
echo   Configuracion de monitorización GEA Health Status
echo ============================================================
echo.
echo Instalando y configurando el servicio SNMP...
echo (Esto puede tardar 1-2 minutos la primera vez)
echo.

:: Instalar SNMP si no está instalado
powershell -Command "Add-WindowsCapability -Online -Name 'SNMP.Client~~~~0.0.1.0' 2>$null; $null" 2>nul

:: Configurar community "public" (solo lectura)
reg add "HKLM\SYSTEM\CurrentControlSet\Services\SNMP\Parameters\ValidCommunities" /v "public" /t REG_DWORD /d 4 /f >nul 2>&1
reg add "HKLM\SYSTEM\CurrentControlSet\Services\SNMP\Parameters\PermittedManagers" /f >nul 2>&1

:: Abrir firewall para el agente de monitorización
netsh advfirewall firewall delete rule name="SNMP Monitoring GEA" >nul 2>&1
netsh advfirewall firewall add rule name="SNMP Monitoring GEA" dir=in action=allow protocol=UDP localport=161

:: Arrancar el servicio
sc config SNMP start= auto >nul
net stop SNMP >nul 2>&1
net start SNMP >nul 2>&1

:: Verificar resultado
sc query SNMP | findstr "RUNNING" >nul
if %errorLevel% equ 0 (
    echo.
    echo  OK  Este equipo esta listo para ser monitorizado.
    echo.
) else (
    echo.
    echo  ERROR  No se pudo arrancar el servicio SNMP.
    echo         Contacte con el administrador de sistemas.
    echo.
)

pause
