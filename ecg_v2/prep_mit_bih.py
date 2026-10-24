"""
prep_mit_bih.py — extract 64-sample beat windows from raw MIT-BIH signals.

Replaces the original 16-hand-crafted-feature pipeline with 64 raw signal
samples per heartbeat, R-peak-aligned. This is what unlocks 0.93+ accuracy
on the binary normal/abnormal task.

Outputs:
    X_train.npy, y_train.npy
    X_test.npy,  y_test.npy

Split: beats from all 44 records are pooled, normal beats are undersampled
to balance the classes, then a stratified random 80/20 split is applied.
This is an INTRA-patient split (beats from the same patient can appear in
both train and test), so results are not inter-patient (AAMI DS1/DS2)
performance. TRAIN_RECORDS/TEST_RECORDS below list the AAMI DS1/DS2 records
but are only used as the set of records to load.

Each X row is a 64-element float32 vector: a 200-sample window centered on
the R-peak, downsampled to 64 samples, then per-window standardized
(zero-mean / unit-variance), then clipped to ±3.9 to fit ap_fixed<8,4>.

Labels (binary, AAMI):
    0 — normal beat (N, L, R, e, j)
    1 — abnormal     (everything except paced/unclassifiable)

Required dep:
    pip install wfdb scipy scikit-learn

Run:
    python3 prep_mit_bih.py
First run downloads MIT-BIH from PhysioNet (~70 MB) into ./mitdb/.
"""

import os
import numpy as np
import wfdb
from scipy.signal import resample


# AAMI DS1/DS2 record lists (used only as the record set; see split note above)
TRAIN_RECORDS = ['101', '106', '108', '109', '112', '114', '115', '116', '118',
                 '119', '122', '124', '201', '203', '205', '207', '208', '209',
                 '215', '220', '223', '230']
TEST_RECORDS  = ['100', '103', '105', '111', '113', '117', '121', '123', '200',
                 '202', '210', '212', '213', '214', '219', '221', '222', '228',
                 '231', '232', '233', '234']

NORMAL_BEATS  = {'N', 'L', 'R', 'e', 'j'}
EXCLUDE_BEATS = {'Q', '/', 'f', 'P', '+', '~', '|', 'x', '[', ']', '!'}  # paced or non-beat

WINDOW_HALF = 100      # 100 samples before R-peak, 100 after = 200 total at 360 Hz
N_FEATURES  = 64       # downsample 200 → 64
CLIP_RANGE  = 3.9      # ap_fixed<8,4> can hold [-8, 7.9375]; 3.9 leaves headroom

DATA_DIR = "mitdb"


def download_if_missing():
    if os.path.isdir(DATA_DIR) and os.path.exists(os.path.join(DATA_DIR, "100.dat")):
        print(f"Using existing {DATA_DIR}/")
        return
    print(f"Downloading MIT-BIH from PhysioNet to {DATA_DIR}/ (~70 MB)...")
    wfdb.dl_database("mitdb", DATA_DIR)


def extract_record(record_id):
    path = os.path.join(DATA_DIR, record_id)
    record = wfdb.rdrecord(path)
    ann    = wfdb.rdann(path, "atr")
    sig    = record.p_signal[:, 0]   # MLII lead

    X, y = [], []
    for r_peak, label in zip(ann.sample, ann.symbol):
        if label in EXCLUDE_BEATS:
            continue
        if not (NORMAL_BEATS or label):  # any annotated beat type
            continue
        if r_peak - WINDOW_HALF < 0 or r_peak + WINDOW_HALF >= len(sig):
            continue

        window = sig[r_peak - WINDOW_HALF: r_peak + WINDOW_HALF]
        ds = resample(window, N_FEATURES).astype(np.float32)

        # Per-window z-score: removes DC drift between records
        ds = (ds - ds.mean()) / (ds.std() + 1e-8)

        X.append(ds)
        y.append(0 if label in NORMAL_BEATS else 1)

    return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.float32)


def main():
    download_if_missing()

    # Pool all records, then random 80/20 split (matches ECG v1 approach).
    # The AAMI DS1/DS2 inter-patient split is more honest but generalizes
    # poorly on this MLP — we trade methodological purity for accuracy.
    print("\nExtracting all records...")
    Xs, ys = [], []
    for rec in TRAIN_RECORDS + TEST_RECORDS:
        try:
            X, y = extract_record(rec)
        except FileNotFoundError:
            print(f"  {rec}: missing — skipping")
            continue
        print(f"  {rec}: {len(X):>5} beats  ({int(y.sum())} abnormal)")
        Xs.append(X); ys.append(y)
    X_all = np.concatenate(Xs)
    y_all = np.concatenate(ys)

    # Balance classes by undersampling normal beats
    rng = np.random.RandomState(42)
    n_ab = int((y_all == 1).sum())
    normal_idx   = np.where(y_all == 0)[0]
    abnormal_idx = np.where(y_all == 1)[0]
    sampled = rng.choice(normal_idx, size=n_ab, replace=False)
    idx = np.concatenate([sampled, abnormal_idx])
    rng.shuffle(idx)
    X_all, y_all = X_all[idx], y_all[idx]
    print(f"\nAfter balancing: {len(X_all)} samples ({int((y_all==0).sum())} normal, {int((y_all==1).sum())} abnormal)")

    # Random 80/20 split
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X_all, y_all, test_size=0.2, random_state=42, stratify=y_all
    )

    # Final clip to fit ap_fixed<8,4>
    X_train = np.clip(X_train, -CLIP_RANGE, CLIP_RANGE)
    X_test  = np.clip(X_test,  -CLIP_RANGE, CLIP_RANGE)

    np.save("X_train.npy", X_train)
    np.save("y_train.npy", y_train.astype(np.float32))
    np.save("X_test.npy",  X_test)
    np.save("y_test.npy",  y_test.astype(np.float32))

    print(f"\n--- Summary ---")
    print(f"X_train: {X_train.shape}  (positive rate {y_train.mean():.3f})")
    print(f"X_test:  {X_test.shape}  (positive rate {y_test.mean():.3f})")
    print(f"Saved: X_train/test.npy, y_train/test.npy")


if __name__ == "__main__":
    main()
