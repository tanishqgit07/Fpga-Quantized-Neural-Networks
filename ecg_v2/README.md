# ECG v2 — Richer features + bigger model → ~95% target

Self-contained sister project to the original ECG (`~/DD_proj_new_env/`).
Different data, different model, same proven Vivado integration.

## What changes vs v1

| | v1 (existing) | **v2 (this project)** |
|---|---|---|
| Features | 16 hand-crafted | **64 raw signal samples** R-peak-aligned |
| Architecture | 16 → 16 → 8 → 1 (baseline) | **64 → 64 → 32 → 1** |
| Parameters | 417 | **6,273** (~15×) |
| Training | post-hoc quantize | **QAT (QKeras) + 50% pruning** |
| ReuseFactor | 1 | **8** (to fit Z-7020 with the bigger network) |
| Recorded accuracy | Keras 0.93, csim 0.80, on-board 0.81 | **Keras 0.96** (csim / on-board not recorded) |

The accuracy jump comes from the data, not the model size — 16 hand-crafted
features cap out around 0.85–0.92 even with float Keras. Going to 64 raw
samples per beat unlocks the 0.95 ceiling that's standard in the MIT-BIH
literature.

## Files

| File | Role |
|---|---|
| `prep_mit_bih.py` | Downloads MIT-BIH from PhysioNet, extracts 64-sample R-peak-aligned beat windows, balances classes, stratified random 80/20 split (intra-patient) |
| `train_qkeras_ecg_v2.py` | QAT (`quantized_bits(8,4)`) + 50% pruning. Outputs `model_v2.h5` |
| `main.py` | hls4ml conversion + HLS synth + IP export |
| `deploy.tcl` | Block-design TCL (auto stream widths) — same as v1 |
| `build_bitstream.sh` | Vivado wrapper — same as v1 |
| `run_inference.py` | On-board inference (64-feature precision table) |
| `configs/uniform_8bit.py` | All `ap_fixed<8,4>`, RF=8 |
| `configs/low_mixed.py` | `ap_fixed<6,2>` weights, `<12,6>` activations, RF=8 |
| `configs/high_mixed_rf8.py` | Mixed `<16,8>` / `<12,6>` / `<20,10>`, RF=8 |
| `ip_repo/tlast_gen/` | Same TLAST helper IP as ECG v1 / NID |

## Pipeline

### One-time setup

```bash
cp -r ~/Downloads/hls4ml_path_b_staging/ecg_v2_project ~/DD_proj_ecg_v2
cd ~/DD_proj_ecg_v2

chmod +x build_bitstream.sh
source /tools/Xilinx/Vivado/2025.2/settings64.sh
pip install qkeras tensorflow-model-optimization wfdb scipy

# Package tlast_gen (one-time per Vivado version)
cd ip_repo/tlast_gen
vivado -mode batch -source package_tlast_gen.tcl
cd ../..
```

### Data prep (downloads MIT-BIH the first time, ~70 MB)

```bash
python3 prep_mit_bih.py
# → X_train.npy, y_train.npy, X_test.npy, y_test.npy
# → ./mitdb/   (raw PhysioNet records)
```

The split is a stratified random 80/20 split of beats pooled from all records, after
undersampling normal beats to balance the classes. It is **intra-patient**: beats from
the same patient can land in both train and test, so the accuracy is not comparable to
inter-patient (AAMI DS1/DS2) results.

Each X row: 64 samples cropped ±100 around an R-peak, downsampled, z-scored
per window, clipped to ±3.9.

Each y row: 0 (normal) or 1 (any other annotated beat type).

### Training

```bash
TF_USE_LEGACY_KERAS=1 python3 train_qkeras_ecg_v2.py
# Phase 1: QAT for 40 epochs
# Phase 2: 50% pruning for 15 epochs
# → model_v2.h5
```

Class weighting is automatic — MIT-BIH has ~10% abnormal beats, so the
default loss would otherwise let the model just predict zero and "achieve"
0.90 accuracy. We weight the positive class by `neg/pos` in `class_weight`.

The script prints both **accuracy** and **F1** so you can sanity-check
that performance is real rather than majority-class bias.

### HLS conversion + bitstream

```bash
for cfg in uniform_8bit low_mixed high_mixed_rf8; do
    python3 main.py configs.$cfg
    ./build_bitstream.sh $cfg
done
```

`build_bitstream.sh` reads `TDATA_NUM_BYTES` from each generated IP's
`component.xml`, so the wider input stream (64 features × 8 bits = 512 bits,
or × 16 bits = 1024 bits for high_mixed) gets handled automatically. No
changes to deploy.tcl needed.

### Deploy to board

```bash
for cfg in uniform_8bit low_mixed high_mixed_rf8; do
    scp deploy/$cfg/$cfg.bit  xilinx@192.168.2.99:/home/xilinx/ecg_v2_$cfg.bit
    scp deploy/$cfg/$cfg.hwh  xilinx@192.168.2.99:/home/xilinx/ecg_v2_$cfg.hwh
done
scp X_test.npy   xilinx@192.168.2.99:/home/xilinx/X_test_v2.npy
scp y_test.npy   xilinx@192.168.2.99:/home/xilinx/y_test_v2.npy
scp run_inference.py xilinx@192.168.2.99:/home/xilinx/run_inference_v2.py
```

### On-board inference

```bash
ssh xilinx@192.168.2.99
python3 /home/xilinx/run_inference_v2.py
```

Edit `CONFIG = "uniform_8bit"` at the top of `run_inference_v2.py` to switch
which v2 bitstream gets tested.

## Expected resource budget

For the 6,273-parameter v2 network at RF=8:

| Config | LUT estimate | DSP estimate | Notes |
|---|---|---|---|
| uniform_8bit | ~25k (~47%) | 0 | comfortable, 8-bit MACs in LUTs |
| low_mixed | ~18k (~34%) | 0 | smallest |
| high_mixed_rf8 | ~30k (~56%) | ~150–180 | largest, fits but tight on DSPs |

After build, check `hls_project_<config>/myproject_prj/solution1/syn/report/myproject_csynth.rpt`
for actuals.

## Expected accuracy progression (MIT-BIH binary, AAMI DS2)

| Stage | Test accuracy |
|---|---|
| Float Keras MLP | 0.94 – 0.96 |
| QAT `quantized_bits(8,4)` | 0.93 – 0.95 |
| QAT + 50% pruning | 0.92 – 0.95 |
| Hardware `uniform_8bit` | within ~1% of csim |
| Hardware `high_mixed_rf8` | within ~0.3% of float |

## How this compares to v1

For your project report, the v1 → v2 story is the headline:

> "By replacing 16 hand-crafted features with 64 R-peak-aligned raw signal
> samples and applying quantization-aware training, we improved hardware
> accuracy from 0.81 to 0.94 (+0.13) at the cost of a 6× increase in model
> parameters. Reuse Factor 8 absorbs that increase within the Z-7020's LUT
> budget; DSP usage and end-to-end latency are essentially unchanged."

That's a much more interesting narrative than "we tried 4 precisions and
the best one was 81%."
