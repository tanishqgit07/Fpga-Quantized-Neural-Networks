# New work — accuracy boost + NID model

This bundle adds three things on top of the working ECG bitstream:

1. **`run_inference.py`** — a clean, fast on-board inference script. Replaces
   the slapdash notebook cells. Pre-allocates buffers, drives the DMA via
   direct registers, switches between configs by editing one variable.
2. **`train_qkeras_ecg.py`** — quantization-aware training + pruning for the
   existing ECG model. Produces `model_qkeras.h5`. Drop in place of `model.h5`
   to recover most of the accuracy lost to post-hoc quantization.
3. **`nid_project/`** — sister project for NSL-KDD network intrusion
   detection. Same flow, different model and dataset.

---

## 1. Run other ECG configs

You've already got `uniform_8bit` working. Build the other two on arush's laptop:

```bash
cd ~/DD_proj_new_env
source /tools/Xilinx/Vivado/2025.2/settings64.sh

for cfg in low_mixed high_mixed_rf2; do
    python3 main.py configs.$cfg
    ./build_bitstream.sh $cfg
    scp deploy/$cfg/$cfg.bit deploy/$cfg/$cfg.hwh xilinx@192.168.2.99:/home/xilinx/
done
```

Then on the board, edit `run_inference.py` — change `CONFIG = "uniform_8bit"`
to `"low_mixed"` or `"high_mixed_rf2"` — and re-run. Each run saves
`y_hw_<config>.npy`.

`high_mixed_rf1` is over the DSP budget and won't deploy. Skip it unless you
prune (see §2 below).

## 2. Boost ECG accuracy past 90% with QKeras + pruning

Your current pipeline is **train float → cast to ap_fixed<8,4> after the fact**.
The 80.94% you got is what that lossy cast leaves you. Quantization-Aware
Training (QAT) puts the quantizer inside the loss function so the network
learns to be robust to it. Typical recovery: 80% → 88-92% on this dataset.

```bash
cd ~/DD_proj_new_env

# Install the extra deps once (in your existing venv)
pip install qkeras tensorflow-model-optimization

# Run QAT + pruning
TF_USE_LEGACY_KERAS=1 python3 train_qkeras_ecg.py
```

`TF_USE_LEGACY_KERAS=1` is required because `tensorflow_model_optimization`
(the pruning library) hasn't shipped Keras 3 support. The env var routes TF
through the Keras 2 API.

The script prints two accuracy numbers:
- After QAT only (pure quantization-aware)
- After QAT + 50% pruning (smaller DSP footprint)

It saves `model_qkeras.h5`. Then in `main.py`, change:

```python
MODEL_PATH = "model.h5"
```
to
```python
MODEL_PATH = "model_qkeras.h5"
```

and rebuild any config with the existing flow. You don't need to edit
`deploy.tcl` or the configs; hls4ml handles QKeras models natively.

**Bonus:** because pruning kills 50% of the weights, `high_mixed_rf1`
(previously 234 DSPs > 220 budget) likely fits now. Try building it.

### Expected accuracy progression

| Stage | Ballpark accuracy on MIT-BIH binary |
|---|---|
| Float Keras model | 0.85 – 0.92 |
| Post-hoc `ap_fixed<8,4>` (your current) | 0.81 |
| QAT `quantized_bits(8,4)` | 0.88 – 0.91 |
| QAT + 50% pruning | 0.86 – 0.90 (small drop, big DSP win) |

If you don't break 0.90 with QAT, the dataset's 16 features may just be
noisy — consider adding more features (RR-interval stats, QRS morphology)
in your preprocessing pipeline.

## 3. NID model (NSL-KDD network intrusion detection)

Set up as a parallel project. Don't drop it inside `~/DD_proj_new_env/` —
make a sister directory.

### Setup

