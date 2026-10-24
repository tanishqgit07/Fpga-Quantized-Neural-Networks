"""
model.py — float baseline NID model

Plain Keras MLP for binary intrusion detection on NSL-KDD (41 -> 64 -> 32 -> 1).
Used as the accuracy ceiling for comparison; the QKeras + pruning version in
train_qkeras_nid.py is what gets deployed.

Layer naming follows the ECG project convention so the same configs/*.py
schema (referencing 'dense1', 'dense2', 'output') applies.

Run:
    python3 model.py
"""

import os
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")

import numpy as np
from tensorflow import keras
from tensorflow.keras import layers as L
from sklearn.metrics import accuracy_score

INPUT_DIM = 41
OUT_PATH  = "model.h5"


def build():
    inp = L.Input(shape=(INPUT_DIM,), name="dense1_input")
    x = L.Dense(64, activation="relu", name="dense1")(inp)
    x = L.Dense(32, activation="relu", name="dense2")(x)
    x = L.Dense(1,  name="output")(x)
    out = L.Activation("sigmoid", name="layer7_out")(x)
    m = keras.Model(inp, out, name="mlp_nid")
    m.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return m


def main():
    X_train = np.load("X_train.npy")
    y_train = np.load("y_train.npy")
    X_test  = np.load("X_test.npy")
    y_test  = np.load("y_test.npy")

    m = build()
    m.summary()

    m.fit(X_train, y_train,
          validation_split=0.1,
          epochs=20,
          batch_size=256,
          verbose=2)

    pred = (m.predict(X_test, verbose=0).flatten() > 0.5).astype(int)
    print(f"Test accuracy (float): {accuracy_score(y_test, pred):.4f}")

    m.save(OUT_PATH)
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
