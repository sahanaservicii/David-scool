@echo off
cd /d "%~dp0"
call run.cmd serve --host 0.0.0.0 --open %*
