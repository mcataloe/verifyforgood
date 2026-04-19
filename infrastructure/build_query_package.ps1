param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$moduleDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $moduleDir "..")
$buildRoot = Join-Path $moduleDir "build"
$packageDir = Join-Path $buildRoot "query_package"
$tempRequirements = Join-Path $buildRoot "query_requirements.txt"

if (Test-Path $packageDir) {
    Remove-Item -Recurse -Force $packageDir
}

New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

$requirementsPath = Join-Path $moduleDir "requirements.txt"
$packageRequirements = Get-Content $requirementsPath | Where-Object {
    $line = $_.Trim()
    $line -and -not $line.StartsWith("#") -and $line -ne "boto3"
}

if ($packageRequirements.Count -gt 0) {
    Set-Content -Path $tempRequirements -Value $packageRequirements -Encoding ascii
    & $PythonExe -m pip install `
        -r $tempRequirements `
        --target $packageDir `
        --only-binary=:all: `
        --platform manylinux2014_x86_64 `
        --implementation cp `
        --python-version 311
    Remove-Item -Force $tempRequirements
}

Copy-Item -Path (Join-Path $moduleDir "lambda_query.py") -Destination $packageDir -Force
Copy-Item -Path (Join-Path $moduleDir "verification") -Destination $packageDir -Recurse -Force
Copy-Item -Path (Join-Path $moduleDir "verification_platform") -Destination $packageDir -Recurse -Force
Copy-Item -Path (Join-Path $repoRoot "private-platform\\src\\verification_platform") -Destination $packageDir -Recurse -Force

Get-ChildItem -Path $packageDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $packageDir -Recurse -Include *.pyc, *.pyo -File | Remove-Item -Force

Write-Host "Query package prepared at $packageDir"

