# NID Project — NSL-KDD on PYNQ-Z2

Self-contained sister project to the ECG arrhythmia classifier. Same flow,
different model and dataset. Drop the whole `nid_project/` directory onto
arush's laptop as e.g. `~/DD_proj_nid/` and the commands below run as-is.

## Architecture

```
41 features → Dense(64, ReLU) → Dense(32, ReLU) → Dense(1, sigmoid)
```

Layer names match the ECG project (`dense1`, `dense2`, `output`,
`layer7_out`) so the configs/*.py schema is shared.

## Files

| File | Role |
|---|---|
| `prep_nsl_kdd.py` | Auto-downloads NSL-KDD, preprocesses to 41-feature `.npy` files |
| `model.py` | Float Keras baseline (accuracy ceiling) |
| `train_qkeras_nid.py` | QAT (`quantized_bits(8,4)`) + 50% pruning. Outputs `model_qkeras.h5` |
| `main.py` | hls4ml conversion + HLS synth + IP export |
| `deploy.tcl` | Block-design construction. Auto-reads stream widths from IP `component.xml` |
| `build_bitstream.sh` | Wrapper around Vivado batch invocation; handles per-config widths |
| `run_inference.py` | On-board inference with per-config precision table |
| `configs/uniform_8bit.py` | All-`ap_fixed<8,4>`, RF=1 |
| `configs/low_mixed.py` | `ap_fixed<6,2>` weights, `<12,6>` activations, RF=1 |
| `configs/high_mixed_rf1.py` | `ap_fixed<12,6>`/`<16,8>` mixed, RF=1 (likely over DSP budget) |
| `configs/high_mixed_rf2.py` | Same precisions as rf1, RF=2 (fits) |
| `ip_repo/tlast_gen/` | Tiny Verilog AXI-Stream IP that asserts TLAST every PACKET_SIZE beats |

## Pipeline

### One-time setup

```bash
cp -r ~/Downloads/hls4ml_path_b_staging/nid_project ~/DD_proj_nid
cd ~/DD_proj_nid

# Make scripts executable
chmod +x build_bitstream.sh

# Source the toolchain
source /tools/Xilinx/Vivado/2025.2/settings64.sh
which vivado vitis_hls

# Install training-side deps once
pip install qkeras tensorflow-model-optimization

# Package the tlast_gen IP (one-time per Vivado version)
cd ip_repo/tlast_gen
vivado -mode batch -source package_tlast_gen.tcl
cd ../..
```

### Data prep

```bash
python3 prep_nsl_kdd.py
# Produces: X_train.npy, y_train.npy, X_test.npy, y_test.npy,
#           scaler_mean.npy, scaler_std.npy
```

### Training

```bash
# Float baseline (sanity check)
TF_USE_LEGACY_KERAS=1 python3 model.py
# → model.h5

# Deployable QKeras + pruned model
TF_USE_LEGACY_KERAS=1 python3 train_qkeras_nid.py
# → model_qkeras.h5
```

### HLS conversion + bitstream

```bash
# Edit MODEL_PATH at the top of main.py if you want the float baseline
# (default is "model_qkeras.h5")

for cfg in uniform_8bit low_mixed high_mixed_rf2; do
    python3 main.py configs.$cfg
    ./build_bitstream.sh $cfg
done
# Skip high_mixed_rf1 unless QKeras+pruning brought DSP usage under 220.
```

### Deploy to board

```bash
for cfg in uniform_8bit low_mixed high_mixed_rf2; do
    scp deploy/$cfg/$cfg.bit  xilinx@192.168.2.99:/home/xilinx/nid_$cfg.bit
    scp deploy/$cfg/$cfg.hwh  xilinx@192.168.2.99:/home/xilinx/nid_$cfg.hwh
done
scp X_test.npy   xilinx@192.168.2.99:/home/xilinx/X_test_nid.npy
scp y_test.npy   xilinx@192.168.2.99:/home/xilinx/y_test_nid.npy
scp run_inference.py xilinx@192.168.2.99:/home/xilinx/run_inference_nid.py
```

The `nid_` prefix on bitstream filenames keeps NID and ECG bitstreams from
colliding on the board.

### On-board inference

```bash
ssh xilinx@192.168.2.99
python3 /home/xilinx/run_inference_nid.py
```

Edit `CONFIG = "uniform_8bit"` at the top of `run_inference_nid.py` to switch
which bitstream gets tested.

## Expected accuracy (literature range, not measured here)

Canonical KDDTrain+ → KDDTest+ split (what `prep_nsl_kdd.py` produces).

| Stage | Typical test accuracy on NSL-KDD binary |
|---|---|
| Float Keras MLP | 0.78 – 0.83 |
| QAT `quantized_bits(8,4)` | 0.76 – 0.81 |
| QAT + 30% pruning | similar |

NSL-KDD's test set intentionally contains attack types not seen during
training. Test accuracy ceilings are around 0.83 regardless of model size.
For a >95% headline number, swap `prep_nsl_kdd.py` for **UNSW-NB15** or
**CIC-IDS-2017** preprocessing — same pipeline, same model, different
dataset.

## How `deploy.tcl` works for this project

The deploy.tcl is **identical** to the ECG project's. Both projects use the
same layer naming convention (`dense1_input` for the input AXI Stream,
`layer7_out` for the output), so:

1. `build_bitstream.sh` extracts the stream widths from the IP's
   `component.xml` (these vary by precision config: 41 × 8 = 328 bits for
   uniform_8bit, 41 × 16 = 656 bits for high_mixed configs).
2. Passes them to `deploy.tcl` as TCL args.
3. `deploy.tcl` configures the AXI DMA's stream widths to match the IP, sets
   `tlast_gen_0/DATA_WIDTH` to match the output stream, and wires the BD.
4. Vivado synthesizes and writes the bitstream.

Stream widths are not hardcoded anywhere — that's why the same scripts work
for both 16-feature ECG and 41-feature NID without changes.

## Resource expectations on Z-7020

NID's first dense layer is 41 → 64 = 2624 MACs (vs ECG's 16 → 32 = 512). The
whole NID network has ~4768 MACs vs ECG's 1040 — about 4.5× larger.

| Config | LUT (rough) | DSP | Notes |
|---|---|---|---|
| uniform_8bit | ~22k (~41%) | 0 | 8-bit MACs in LUTs, plenty of headroom |
| low_mixed | ~17k (~32%) | 0 | smallest |
| high_mixed_rf1 | likely > 220 DSPs | over budget | needs pruning to fit |
| high_mixed_rf2 | ~30k LUTs | ~160 DSPs | tight but fits |

These are estimates from the LUT-per-MAC heuristic; check
`hls_project_<config>/.../myproject_csynth.rpt` for actuals after each
build.
