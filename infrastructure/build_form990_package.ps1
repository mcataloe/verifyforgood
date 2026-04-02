param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$moduleDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $moduleDir "..")
$buildRoot = Join-Path $moduleDir "build"
$packageDir = Join-Path $buildRoot "form990_package"

if (Test-Path $packageDir) {
    Remove-Item -Recurse -Force $packageDir
}

New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

Copy-Item -Path (Join-Path $moduleDir "lambda_form990.py") -Destination $packageDir -Force
Copy-Item -Path (Join-Path $moduleDir "lambda_form990_orchestrator.py") -Destination $packageDir -Force
Copy-Item -Path (Join-Path $moduleDir "lambda_form990_worker.py") -Destination $packageDir -Force
Copy-Item -Path (Join-Path $moduleDir "lambda_monthly_ingest_staging.py") -Destination $packageDir -Force
Copy-Item -Path (Join-Path $moduleDir "charity_status") -Destination $packageDir -Recurse -Force
Copy-Item -Path (Join-Path $repoRoot "private-platform\\src\\charity_status_platform") -Destination $packageDir -Recurse -Force
Copy-Item -Path (Join-Path $repoRoot "backend\\ingest-task\\src\\charity_status_backend") -Destination $packageDir -Recurse -Force

Get-ChildItem -Path $packageDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $packageDir -Recurse -Include *.pyc, *.pyo -File | Remove-Item -Force

Write-Host "Form 990 package prepared at $packageDir"
