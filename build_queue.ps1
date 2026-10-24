# build_queue.ps1 — sequentially build a list of (model, config) bitstreams.
#
# For each entry: clean stale build dir, source Vivado, run main_path_a.py,
# log to build_<config>.log, then move on.
# Failures are logged but don't stop the queue.

param(
    [Parameter(Mandatory = $true)][string[]]$Builds   # e.g. @('nid:low_mixed','ecg_v1:high_mixed_rf2')
)

$root = $PSScriptRoot
$ErrorActionPreference = "Continue"

# Source Vivado once for the whole queue
$envDump = cmd /c "`"C:\Xilinx\Vivado\2020.1\settings64.bat`" && set"
foreach ($line in $envDump) {
    if ($line -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
    }
}
$env:TF_USE_LEGACY_KERAS = "1"

$summary = @()
foreach ($b in $Builds) {
    $parts  = $b.Split(':', 2)
    $model  = $parts[0]
    $config = $parts[1]
    $dir    = "$root\$model"
    $proj   = "$dir\hls_project_${config}_a"

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "BUILD: $model / $config" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan

    if (Test-Path $proj) { Remove-Item -Recurse -Force $proj }

    Set-Location $dir
    $started = Get-Date
    & "$root\.venv\Scripts\python.exe" main_path_a.py "configs.$config" 2>&1 | Tee-Object -FilePath "build_${config}.log" | Out-Null
    $ended = Get-Date

    # Verify bit + hwh produced (regardless of script's success report which
    # uses the wrong path for the post-build copy)
    $bit = Get-ChildItem -Path $proj -Recurse -Filter "design_1_wrapper.bit" -ErrorAction SilentlyContinue | Select-Object -First 1
    $hwh = Get-ChildItem -Path $proj -Recurse -Filter "design_1.hwh"         -ErrorAction SilentlyContinue | Select-Object -First 1

    if ($bit -and $hwh) {
        $dep = "$dir\deploy\$config"
        New-Item -ItemType Directory -Force -Path $dep | Out-Null
        Copy-Item $bit.FullName "$dep\$config.bit" -Force
        Copy-Item $hwh.FullName "$dep\$config.hwh" -Force
        $drv = "$proj\axi_stream_driver.py"
        if (Test-Path $drv) { Copy-Item $drv "$dep\axi_stream_driver.py" -Force }

        $proj_name = "${model}_${config}"
        & "$root\.venv\Scripts\python.exe" "$root\rename_vivado_project.py" "$proj\myproject_vivado_accelerator" $proj_name | Out-Null

        $dur = ($ended - $started).TotalMinutes
        Write-Host "OK   $model/$config  ($([math]::Round($dur,1)) min)" -ForegroundColor Green
        $summary += "OK   $model/$config  $([math]::Round($dur,1))min  bit=$($bit.Length)B"
    } else {
        $dur = ($ended - $started).TotalMinutes
        Write-Host "FAIL $model/$config  ($([math]::Round($dur,1)) min) — check build_${config}.log" -ForegroundColor Red
        $summary += "FAIL $model/$config  $([math]::Round($dur,1))min"
    }
}

Write-Host ""
Write-Host "=================== QUEUE SUMMARY ===================" -ForegroundColor Cyan
$summary | ForEach-Object { Write-Host $_ }
