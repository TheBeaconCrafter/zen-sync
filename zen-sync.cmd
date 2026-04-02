@echo off
setlocal

where bash >nul 2>nul
if errorlevel 1 (
  echo [zen-sync] bash was not found in PATH.
  echo Install Git Bash or WSL, then run again.
  exit /b 1
)

pushd "%~dp0"
set "ZEN_SYNC_LIB_DIR=%USERPROFILE%\.local\lib\zen-sync"
bash ./zen-sync %*
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
