"""
prep_nsl_kdd.py

Download and preprocess the NSL-KDD dataset (a clean version of KDD'99 for
network intrusion detection benchmarking) into:

    X_train.npy, y_train.npy   (~125k samples)
    X_test.npy,  y_test.npy    (~22k  samples)
    scaler_mean.npy, scaler_std.npy

The output features are 41-D float32 vectors: the 38 numeric features plus
the three categorical columns (protocol_type, service, flag) as integer
codes. Encoders and the scaler are fit on KDDTrain+ only (canonical split).

For the binary FPGA model: y = 0 (normal) or 1 (attack).

Run:
    python3 prep_nsl_kdd.py

Reads NSL-KDD from local CSVs if present (./KDDTrain+.txt, ./KDDTest+.txt).
If not, attempts to download from the canonical mirror.
"""

import os
import urllib.request
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler


COLS = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes",
    "land", "wrong_fragment", "urgent", "hot", "num_failed_logins",
    "logged_in", "num_compromised", "root_shell", "su_attempted", "num_root",
    "num_file_creations", "num_shells", "num_access_files", "num_outbound_cmds",
    "is_host_login", "is_guest_login", "count", "srv_count", "serror_rate",
    "srv_serror_rate", "rerror_rate", "srv_rerror_rate", "same_srv_rate",
    "diff_srv_rate", "srv_diff_host_rate", "dst_host_count",
    "dst_host_srv_count", "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate", "dst_host_srv_serror_rate", "dst_host_rerror_rate",
    "dst_host_srv_rerror_rate", "label", "difficulty",
]

# The canonical NSL-KDD mirror (GitHub-hosted)
URL_TRAIN = "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTrain%2B.txt"
URL_TEST  = "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTest%2B.txt"


def download_if_missing(path, url):
    if os.path.exists(path):
        print(f"Using existing {path}")
        return
    print(f"Downloading {url} -> {path}")
    urllib.request.urlretrieve(url, path)


def load_split(path):
    df = pd.read_csv(path, header=None, names=COLS)
    return df


def main():
    download_if_missing("KDDTrain+.txt", URL_TRAIN)
    download_if_missing("KDDTest+.txt",  URL_TEST)

    df_tr = load_split("KDDTrain+.txt")
    df_te = load_split("KDDTest+.txt")

    # Drop the difficulty column
    df_tr = df_tr.drop(columns=["difficulty"])
    df_te = df_te.drop(columns=["difficulty"])

    # Binary label: normal -> 0, anything else -> 1
    y_tr = (df_tr["label"] != "normal").astype(np.float32).values
    y_te = (df_te["label"] != "normal").astype(np.float32).values

    df_tr = df_tr.drop(columns=["label"])
    df_te = df_te.drop(columns=["label"])

    # Encode the 3 categorical columns as integer codes (fit on train only).
    # Categories that only appear in KDDTest+ map to an extra "unseen" code.
    cat_cols = ["protocol_type", "service", "flag"]
    for col in cat_cols:
        enc = LabelEncoder().fit(df_tr[col])
        known = set(enc.classes_)
        unseen = len(enc.classes_)
        df_tr[col] = enc.transform(df_tr[col])
        df_te[col] = [enc.transform([v])[0] if v in known else unseen for v in df_te[col]]

    X_tr = df_tr.values.astype(np.float32)
    X_te = df_te.values.astype(np.float32)
    print(f"Feature count: {X_tr.shape[1]}  (expecting 41)")

    # Standardize using train statistics
    scaler = StandardScaler().fit(X_tr)
    X_tr = scaler.transform(X_tr).astype(np.float32)
    X_te = scaler.transform(X_te).astype(np.float32)

    # Clip to a reasonable range so ap_fixed<8,4> can represent the values
    # without saturating most of them. After scaling, ~99% of values are
    # within +/- 3; clipping to +/- 4 leaves headroom and matches the
    # 4 integer bits.
    X_tr = np.clip(X_tr, -3.9, 3.9)
    X_te = np.clip(X_te, -3.9, 3.9)

    # Canonical NSL-KDD protocol: train on KDDTrain+, evaluate on KDDTest+.
    # (The prebuilt nid_uniform_8bit bitstream predates this and was trained
    # on a pooled random 80/20 split of both files, which leaks test-set
    # attack types into training — see prebuilt/README.md.)

    np.save("X_train.npy", X_tr)
    np.save("y_train.npy", y_tr)
    np.save("X_test.npy",  X_te)
    np.save("y_test.npy",  y_te)
    np.save("scaler_mean.npy", scaler.mean_.astype(np.float32))
    np.save("scaler_std.npy",  scaler.scale_.astype(np.float32))

    print(f"X_train: {X_tr.shape}  y_train mean (attack rate): {y_tr.mean():.3f}")
    print(f"X_test:  {X_te.shape}  y_test  mean (attack rate): {y_te.mean():.3f}")
    print("Saved: X_train.npy, y_train.npy, X_test.npy, y_test.npy, scaler_*.npy")


if __name__ == "__main__":
    main()
