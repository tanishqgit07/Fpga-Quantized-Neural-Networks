# PYNQ-Z2 Deployment Package

4 ready-to-run bitstreams. Each subfolder is self-contained — one folder = one experiment.

## Contents

| Folder | Model | Config | Test set | Keras accuracy (recorded) | Expected on-board (not measured) |
|---|---|---|---|---|---|
| `ecg_v1_uniform_8bit/` | ECG arrhythmia (16 hand-crafted features, QAT variant 16→32→16→1) | uniform `ap_fixed<8,4>` | 7,544 | 91.76% | **~80-85%**¹ |
| `ecg_v1_low_mixed/`    | same model | mixed precision (12-bit weight, 14-bit acc) | 7,544 | 91.76% | **~80-85%**¹ |
| `ecg_v2_uniform_8bit/` | ECG arrhythmia (64 raw R-peak samples) | uniform `ap_fixed<8,4>` | 4,412 | 96.19% | **~94-96%** |
| `nid_uniform_8bit/`    | NSL-KDD network intrusion detector² | uniform `ap_fixed<8,4>` | 29,704 | 98.88% | **~98-99%** |

None of these four bundles has a recorded on-board accuracy. The only on-board measurement in this
project is 80.94% for the earlier post-hoc-quantised ECG-v1 baseline (16→16→8→1), which is not one of
these bundles.

² Demo only. This model was trained on a pooled random 80/20 split of KDDTrain+ and KDDTest+, so test-set
attack types leak into training and 98.88% is **not** comparable to NSL-KDD benchmarks. `nid/prep_nsl_kdd.py`
now uses the canonical KDDTrain+/KDDTest+ split; a bitstream for that model has not been built yet.

¹ ECG v1 hits saturation: features have range up to ~31, but `ap_fixed<8,4>` only holds ±7.94. ECG v2 + NID don't have this issue (data clipped to ±3.9 during prep).

## How to deploy one model

```bash
# 1. From your laptop — scp the whole subfolder to the PYNQ board
scp -r ecg_v2_uniform_8bit/ xilinx@<BOARD_IP>:~/

# 2. On the board — open JupyterLab
#    Browser: http://<BOARD_IP>:9090   (password: xilinx)

# 3. Navigate to ~/ecg_v2_uniform_8bit/, open run_inference.ipynb
#    The first cell is already configured for this model.

# 4. Cell -> Run All
```

The last cell prints:
- Accuracy
- Confusion matrix + classification report
- Total wall time, per-sample latency, throughput (inferences/sec)

## To switch models

Restart the kernel (Kernel → Restart) and `cd` into a different subfolder, then run that folder's notebook. Or scp a different subfolder and open it.

## Finding the board IP

Default fallback (direct cable): `192.168.2.99`
On a router: check the DHCP client list, or run `ip addr` on the board's serial console (microUSB UART @ 115200 baud, login `xilinx`/`xilinx`).

## What's in each subfolder

```
<model>/
├── <config>.bit              ← FPGA bitstream
├── <config>.hwh              ← PYNQ hardware metadata
├── X_test.npy                ← test inputs (float32)
├── y_test.npy                ← ground-truth labels
└── run_inference.ipynb       ← pre-configured for this model — Run All
```

The notebook driver class is inlined (no separate `axi_stream_driver.py` needed). The DMA hierarchy is `/hier_0/axi_dma_0` and stream dtype is `np.float32` — matches all 4 bitstreams.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `RuntimeError: ... wait` hangs | DMA stuck (missing TLAST?) | Power-cycle board, reload overlay |
| Accuracy ~50% | Wrong `X_test.npy` for this bitstream | Each folder has its own — don't mix |
| `IOError: ... bitstream` | Vivado version mismatch | Notebook uses `ignore_version=True` — should not happen |
| `pynq` import error | Not running on PYNQ board | These files only run on the PYNQ-Z2 |
| Kernel won't start | Old kernel state | Kernel → Restart and Clear Output |
