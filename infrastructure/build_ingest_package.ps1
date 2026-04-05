param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$moduleDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildRoot = Join-Path $moduleDir "build"
$packageDir = Join-Path $buildRoot "ingest_package"

if (Test-Path $packageDir) {
    Remove-Item -Recurse -Force $packageDir
}

New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

& $PythonExe -m pip install -r (Join-Path $moduleDir "requirements.txt") -t $packageDir

Copy-Item -Path (Join-Path $moduleDir "eo_bmf_ingest_worker.py") -Destination $packageDir -Force

Write-Host "Ingest package prepared at $packageDir"
