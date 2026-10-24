"""
train_qkeras_ecg.py

Quantization-aware training (QKeras) + pruning for the ECG arrhythmia
classifier. Drops the post-quantization accuracy penalty and reduces
DSP/LUT usage.

Output: model_qkeras.h5 — point main.py at this file (set MODEL_PATH).

Why this works
--------------
- Plain training + post-hoc ap_fixed<8,4> casting (current flow): 80.94%
- QAT with quantized_bits(8,4) in the loop: typically 88-92% on MIT-BIH
  binary because the network learns to be robust to the quantization step
- 50% pruning on top: small accuracy delta but ~halves DSP usage on the
  high_mixed configs, which lets you actually deploy high_mixed_rf1

Run
---
    cd ~/DD_proj_new_env
    TF_USE_LEGACY_KERAS=1 python3 train_qkeras_ecg.py

The TF_USE_LEGACY_KERAS=1 part is critical — tensorflow_model_optimization
is incompatible with Keras 3. The env var forces TF to use tf_keras
(Keras 2 API) under the hood.

Inputs
------
- X_train.npy, y_train.npy  (if missing, the script splits X_test/y_test
  into train/val/test 70/15/15)
- X_test.npy,  y_test.npy
"""

import os
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers as L

from qkeras import QDense, QActivation, quantized_bits, quantized_relu
import tensorflow_model_optimization as tfmot
from sklearn.metrics import accuracy_score


# ----------------------------------------------------------------------
# Hyperparameters
# ----------------------------------------------------------------------
WEIGHT_BITS    = 8
WEIGHT_INT     = 4
ACT_BITS       = 8
ACT_INT        = 4

QAT_EPOCHS     = 40
PRUNE_EPOCHS   = 10
BATCH_SIZE     = 256
FINAL_SPARSITY = 0.5

OUT_PATH       = "model_qkeras.h5"


def build_model(input_dim):
    wq = quantized_bits(WEIGHT_BITS, WEIGHT_INT, alpha=1)
    bq = quantized_bits(WEIGHT_BITS, WEIGHT_INT, alpha=1)
    aq = quantized_relu(ACT_BITS, ACT_INT)

    inp = L.Input(shape=(input_dim,), name="dense1_input")
    x = QDense(32, kernel_quantizer=wq, bias_quantizer=bq, name="dense1")(inp)
    x = QActivation(aq, name="relu1")(x)
    x = QDense(16, kernel_quantizer=wq, bias_quantizer=bq, name="dense2")(x)
    x = QActivation(aq, name="relu2")(x)
    x = QDense(1,  kernel_quantizer=wq, bias_quantizer=bq, name="dense3")(x)
    out = L.Activation("sigmoid", name="layer7_out")(x)

    model = keras.Model(inp, out, name="qmlp_ecg")
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def load_data():
    if os.path.exists("X_train.npy") and os.path.exists("y_train.npy"):
        X_train = np.load("X_train.npy")
        y_train = np.load("y_train.npy")
        X_test  = np.load("X_test.npy")
        y_test  = np.load("y_test.npy")
        # Carve a small validation set off the training data
        n_val = max(1, int(0.1 * len(X_train)))
        X_val, y_val = X_train[-n_val:], y_train[-n_val:]
        X_train, y_train = X_train[:-n_val], y_train[:-n_val]
    else:
        # No pre-split data; split X_test/y_test into 70/15/15
        print("WARNING: X_train.npy not found — splitting X_test 70/15/15")
        X = np.load("X_test.npy")
        y = np.load("y_test.npy")
        rng = np.random.RandomState(0)
        idx = rng.permutation(len(X))
        n = len(X)
        n_tr, n_val = int(0.7 * n), int(0.15 * n)
        X_train, y_train = X[idx[:n_tr]], y[idx[:n_tr]]
        X_val,   y_val   = X[idx[n_tr:n_tr+n_val]], y[idx[n_tr:n_tr+n_val]]
        X_test,  y_test  = X[idx[n_tr+n_val:]],     y[idx[n_tr+n_val:]]

    print(f"Train: {X_train.shape}  Val: {X_val.shape}  Test: {X_test.shape}")
    return X_train, y_train, X_val, y_val, X_test, y_test


def evaluate(model, X, y, label):
    pred = (model.predict(X, verbose=0).flatten() > 0.5).astype(int)
    acc  = accuracy_score(y, pred)
    print(f"{label}: {acc:.4f}")
    return acc


def main():
    X_train, y_train, X_val, y_val, X_test, y_test = load_data()
    input_dim = X_train.shape[1]

    # ---------- Phase 1: QAT ----------
    print("\n=== Phase 1: Quantization-Aware Training ===")
    model = build_model(input_dim)
    model.summary()

    model.fit(X_train, y_train,
              validation_data=(X_val, y_val),
              epochs=QAT_EPOCHS,
              batch_size=BATCH_SIZE,
              verbose=2)
    evaluate(model, X_test, y_test, "QAT test accuracy")

    # ---------- Phase 2: Pruning ----------
    print(f"\n=== Phase 2: Pruning to {int(FINAL_SPARSITY*100)}% sparsity ===")
    end_step = max(1, (len(X_train) // BATCH_SIZE) * PRUNE_EPOCHS)
    pruning_params = {
        "pruning_schedule": tfmot.sparsity.keras.PolynomialDecay(
            initial_sparsity=0.0,
            final_sparsity=FINAL_SPARSITY,
            begin_step=0,
            end_step=end_step,
        )
    }
    pruned = tfmot.sparsity.keras.prune_low_magnitude(model, **pruning_params)
    pruned.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])

    pruned.fit(X_train, y_train,
               validation_data=(X_val, y_val),
               epochs=PRUNE_EPOCHS,
               batch_size=BATCH_SIZE,
               callbacks=[tfmot.sparsity.keras.UpdatePruningStep()],
               verbose=2)

    final = tfmot.sparsity.keras.strip_pruning(pruned)
    evaluate(final, X_test, y_test, "QAT+Prune test accuracy")

    final.save(OUT_PATH)
    print(f"\nSaved: {OUT_PATH}")
    print("\nNext: edit main.py — change MODEL_PATH = 'model_qkeras.h5' — and rebuild.")


if __name__ == "__main__":
    main()
