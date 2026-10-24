# package_for_board.ps1 — bundle everything needed to test ONE bitstream on the
# PYNQ-Z2 into a single self-contained directory you can scp in one go.
#
# Usage:
#   .\board\package_for_board.ps1 ecg_v1 uniform_8bit
#   .\board\package_for_board.ps1 ecg_v2 low_mixed
#   .\board\package_for_board.ps1 nid    uniform_8bit
#
# Produces:  <repo>\board_pkg\<model>_<config>\
#            ├── <config>.bit
#            ├── <config>.hwh
#            ├── X_test.npy
#            ├── y_test.npy
#            ├── run_inference.ipynb   (pre-configured for this model)
#            └── README.md

param(
    [Parameter(Mandatory = $true)][string]$Model,   # ecg_v1 | ecg_v2 | nid
    [Parameter(Mandatory = $true)][string]$Config   # uniform_8bit | low_mixed | ...
)

$root = Split-Path $PSScriptRoot -Parent
$bit  = "$root\$Model\deploy\$Config\$Config.bit"
$hwh  = "$root\$Model\deploy\$Config\$Config.hwh"
$xtest = "$root\$Model\X_test.npy"
$ytest = "$root\$Model\y_test.npy"

foreach ($p in @($bit, $hwh, $xtest, $ytest)) {
    if (-not (Test-Path $p)) {
        Write-Host "MISSING: $p" -ForegroundColor Red
        exit 1
    }
}

$dim_map = @{ 'ecg_v1' = 16; 'ecg_v2' = 64; 'nid' = 41 }
$input_dim = $dim_map[$Model]
if (-not $input_dim) {
    Write-Host "Unknown model '$Model'. Must be ecg_v1, ecg_v2, or nid." -ForegroundColor Red
    exit 1
}

$pkg = "$root\board_pkg\${Model}_${Config}"
New-Item -ItemType Directory -Force -Path $pkg | Out-Null

Copy-Item $bit, $hwh, $xtest, $ytest, "$root\board\README.md" $pkg -Force

# Pre-configure the notebook for this model by patching the first config cell
$nb = Get-Content "$root\board\run_inference.ipynb" -Raw
$nb = $nb -replace "CONFIG\s+=\s+'[^']+'", "CONFIG       = '$Config'"
$nb = $nb -replace "INPUT_DIM\s+=\s+\d+", "INPUT_DIM    = $input_dim"
$nb | Out-File "$pkg\run_inference.ipynb" -Encoding utf8

Write-Host "Packaged at: $pkg" -ForegroundColor Green
Get-ChildItem $pkg | Format-Table Name, Length -AutoSize

Write-Host ""
Write-Host "To copy to the board:" -ForegroundColor Cyan
Write-Host "  scp -r '$pkg' xilinx@<BOARD_IP>:~/" -ForegroundColor Cyan
