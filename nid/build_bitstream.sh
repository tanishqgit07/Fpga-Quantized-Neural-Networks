#!/usr/bin/env bash
# build_bitstream.sh
#
# Standalone bitstream builder. Run AFTER `python3 main.py configs.<name>`
# has produced the hls4ml IP. Generates everything fresh.
#
# This version reads the IP's actual AXI Stream widths from its
# component.xml and passes them to deploy.tcl, so each config gets a DMA
# wired to the right widths (different precisions = different stream widths).
#
# Usage:
#   ./build_bitstream.sh <config_name>
#
# Produces:
#   deploy/<config_name>/<config_name>.bit
#   deploy/<config_name>/<config_name>.hwh

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <config_name>"
    echo "Example: $0 uniform_8bit"
    exit 1
fi

CONFIG="$1"
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
HLS_OUTPUT_DIR="$PROJECT_ROOT/hls_project_${CONFIG}"
HLS_IP_DIR="$HLS_OUTPUT_DIR/myproject_prj/solution1/impl/ip"
TLAST_IP_DIR="$PROJECT_ROOT/ip_repo/tlast_gen"
DEPLOY_DIR="$PROJECT_ROOT/deploy/${CONFIG}"

if [[ ! -d "$HLS_IP_DIR" ]]; then
    echo "ERROR: hls4ml IP not found at: $HLS_IP_DIR"
    echo "Run 'python3 main.py configs.${CONFIG}' first."
    exit 1
fi

if [[ ! -f "$TLAST_IP_DIR/component.xml" ]]; then
    echo "ERROR: tlast_gen IP not packaged at: $TLAST_IP_DIR"
    echo "Run: cd $TLAST_IP_DIR && vivado -mode batch -source package_tlast_gen.tcl"
    exit 1
fi

if ! command -v vivado >/dev/null 2>&1; then
    echo "ERROR: vivado not found. Run: source /tools/Xilinx/Vivado/2025.2/settings64.sh"
    exit 1
fi

# ----------------------------------------------------------------------
# Parse the hls4ml IP's component.xml to find AXI Stream widths.
# Different configs (different precisions) yield different stream widths;
# the DMA must match or the IP receives garbled data.
# ----------------------------------------------------------------------
extract_tdata_bytes() {
    local interface_name_upper="$1"
    local xml="$HLS_IP_DIR/component.xml"
    grep "BUSIFPARAM_VALUE.${interface_name_upper}.TDATA_NUM_BYTES" "$xml" \
        | sed -n 's/.*>\([0-9]\+\)<.*/\1/p' \
        | head -1
}

IN_BYTES=$(extract_tdata_bytes DENSE1_INPUT)
OUT_BYTES=$(extract_tdata_bytes LAYER7_OUT)

if [[ -z "$IN_BYTES" || -z "$OUT_BYTES" ]]; then
    echo "ERROR: could not parse TDATA_NUM_BYTES from $HLS_IP_DIR/component.xml"
    echo "       IN_BYTES='$IN_BYTES'  OUT_BYTES='$OUT_BYTES'"
    exit 1
fi

echo "----------------------------------------"
echo "Building bitstream for: $CONFIG"
echo "  hls_ip_dir   = $HLS_IP_DIR"
echo "  tlast_ip_dir = $TLAST_IP_DIR"
echo "  output_dir   = $HLS_OUTPUT_DIR"
echo "  IP stream widths: input=${IN_BYTES} bytes, output=${OUT_BYTES} bytes"
echo "----------------------------------------"

cd "$HLS_OUTPUT_DIR"

vivado -mode batch \
    -source "$PROJECT_ROOT/deploy.tcl" \
    -tclargs "$CONFIG" "$HLS_IP_DIR" "$TLAST_IP_DIR" "$HLS_OUTPUT_DIR" \
             "$IN_BYTES" "$OUT_BYTES"

# Package fresh artifacts
BIT_SRC="$HLS_OUTPUT_DIR/vivado_proj/vivado_proj.runs/impl_1/design_1_wrapper.bit"
HWH_SRC="$HLS_OUTPUT_DIR/vivado_proj/vivado_proj.gen/sources_1/bd/design_1/hw_handoff/design_1.hwh"

if [[ ! -f "$BIT_SRC" || ! -f "$HWH_SRC" ]]; then
    echo "ERROR: build did not produce .bit and .hwh"
    exit 1
fi

mkdir -p "$DEPLOY_DIR"
cp "$BIT_SRC" "$DEPLOY_DIR/${CONFIG}.bit"
cp "$HWH_SRC" "$DEPLOY_DIR/${CONFIG}.hwh"

echo "----------------------------------------"
echo "Done."
echo "  $DEPLOY_DIR/${CONFIG}.bit"
echo "  $DEPLOY_DIR/${CONFIG}.hwh"
echo "  Stream widths recorded:  input=${IN_BYTES}B  output=${OUT_BYTES}B"
echo "----------------------------------------"
echo "Deploy:"
echo "  scp $DEPLOY_DIR/${CONFIG}.{bit,hwh} xilinx@192.168.2.99:/home/xilinx/"
