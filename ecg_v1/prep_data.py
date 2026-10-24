"""
prep_data.py — download MIT-BIH and produce X_train/X_test (16 features).

Same feature pipeline as model.py but writes BOTH X_train and X_test so
train_qkeras_ecg.py can do real training instead of falling back to a
70/15/15 split of the test set.

First run downloads MIT-BIH (~70 MB) into ./mitdb/.
"""

import os
import numpy as np
import wfdb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

DATA_DIR = "mitdb"
RECORDS = [
    '100', '101', '102', '103', '104', '105', '106', '107',
    '108', '109', '111', '112', '113', '114', '115', '116',
    '117', '118', '119', '121', '122', '123', '124', '200',
    '201', '202', '203', '205', '207', '208', '209', '210',
    '212', '213', '214', '215', '217', '219', '220', '221',
    '222', '223', '228', '230', '231', '232', '233', '234'
]
NORMAL = {'N', 'L', 'R', 'e', 'j'}
ABNORMAL = {'V', 'F', 'A', 'a', 'J', 'S', 'E', '/', 'f', 'Q'}


def _skew(x):
    mu, sd = np.mean(x), np.std(x)
    return np.mean(((x - mu) / (sd + 1e-8)) ** 3)


def _kurt(x):
    mu, sd = np.mean(x), np.std(x)
    return np.mean(((x - mu) / (sd + 1e-8)) ** 4)


def _spec_ent(fft_vals):
    psd = fft_vals ** 2
    psd = psd / (np.sum(psd) + 1e-8)
    return -np.sum(psd * np.log(psd + 1e-8))


def extract_features(beat, fs):
    half = len(beat) // 2
    rr_interval     = len(beat) / fs
    qrs_amplitude   = np.max(beat) - np.min(beat)
    r_peak          = np.max(beat)
    q_trough        = np.min(beat[:half])
    s_trough        = np.min(beat[half:])
    mean_val        = np.mean(beat)
    std_val         = np.std(beat)
    energy          = np.sum(beat ** 2)
    skew            = _skew(beat)
    kurt            = _kurt(beat)
    fft_vals = np.abs(np.fft.rfft(beat))
    freqs    = np.fft.rfftfreq(len(beat), d=1/fs)
    lf_power = np.sum(fft_vals[(freqs >= 0.5) & (freqs < 5)] ** 2)
    hf_power = np.sum(fft_vals[(freqs >= 5)  & (freqs < 40)] ** 2)
    lf_hf    = lf_power / (hf_power + 1e-8)
    dom_freq = freqs[np.argmax(fft_vals)]
    spec_ent = _spec_ent(fft_vals)
    zc       = np.sum(np.diff(np.sign(beat)) != 0)
    return [rr_interval, qrs_amplitude, r_peak, q_trough, s_trough,
            mean_val, std_val, energy, skew, kurt,
            lf_power, hf_power, lf_hf, dom_freq, spec_ent, zc]


def download_if_missing():
    if os.path.isdir(DATA_DIR) and os.path.exists(os.path.join(DATA_DIR, "100.dat")):
        print(f"Using existing {DATA_DIR}/")
        return
    print(f"Downloading MIT-BIH to {DATA_DIR}/ (~70 MB)...")
    wfdb.dl_database("mitdb", DATA_DIR)


def main():
    download_if_missing()
    X, y = [], []
    for rec in RECORDS:
        try:
            record = wfdb.rdrecord(os.path.join(DATA_DIR, rec))
            ann    = wfdb.rdann(os.path.join(DATA_DIR, rec), "atr")
        except Exception as e:
            print(f"  skip {rec}: {e}")
            continue
        sig = record.p_signal[:, 0]
        fs  = record.fs
        win = int(0.3 * fs)
        for sample, symbol in zip(ann.sample, ann.symbol):
            if sample - win < 0 or sample + win >= len(sig):
                continue
            if symbol not in NORMAL and symbol not in ABNORMAL:
                continue
            beat = sig[sample - win: sample + win]
            X.append(extract_features(beat, fs))
            y.append(0 if symbol in NORMAL else 1)
        print(f"  {rec}: running total {len(X)} beats")
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.int64)
    print(f"\nTotal: {len(X)} beats ({int((y==0).sum())} normal, {int((y==1).sum())} abnormal)")

    # Standardize
    scaler = StandardScaler()
    X = scaler.fit_transform(X)
    np.save('scaler_mean.npy', scaler.mean_)
    np.save('scaler_std.npy', scaler.scale_)

    # Balance via undersampling (matches model.py)
    rng = np.random.RandomState(42)
    n_ab = int((y == 1).sum())
    normal_idx   = np.where(y == 0)[0]
    abnormal_idx = np.where(y == 1)[0]
    sampled = rng.choice(normal_idx, size=n_ab, replace=False)
    idx = np.concatenate([sampled, abnormal_idx])
    rng.shuffle(idx)
    X, y = X[idx], y[idx]
    print(f"After balancing: {len(X)} samples")

    # 80/20 stratified
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    np.save('X_train.npy', X_train.astype(np.float32))
    np.save('y_train.npy', y_train.astype(np.float32))
    np.save('X_test.npy',  X_test.astype(np.float32))
    np.save('y_test.npy',  y_test.astype(np.float32))
    print(f"\nSaved: X_train {X_train.shape}, X_test {X_test.shape}")


if __name__ == "__main__":
    main()