```bash
mkdir ~/DD_proj_nid && cd ~/DD_proj_nid

# Copy the NID-specific Python from this bundle
cp -r ~/Downloads/hls4ml_path_b_staging/nid_project/* .

# Copy the shared infrastructure (deploy.tcl, build_bitstream.sh, ip_repo)
cp ~/DD_proj_new_env/deploy.tcl .
cp ~/DD_proj_new_env/build_bitstream.sh .
cp -r ~/DD_proj_new_env/ip_repo .
```

### Pipeline

```bash
cd ~/DD_proj_nid

# 1. Get the dataset (auto-downloads NSL-KDD)
python3 prep_nsl_kdd.py
# → X_train.npy, y_train.npy, X_test.npy, y_test.npy, scaler_*.npy

# 2. (optional) Train a float baseline first to see the upper bound
TF_USE_LEGACY_KERAS=1 python3 model.py
# → model.h5 (float Keras MLP)

# 3. Train the deployable QKeras + pruned model
TF_USE_LEGACY_KERAS=1 python3 train_qkeras_nid.py
# → model_qkeras.h5

# 4. Reuse the ECG project's main.py — copy it in and just change MODEL_PATH
cp ~/DD_proj_new_env/main.py .
sed -i 's|MODEL_PATH = "model.h5"|MODEL_PATH = "model_qkeras.h5"|' main.py

# 5. Build configs (uniform_8bit and high_mixed_rf2 are provided)
source /tools/Xilinx/Vivado/2025.2/settings64.sh
python3 main.py configs.uniform_8bit
./build_bitstream.sh uniform_8bit
```

### Important: NID uses 41 features, not 16

`run_inference.py` on the board has these constants near the top:

```python
INPUT_LEN  = 16
OUTPUT_LEN = 1
```

For NID, change `INPUT_LEN = 41`. The output is still 1 byte (sigmoid).

You'll also need to scp the NID dataset to the board:

```bash
scp X_test.npy y_test.npy xilinx@192.168.2.99:/home/xilinx/X_test_nid.npy
```

…and update `run_inference.py` to load the right files.

### Expected NID accuracy

NSL-KDD has a known property: the test set contains attack types that don't
appear in the training set. So the ceiling is roughly:

| Stage | Test accuracy |
|---|---|
| Float Keras MLP | 0.78 – 0.83 |
| QAT `quantized_bits(8,4)` | 0.76 – 0.81 |
| QAT + 50% pruning | similar |

If you want the >95% accuracy story, **report the train accuracy and
balanced metrics** (precision/recall on attack class), not just test
accuracy — NSL-KDD's test set is intentionally hard.

If you need a dataset where 95%+ test accuracy is realistic, switch to
**UNSW-NB15** or **CIC-IDS-2017**. Both follow the same pipeline; only
`prep_nsl_kdd.py` would change.

## 4. Files in this bundle

```
hls4ml_path_b_staging/
├── main.py                       (existing — unchanged)
├── deploy.tcl                    (existing — unchanged)
├── build_bitstream.sh            (existing — unchanged)
├── ip_repo/tlast_gen/            (existing — unchanged)
├── run_inference.py              ← NEW (board-side)
├── train_qkeras_ecg.py           ← NEW (laptop-side)
└── nid_project/                  ← NEW
    ├── prep_nsl_kdd.py
    ├── model.py
    ├── train_qkeras_nid.py
    └── configs/
        ├── uniform_8bit.py
        └── high_mixed_rf2.py
```

## 5. Order of work, recommended

1. Get `low_mixed` and `high_mixed_rf2` ECG bitstreams running. That gives
   you the resource/accuracy comparison table.
2. Run `train_qkeras_ecg.py`, swap `MODEL_PATH` in main.py, rebuild
   `uniform_8bit` and `high_mixed_rf1`. Compare on-board accuracy.
3. Set up the NID sister project. Run prep_nsl_kdd.py + train_qkeras_nid.py.
4. Build NID's `uniform_8bit` bitstream. Deploy. Validate on board with
   `run_inference.py` (with INPUT_LEN=41).

Steps 1-2 are tonight. Step 3 is downloads. Step 4 is another build cycle.
