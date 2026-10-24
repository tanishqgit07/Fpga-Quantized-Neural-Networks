"""
train_qkeras_ecg_v2.py

ECG v2 model: 64 raw signal features per heartbeat.
Architecture: 64 → QDense(64) → QReLU → QDense(32) → QReLU → QDense(1) → sigmoid
Roughly 6× more parameters than v1 (1089 → 6273).

Trains in two phases:
  1. Quantization-aware training (QKeras quantized_bits(8,4))
  2. 50% pruning on top of QAT

Outputs: model_v2.h5 — point main.py at this file.

Class imbalance is handled with class_weight (MIT-BIH has ~10% abnormal beats).

Run:
    cd ~/DD_proj_ecg_v2
    TF_USE_LEGACY_KERAS=1 python3 train_qkeras_ecg_v2.py

Recorded result for the deployed model (intra-patient 80/20 split, see
prep_mit_bih.py): QAT + 50% pruning, Keras accuracy 0.9619.
"""

import os
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")

import numpy as np
from tensorflow import keras
from tensorflow.keras import layers as L
from qkeras import QDense, QActivation, quantized_bits, quantized_relu
import tensorflow_model_optimization as tfmot
from sklearn.metrics import accuracy_score, f1_score


WEIGHT_BITS, WEIGHT_INT = 8, 4
ACT_BITS,    ACT_INT    = 8, 4

QAT_EPOCHS     = 40
PRUNE_EPOCHS   = 15
BATCH_SIZE     = 256
FINAL_SPARSITY = 0.5
INPUT_DIM      = 64

OUT_PATH       = "model_v2.h5"


def build():
    wq = quantized_bits(WEIGHT_BITS, WEIGHT_INT, alpha=1)
    aq = quantized_relu(ACT_BITS, ACT_INT)

    inp = L.Input(shape=(INPUT_DIM,), name="dense1_input")
    x = QDense(64, kernel_quantizer=wq, bias_quantizer=wq, name="dense1")(inp)
    x = QActivation(aq, name="relu1")(x)
    x = QDense(32, kernel_quantizer=wq, bias_quantizer=wq, name="dense2")(x)
    x = QActivation(aq, name="relu2")(x)
    x = QDense(1,  kernel_quantizer=wq, bias_quantizer=wq, name="output")(x)
    out = L.Activation("sigmoid", name="layer7_out")(x)

    m = keras.Model(inp, out, name="qmlp_ecg_v2")
    m.compile(optimizer=keras.optimizers.Adam(1e-3),
              loss="binary_crossentropy",
              metrics=["accuracy"])
    return m


def evaluate(model, X, y, label):
    proba = model.predict(X, verbose=0).flatten()
    pred  = (proba > 0.5).astype(int)
    acc   = accuracy_score(y, pred)
    f1    = f1_score(y, pred)
    print(f"{label}: acc={acc:.4f}  f1={f1:.4f}")
    return acc


def main():
    X_train = np.load("X_train.npy")
    y_train = np.load("y_train.npy")
    X_test  = np.load("X_test.npy")
    y_test  = np.load("y_test.npy")
    print(f"Train: {X_train.shape}  positive rate {y_train.mean():.3f}")
    print(f"Test:  {X_test.shape}   positive rate {y_test.mean():.3f}")

    # Class imbalance: MIT-BIH has ~10% abnormal beats. Without weighting, the
    # model can learn to predict all-zero and still get 0.90 accuracy.
    pos = max(y_train.sum(), 1.0)
    neg = max((1 - y_train).sum(), 1.0)
    class_weight = {0: 1.0, 1: float(neg / pos)}
    print(f"Class weight (positive class): {class_weight[1]:.3f}")

    # ---- Phase 1: QAT ----
    print("\n=== Phase 1: Quantization-Aware Training ===")
    m = build()
    m.summary()
    m.fit(X_train, y_train,
          validation_split=0.1,
          epochs=QAT_EPOCHS,
          batch_size=BATCH_SIZE,
          class_weight=class_weight,
          verbose=2)
    evaluate(m, X_test, y_test, "After QAT")

    # ---- Phase 2: Pruning ----
    print(f"\n=== Phase 2: Pruning to {int(FINAL_SPARSITY*100)}% sparsity ===")
    end_step = max(1, (len(X_train) // BATCH_SIZE) * PRUNE_EPOCHS)
    pp = {"pruning_schedule": tfmot.sparsity.keras.PolynomialDecay(
        initial_sparsity=0.0, final_sparsity=FINAL_SPARSITY,
        begin_step=0, end_step=end_step)}
    pruned = tfmot.sparsity.keras.prune_low_magnitude(m, **pp)
    pruned.compile(optimizer=keras.optimizers.Adam(5e-4),
                   loss="binary_crossentropy",
                   metrics=["accuracy"])
    pruned.fit(X_train, y_train,
               validation_split=0.1,
               epochs=PRUNE_EPOCHS,
               batch_size=BATCH_SIZE,
               class_weight=class_weight,
               callbacks=[tfmot.sparsity.keras.UpdatePruningStep()],
               verbose=2)
    final = tfmot.sparsity.keras.strip_pruning(pruned)
    evaluate(final, X_test, y_test, "After QAT + Pruning")

    final.save(OUT_PATH)
    print(f"\nSaved: {OUT_PATH}")
    print("\nNext: run `python3 main.py configs.uniform_8bit` then `./build_bitstream.sh uniform_8bit`")


if __name__ == "__main__":
    main()
