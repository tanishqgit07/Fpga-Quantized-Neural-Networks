# Source Vivado 2020.1 + activate the project's Python venv in one shot.
# Usage:   . .\activate.ps1     (note the leading dot — script runs in current shell)

$ErrorActionPreference = "Stop"

$vivadoBat = "C:\Xilinx\Vivado\2020.1\settings64.bat"
if (-not (Test-Path $vivadoBat)) {
    Write-Host "Vivado 2020.1 not found at $vivadoBat" -ForegroundColor Red
    return
}

# Pull the env vars set by settings64.bat into this PS session.
$envDump = cmd /c "`"$vivadoBat`" && set"
foreach ($line in $envDump) {
    if ($line -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
    }
}

# Activate Python venv.
$venvActivate = Join-Path $PSScriptRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
} else {
    Write-Host "venv not found at $venvActivate — skipping" -ForegroundColor Yellow
}

Write-Host "Vivado + venv sourced. Try: vivado_hls -version" -ForegroundColor Green
