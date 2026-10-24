# Path B — Transfer to arush's laptop and run

## Files in this staging directory

```
hls4ml_path_b_staging/
├── main.py                              # replaces ~/DD_proj_new_env/main.py
├── deploy.tcl                           # replaces ~/DD_proj_new_env/deploy.tcl
├── build_bitstream.sh                   # NEW — standalone bitstream builder
└── ip_repo/
    └── tlast_gen/
        ├── src/tlast_gen.v              # NEW — TLAST-on-Nth-beat AXI-Stream IP
        └── package_tlast_gen.tcl        # NEW — packages tlast_gen.v as Vivado IP
```

## Two-step flow (no file patching)

`main.py` only does HLS — same as before. Bitstream is built by a separate script.
Each step regenerates everything fresh; no in-place edits to project files.

```
python3 main.py configs.uniform_8bit       # HLS → packaged IP
./build_bitstream.sh    uniform_8bit       # IP → block design → bitstream
```

## Transfer to arush's laptop

```bash
scp -r ~/hls4ml_path_b_staging/* arush@<arush-ip>:~/DD_proj_new_env/
```

Or zip → email/USB → unzip into `~/DD_proj_new_env/`.

After landing, the project folder looks like:

```
~/DD_proj_new_env/
├── main.py                              # OVERWRITTEN
├── deploy.tcl                           # OVERWRITTEN (the broken one is gone)
├── build_bitstream.sh                   # NEW
├── ip_repo/tlast_gen/                   # NEW
├── model.h5, X_test.npy, y_test.npy     # untouched
├── configs/                             # untouched
└── ... (other existing files)           # untouched
```

## One-time setup on arush's laptop

```bash
cd ~/DD_proj_new_env

# 1. Source the Xilinx toolchain
source /tools/Xilinx/Vivado/2025.2/settings64.sh
which vivado vitis_hls           # both should resolve

# 2. Make build_bitstream.sh executable
chmod +x build_bitstream.sh

# 3. Package the tlast_gen IP (one-time per Vivado version)
cd ip_repo/tlast_gen
vivado -mode batch -source package_tlast_gen.tcl
cd ../..
ls ip_repo/tlast_gen/component.xml      # must exist after this step
```

## Building one config

Two commands, in order:

```bash
cd ~/DD_proj_new_env

# Step 1: HLS — generates hls_project_uniform_8bit/
python3 main.py configs.uniform_8bit

# Step 2: bitstream — generates hls_project_uniform_8bit/vivado_proj/
#         and copies .bit/.hwh into deploy/uniform_8bit/
./build_bitstream.sh uniform_8bit
```

`main.py` does NOT touch `deploy.tcl`, does NOT invoke Vivado, and does NOT
modify any of the files it generates. `build_bitstream.sh` operates only on
the freshly-produced HLS IP and produces a fresh Vivado project.

Wall time: HLS ~5–10 min, Vivado ~10–25 min.

## Building all configs

```bash
for cfg in uniform_8bit low_mixed high_mixed_rf2; do
    python3 main.py configs.$cfg
    ./build_bitstream.sh $cfg
done
# skip high_mixed_rf1 — over DSP budget
```

## Deploying to the board

```bash
scp deploy/uniform_8bit/uniform_8bit.bit  xilinx@192.168.2.99:/home/xilinx/
scp deploy/uniform_8bit/uniform_8bit.hwh  xilinx@192.168.2.99:/home/xilinx/
```

`.bit` and `.hwh` filenames must match (PYNQ requirement).

