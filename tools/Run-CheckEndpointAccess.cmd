@echo off
setlocal
REM Запуск диагностики доступности конечного адреса (обход ExecutionPolicy для текущего процесса).
REM Примеры:
REM   Run-CheckEndpointAccess.cmd -Target 10.20.30.40 -PortsFile "%~dp0device-ports.example.csv" -MonitorSeconds 120
REM   Run-CheckEndpointAccess.cmd -Target "https://app.example.local" -Profiles Web

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Check-EndpointAccess.ps1" %*
set "RC=%ERRORLEVEL%"
echo.
echo Exit code: %RC%
if /I "%~1"=="" pause
exit /b %RC%
