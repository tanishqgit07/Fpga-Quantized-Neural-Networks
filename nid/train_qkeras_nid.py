"""
train_qkeras_nid.py

QKeras + pruning training for the NSL-KDD network intrusion detector.
Same recipe as train_qkeras_ecg.py, scaled up for the 41-feature input.

Layer names match the ECG convention (dense1, dense2, output) so the same
configs/*.py schema applies.

Output: model_qkeras.h5

Run:
    cd ~/DD_proj_nid
    TF_USE_LEGACY_KERAS=1 python3 train_qkeras_nid.py

Architecture: 41 -> QDense(64) -> QReLU -> QDense(32) -> QReLU -> QDense(1) -> sigmoid

On the canonical KDDTrain+/KDDTest+ split, NSL-KDD binary accuracy is
typically 78-83% in the literature (the test set has attack types unseen in
train). Not yet measured for this model.
QAT recovers most of the post-quantization drop.
"""

import os
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")

import numpy as np
from tensorflow import keras
from tensorflow.keras import layers as L
from qkeras import QDense, QActivation, quantized_bits, quantized_relu
import tensorflow_model_optimization as tfmot
from sklearn.metrics import accuracy_score


WEIGHT_BITS, WEIGHT_INT = 8, 4
ACT_BITS,    ACT_INT    = 8, 4

QAT_EPOCHS     = 40
PRUNE_EPOCHS   = 15
BATCH_SIZE     = 512
FINAL_SPARSITY = 0.3
INPUT_DIM      = 41

OUT_PATH       = "model_qkeras.h5"


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

    m = keras.Model(inp, out, name="qmlp_nid")
    m.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return m


def evaluate(model, X, y, label):
    pred = (model.predict(X, verbose=0).flatten() > 0.5).astype(int)
    acc  = accuracy_score(y, pred)
    print(f"{label}: {acc:.4f}")
    return acc


def main():
    X_train = np.load("X_train.npy")
    y_train = np.load("y_train.npy")
    X_test  = np.load("X_test.npy")
    y_test  = np.load("y_test.npy")
    print(f"Train: {X_train.shape}  Test: {X_test.shape}")

    # ---- Phase 1: QAT ----
    print("\n=== QAT ===")
    m = build()
    m.summary()
    m.fit(X_train, y_train,
          validation_split=0.1,
          epochs=QAT_EPOCHS,
          batch_size=BATCH_SIZE,
          verbose=2)
    evaluate(m, X_test, y_test, "QAT test accuracy")

    # ---- Phase 2: Pruning ----
    print(f"\n=== Pruning to {int(FINAL_SPARSITY*100)}% ===")
    end_step = max(1, (len(X_train) // BATCH_SIZE) * PRUNE_EPOCHS)
    pp = {"pruning_schedule": tfmot.sparsity.keras.PolynomialDecay(
        initial_sparsity=0.0, final_sparsity=FINAL_SPARSITY,
        begin_step=0, end_step=end_step,
    )}
    pruned = tfmot.sparsity.keras.prune_low_magnitude(m, **pp)
    pruned.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    pruned.fit(X_train, y_train,
               validation_split=0.1,
               epochs=PRUNE_EPOCHS,
               batch_size=BATCH_SIZE,
               callbacks=[tfmot.sparsity.keras.UpdatePruningStep()],
               verbose=2)
    final = tfmot.sparsity.keras.strip_pruning(pruned)
    evaluate(final, X_test, y_test, "QAT+Prune test accuracy")

    final.save(OUT_PATH)
    print(f"\nSaved: {OUT_PATH}")


if __name__ == "__main__":
    main()