On the board:
```python
from pynq import Overlay, allocate
import numpy as np

overlay = Overlay("/home/xilinx/uniform_8bit.bit")
dma = overlay.axi_dma_0
mmio = dma.mmio

# Diagnostic — confirms the reset bug is fixed.
print("MM2S DMASR:", hex(mmio.read(0x04)))   # expect 0x00010000 (Halted=1)
print("S2MM DMASR:", hex(mmio.read(0x34)))   # expect 0x00010000 (Halted=1)

# Run inference (ap_fixed<8,4> encoding)
X = np.load("X_test.npy")
in_buf  = allocate(shape=(16,), dtype=np.int8)
out_buf = allocate(shape=(1,),  dtype=np.int8)
in_buf[:] = (X[0] * 16).astype(np.int8)      # encode: x * 2**(W-I) = x * 16

dma.sendchannel.transfer(in_buf)
dma.recvchannel.transfer(out_buf)
dma.sendchannel.wait()
dma.recvchannel.wait()

print("Inference (decoded):", int(out_buf[0]) / 16.0)
```

If `dma.sendchannel.wait()` returns without `RuntimeError` and `DMASR` reads
flip from `0x00010000` (Halted=1) → `0x00000002` (Idle=1) after `RS=1` is
written → `0x00001002` after each transfer completes, the reset bug is fixed.

## What changed and why

| File | Before | After |
|---|---|---|
| `main.py` | HLS only (working as-is) | HLS only (unchanged behavior — does NOT modify any file or invoke Vivado) |
| `deploy.tcl` | Built BD with no DMA, no stream connections — bitstreams in `bitstreams/` are unusable | Full BD: PS + DMA + SmartConnect + properly-wired resets + tlast_gen + xlconstant for ap_start + hls4ml IP |
| `build_bitstream.sh` | did not exist | Standalone script that runs Vivado against `deploy.tcl` and copies `.bit`/`.hwh` into `deploy/<config>/` |
| `ip_repo/tlast_gen/` | did not exist | Tiny Verilog AXI-Stream IP that asserts TLAST every PACKET_SIZE beats. Replaces the `axis_subset_converter` band-aid that was forcing TLAST=1 every beat (truncating receives to 1 byte) |

## The bug fixed by the new `deploy.tcl`

The current blocker (`DMASR=0x0` on both channels, `RuntimeError: DMA channel not started`)
is caused by `axi_dma_0/axi_resetn` being unwired or wired to the wrong reset in the manual BD.
With the datapath held in reset, all DMA registers read 0 and writes don't stick. The new
`deploy.tcl` wires `proc_sys_reset_0/peripheral_aresetn` to **all** of:

- `axi_dma_0/axi_resetn`
- `axi_dma_0/s_axi_lite_aresetn`
- `myproject_0/ap_rst_n`
- `tlast_gen_0/aresetn`
- `sc_ctrl/aresetn`
- `sc_data/aresetn`

`ap_start` is still tied high via `xlconstant` (same as before), and `tlast_gen_0`
replaces the `axis_subset_converter` for clean TLAST handling. The IP-level firmware
is **not modified** — every artifact in `hls_project_<config>/` is whatever hls4ml
generated, untouched.

## If something fails

| Symptom | Likely cause / fix |
|---|---|
| `vivado: command not found` | `source /tools/Xilinx/Vivado/2025.2/settings64.sh` |
| `latest_ip_vlnv` errors out for `axi_dma`/`smartconnect` | IP catalog not refreshed. Run with a clean `hls_project_*/vivado_proj/` directory (the script wipes it on each run) |
| `latest_ip_vlnv` errors out for `tlast_gen` or `myproject` | Either `package_tlast_gen.tcl` was not run, or HLS didn't finish. Check `ip_repo/tlast_gen/component.xml` and `hls_project_<config>/myproject_prj/solution1/impl/ip/component.xml` exist |
| `BOARD_PART tul.com.tw:pynq-z2:part0:1.0` warning | Harmless — board file not installed; deploy.tcl falls back to part-only |
| `apply_bd_automation` fails on `ps7` | Vivado 2025.2 may have removed the legacy automation rule. Hand-set `CONFIG.PCW_*` properties |
| Synth/impl times out at 4 jobs | Edit `deploy.tcl`: drop `-jobs 4` or set to your laptop's core count |
| Want to re-run only the bitstream step | Just run `./build_bitstream.sh <config>` again — it wipes `vivado_proj/` and rebuilds. No need to re-run `main.py` unless you changed the config |
