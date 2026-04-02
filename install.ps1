$ErrorActionPreference = "Stop"

$repoBase = "https://raw.githubusercontent.com/TheBeaconCrafter/zen-sync/main"
$binDir = Join-Path $HOME ".local\bin"
$libDir = Join-Path $HOME ".local\lib\zen-sync"

New-Item -ItemType Directory -Force -Path $binDir | Out-Null
New-Item -ItemType Directory -Force -Path $libDir | Out-Null

Invoke-WebRequest -Uri "$repoBase/zen-sync" -OutFile (Join-Path $binDir "zen-sync")
Invoke-WebRequest -Uri "$repoBase/merge.py" -OutFile (Join-Path $libDir "merge.py")
Invoke-WebRequest -Uri "$repoBase/cloud.py" -OutFile (Join-Path $libDir "cloud.py")
Invoke-WebRequest -Uri "$repoBase/storagebox.py" -OutFile (Join-Path $libDir "storagebox.py")
Invoke-WebRequest -Uri "$repoBase/merge.py" -OutFile (Join-Path $binDir "merge.py")
Invoke-WebRequest -Uri "$repoBase/cloud.py" -OutFile (Join-Path $binDir "cloud.py")
Invoke-WebRequest -Uri "$repoBase/storagebox.py" -OutFile (Join-Path $binDir "storagebox.py")

$cmd = @'
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
'@
Set-Content -Path (Join-Path $binDir "zen-sync.cmd") -Value $cmd -Encoding ascii

Write-Host "Installed zen-sync to $binDir\zen-sync"

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ([string]::IsNullOrWhiteSpace($userPath)) {
    $userPath = ""
}

$escapedBin = [Regex]::Escape($binDir)
if ($userPath -notmatch "(^|;)$escapedBin(;|$)") {
    $newPath = if ($userPath) { "$binDir;$userPath" } else { $binDir }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "Added $binDir to your user PATH. Restart your terminal to use zen-sync."
}

if (-not (Get-Command bash -ErrorAction SilentlyContinue)) {
    Write-Warning "bash not found in PATH. Install Git Bash or WSL before running zen-sync."
}

Write-Host "Run 'zen-sync init' to get started."
Write-Host "For R2/StorageBox cloud modes, also install: age"
