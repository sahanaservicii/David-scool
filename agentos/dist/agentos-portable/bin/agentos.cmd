@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if exist "runtime\python-win64\python.exe" (
  "runtime\python-win64\python.exe" -m agentos %*
) else (
  where py >nul 2>nul
  if errorlevel 1 (
    python -m agentos %*
  ) else (
    py -3 -m agentos %*
  )
)
