"""
run_inference.py — on-board NID inference

Runs on the PYNQ-Z2. Same shape as the ECG run_inference.py but tuned for
41 input features and per-config precisions. Drives the AXI DMA via direct
MMIO to avoid PYNQ's wrapper checking too aggressively for an idle channel.
"""

import time
import numpy as np
from pynq import Overlay, allocate

# ----------------------------------------------------------------------
# Pick the config (must have <CONFIG>.bit and <CONFIG>.hwh on the board)
# ----------------------------------------------------------------------
CONFIG = "uniform_8bit"           # or "low_mixed", "high_mixed_rf2", etc.

BIT_PATH = f"/home/xilinx/nid_{CONFIG}.bit"   # naming convention: nid_<config>.bit
X_TEST   = "/home/xilinx/X_test_nid.npy"
Y_TEST   = "/home/xilinx/y_test_nid.npy"

# ----------------------------------------------------------------------
# Per-config precision table
#
#  - in_W  / in_I:  ap_fixed<W,I> of dense1_input stream
#  - out_W / out_I: ap_fixed<W,I> of layer7_out stream
#
# Pulled from each config's hls_config Model.Precision (and per-layer
# overrides if any). Verify against the IP's component.xml when in doubt:
#     grep TDATA_NUM_BYTES hls_project_<config>/.../component.xml
# ----------------------------------------------------------------------
PRECISION_BY_CONFIG = {
    "uniform_8bit": {
        "input_features": 41, "in_W": 8,  "in_I": 4,
        "output_features": 1, "out_W": 8, "out_I": 4,
    },
    "low_mixed": {
        "input_features": 41, "in_W": 12, "in_I": 6,
        "output_features": 1, "out_W": 12, "out_I": 6,
    },
    "high_mixed_rf1": {
        "input_features": 41, "in_W": 16, "in_I": 8,
        "output_features": 1, "out_W": 16, "out_I": 8,
    },
    "high_mixed_rf2": {
        "input_features": 41, "in_W": 16, "in_I": 8,
        "output_features": 1, "out_W": 16, "out_I": 8,
    },
}


def numpy_dtype_for(W):
    if W <= 8:  return np.int8
    if W <= 16: return np.int16
    if W <= 32: return np.int32
    raise ValueError(f"Width {W} too wide for numpy int")


# ----------------------------------------------------------------------
# AXI DMA register offsets (no SG mode)
# ----------------------------------------------------------------------
MM2S_DMACR  = 0x00
MM2S_DMASR  = 0x04
MM2S_SA     = 0x18
MM2S_SA_MSB = 0x1C
MM2S_LENGTH = 0x28
S2MM_DMACR  = 0x30
S2MM_DMASR  = 0x34
S2MM_DA     = 0x48
S2MM_DA_MSB = 0x4C
S2MM_LENGTH = 0x58


overlay = Overlay(BIT_PATH)
dma  = overlay.axi_dma_0
mmio = dma.mmio


def reset_and_arm():
    mmio.write(MM2S_DMACR, 0x4)
    mmio.write(S2MM_DMACR, 0x4)
    time.sleep(0.001)
    mmio.write(MM2S_DMACR, 0x1)
    mmio.write(S2MM_DMACR, 0x1)


def wait_complete(sr_offset, timeout_ms=200):
    for _ in range(timeout_ms):
        sr = mmio.read(sr_offset)
        if sr & 0x70:
            raise RuntimeError(f"DMA error: DMASR={hex(sr)}")
        if sr & 0x1000:
            mmio.write(sr_offset, 0x1000)
            return sr
        time.sleep(0.001)
    raise TimeoutError(f"DMA timed out: DMASR={hex(mmio.read(sr_offset))}")


def make_codec(p):
    in_dtype  = numpy_dtype_for(p["in_W"])
    out_dtype = numpy_dtype_for(p["out_W"])

    in_scale  = 1 << (p["in_W"]  - p["in_I"])
    out_scale = 1.0 / (1 << (p["out_W"] - p["out_I"]))

    in_max = (1 << (p["in_W"] - 1)) - 1
    in_min = -(1 << (p["in_W"] - 1))

    def encode(x):
        scaled = np.round(np.asarray(x) * in_scale)
        return np.clip(scaled, in_min, in_max).astype(in_dtype)

    def decode(out_value):
        return float(out_value) * out_scale

    in_nbytes  = (p["in_W"]  + 7) // 8 * p["input_features"]
    out_nbytes = (p["out_W"] + 7) // 8 * p["output_features"]

    return encode, decode, in_dtype, out_dtype, in_nbytes, out_nbytes


def main():
    if CONFIG not in PRECISION_BY_CONFIG:
        raise KeyError(f"No precision spec for '{CONFIG}'. "
                       f"Add it to PRECISION_BY_CONFIG.")
    p = PRECISION_BY_CONFIG[CONFIG]
    encode, decode, in_dtype, out_dtype, in_nbytes, out_nbytes = make_codec(p)

    print(f"Bitstream: {CONFIG}")
    print(f"  Input:  ap_fixed<{p['in_W']},{p['in_I']}>  "
          f"× {p['input_features']} = {in_nbytes} bytes ({in_dtype.__name__})")
    print(f"  Output: ap_fixed<{p['out_W']},{p['out_I']}> "
          f"× {p['output_features']} = {out_nbytes} bytes ({out_dtype.__name__})")

    X_test = np.load(X_TEST)
    y_test = np.load(Y_TEST)
    n = len(X_test)

    in_buf  = allocate(shape=(p["input_features"],),  dtype=in_dtype)
    out_buf = allocate(shape=(p["output_features"],), dtype=out_dtype)

    y_hw = np.zeros(n, dtype=np.float32)

    print(f"  Samples: {n}")

    t0 = time.time()
    for i in range(n):
        in_buf[:] = encode(X_test[i])

        reset_and_arm()
        mmio.write(S2MM_DA,     out_buf.physical_address & 0xFFFFFFFF)
        mmio.write(S2MM_DA_MSB, 0)
        mmio.write(S2MM_LENGTH, out_nbytes)
        mmio.write(MM2S_SA,     in_buf.physical_address & 0xFFFFFFFF)
        mmio.write(MM2S_SA_MSB, 0)
        mmio.write(MM2S_LENGTH, in_nbytes)
        wait_complete(MM2S_DMASR)
        wait_complete(S2MM_DMASR)

        y_hw[i] = decode(out_buf[0])
    t1 = time.time()

    pred = (y_hw > 0.5).astype(int)
    acc  = (pred == y_test).mean()
    print(f"  Accuracy:  {acc:.4f}")
    print(f"  Wall time: {(t1-t0)*1000:.1f} ms total")
    print(f"  Per-inf:   {(t1-t0)*1000/n:.3f} ms")

    out_path = f"/home/xilinx/y_hw_nid_{CONFIG}.npy"
    np.save(out_path, y_hw)
    print(f"  Saved:     {out_path}")


if __name__ == "__main__":
    main()
