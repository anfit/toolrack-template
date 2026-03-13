@echo off
setlocal

set "REPO_ROOT=%~dp0.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"

set "TOOLRACK_CLI_NAME=%~n0"
set "TOOLRACK_REPO_ROOT=%REPO_ROOT%"
set "TOOLRACK_SCRIPTS_ROOT=%REPO_ROOT%\scripts"
set "TOOLRACK_REGISTRY_FILE=%REPO_ROOT%\.toolrack"

"%REPO_ROOT%\.venv\Scripts\python.exe" -m toolrack %*
