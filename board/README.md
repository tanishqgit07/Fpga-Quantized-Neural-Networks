# PYNQ-Z2 Board-Side Inference

Open `run_inference.ipynb` in JupyterLab on the PYNQ-Z2 (default `http://<board-ip>:9090`, password `xilinx`).

## Per-model parameters

Edit the first config cell with the correct values for the bitstream you want to test:

| Model / config | `CONFIG` | `INPUT_DIM` | Expected on-board accuracy (estimate, not measured) | Notes |
|---|---|---|---|---|
| ECG v1 uniform_8bit | `uniform_8bit` | 16 | **~80-85%** | Keras was 91.76% — features have range up to ~31, get clipped to ap_fixed<8,4> range [-8, +7.94] on the FPGA |
| ECG v1 low_mixed   | `low_mixed`    | 16 | **~80-85%** | Same saturation issue as above |
| ECG v2 uniform_8bit | `uniform_8bit` | 64 | **~94-96%** | Data already clipped to ±3.9 in prep |
| ECG v2 low_mixed   | `low_mixed`    | 64 | **~93-95%** | 6-bit weights, slightly lower than uniform |
| NID uniform_8bit   | `uniform_8bit` | 41 | **~98-99%** | Pooled random split demo — see `prebuilt/README.md` |
| NID low_mixed      | `low_mixed`    | 41 | **~97-99%** | |

> All are binary sigmoid classifiers (`OUTPUT_DIM = 1`, `DECISION_THR = 0.5`).
>
> **Why ECG v1's on-board accuracy is lower than keras:** the 16 hand-crafted ECG features (RR interval, QRS amplitude, FFT bins, etc.) span a wide dynamic range (-8.7 to 31.0). The Keras model is float32 so it handles this fine; the FPGA's `ap_fixed<8,4>` only represents [-8, +7.9375] and saturates the rest. The QAT training partially mitigates this. ECG v2 and NID avoid this by clipping features to ±3.9 before saving.

## What to scp to the board (per model)

For each model you want to test, copy these 4 files into the same directory as `run_inference.ipynb`:

```
<config>.bit         # bitstream
<config>.hwh         # hardware description / metadata
X_test.npy           # input data (float32, shape [N, INPUT_DIM])
y_test.npy           # ground-truth labels (int, shape [N])
```

From the laptop (Windows PowerShell):

```powershell
# Replace <BOARD_IP> with the PYNQ board's actual IP (probably 192.168.2.99 for direct link,
# or DHCP-assigned if on a real network — see "Finding the board IP" below).
scp ecg_v1\deploy\uniform_8bit\* xilinx@<BOARD_IP>:~/
scp ecg_v1\X_test.npy ecg_v1\y_test.npy  xilinx@<BOARD_IP>:~/
```

The `axi_stream_driver.py` in `deploy/` is **not needed** — the notebook has the driver class inlined.

## Finding the board IP

If you don't know the board's IP after switching networks:

```bash
# On the board itself, plug in a monitor or use serial console (microUSB UART, 115200 baud):
ip addr

# Or from the laptop on the same LAN:
nmap -sn 192.168.1.0/24   # adjust subnet to match your router
arp -a | findstr "PYNQ"   # Windows
```

## Quick smoke test

Set `MAX_SAMPLES = 100` in the config cell first. Runs in ~1.5 s. If accuracy is in the expected range, set `MAX_SAMPLES = None` for the full test (7544 ECG v1 / 4412 ECG v2 / 29704 NID samples).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `RuntimeError: ... wait` hangs forever | TLAST not asserted / DMA stuck | Power-cycle the board, reload overlay |
| `AssertionError: INPUT_DIM mismatch` | Wrong `INPUT_DIM` for the loaded bitstream | Check the per-model table above |
| Accuracy is ~50% | Wrong `X_test.npy` for this model | Each model has its own preprocessing — copy the right one |
| `pynq` import fails | Not running on PYNQ board | This notebook only works on the PYNQ-Z2 |
| `IOError: Bitstream incompatible` | Vivado version mismatch | The driver passes `ignore_version=True` — should not happen, but power-cycle if it does |
