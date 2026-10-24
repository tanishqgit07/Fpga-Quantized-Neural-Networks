import numpy as np
import wfdb
import os
from tensorflow import keras
from keras import Sequential
from keras.layers import Dense, Dropout
from keras.optimizers import Adam
from keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
import matplotlib.pyplot as plt

# ------------------------------------------------------------------
# 1. Download MIT-BIH dataset
# ------------------------------------------------------------------
def download_mitbih(data_dir='mitbih_data'):
    os.makedirs(data_dir, exist_ok=True)

    # MIT-BIH record numbers
    records = [
        '100', '101', '102', '103', '104', '105', '106', '107',
        '108', '109', '111', '112', '113', '114', '115', '116',
        '117', '118', '119', '121', '122', '123', '124', '200',
        '201', '202', '203', '205', '207', '208', '209', '210',
        '212', '213', '214', '215', '217', '219', '220', '221',
        '222', '223', '228', '230', '231', '232', '233', '234'
    ]

    print("Downloading MIT-BIH records...")
    for rec in records:
        try:
            wfdb.dl_database('mitdb', dl_dir=data_dir, records=[rec])
        except Exception as e:
            print(f"  Skipping {rec}: {e}")

    print("Download complete.")
    return data_dir, records

# ------------------------------------------------------------------
# 2. Extract features from ECG beats
# ------------------------------------------------------------------
def extract_features(data_dir, records):
    X = []
    y = []

    # Normal beat annotations
    normal_annotations = ['N', 'L', 'R', 'e', 'j']
    # Abnormal beat annotations
    abnormal_annotations = ['V', 'F', 'A', 'a', 'J', 'S', 'E', '/', 'f', 'Q']

    print("Extracting features...")
    for rec in records:
        try:
            record   = wfdb.rdrecord(os.path.join(data_dir, rec))
            annot    = wfdb.rdann(os.path.join(data_dir, rec), 'atr')
            signal   = record.p_signal[:, 0]  # use lead 1
            fs       = record.fs              # sampling frequency (360 Hz)
            symbols  = annot.symbol
            samples  = annot.sample

            window   = int(0.3 * fs)  # 0.3 seconds each side = 108 samples

            for i, (sample, symbol) in enumerate(zip(samples, symbols)):
                # Skip if too close to start or end
                if sample - window < 0 or sample + window >= len(signal):
                    continue

                # Extract beat window
                beat = signal[sample - window: sample + window]

                # Extract 16 features from beat
                features = extract_beat_features(beat, fs)

                if symbol in normal_annotations:
                    X.append(features)
                    y.append(0)  # normal
                elif symbol in abnormal_annotations:
                    X.append(features)
                    y.append(1)  # abnormal

        except Exception as e:
            print(f"  Skipping record {rec}: {e}")

    X = np.array(X)
    y = np.array(y)
    print(f"Extracted {len(X)} beats: {np.sum(y==0)} normal, {np.sum(y==1)} abnormal")
    return X, y

# ------------------------------------------------------------------
# 3. Extract 16 features from a single beat
# ------------------------------------------------------------------
def extract_beat_features(beat, fs):
    window = len(beat)
    half   = window // 2

    # Time domain features
    rr_interval     = window / fs                          # RR interval
    qrs_amplitude   = np.max(beat) - np.min(beat)         # QRS amplitude
    r_peak          = np.max(beat)                         # R peak amplitude
    q_trough        = np.min(beat[:half])                  # Q trough
    s_trough        = np.min(beat[half:])                  # S trough
    mean_val        = np.mean(beat)                        # Mean amplitude
    std_val         = np.std(beat)                         # Std deviation
    energy          = np.sum(beat ** 2)                    # Signal energy
    skewness        = _skewness(beat)                      # Skewness
    kurtosis        = _kurtosis(beat)                      # Kurtosis

    # Frequency domain features
    fft_vals        = np.abs(np.fft.rfft(beat))
    freqs           = np.fft.rfftfreq(window, d=1/fs)
    lf_power        = np.sum(fft_vals[(freqs >= 0.5) & (freqs < 5)] ** 2)
    hf_power        = np.sum(fft_vals[(freqs >= 5)  & (freqs < 40)] ** 2)
    lf_hf_ratio     = lf_power / (hf_power + 1e-8)
    dominant_freq   = freqs[np.argmax(fft_vals)]
    spectral_entropy = _spectral_entropy(fft_vals)
    zero_crossings  = np.sum(np.diff(np.sign(beat)) != 0)

    features = [
        rr_interval, qrs_amplitude, r_peak, q_trough, s_trough,
        mean_val, std_val, energy, skewness, kurtosis,
        lf_power, hf_power, lf_hf_ratio, dominant_freq,
        spectral_entropy, zero_crossings
    ]
    return features

def _skewness(x):
    mu  = np.mean(x)
    std = np.std(x)
    return np.mean(((x - mu) / (std + 1e-8)) ** 3)

def _kurtosis(x):
    mu  = np.mean(x)
    std = np.std(x)
    return np.mean(((x - mu) / (std + 1e-8)) ** 4)

def _spectral_entropy(fft_vals):
    psd  = fft_vals ** 2
    psd  = psd / (np.sum(psd) + 1e-8)
    return -np.sum(psd * np.log(psd + 1e-8))

# ------------------------------------------------------------------
# 4. Build model (16 inputs matching hls4ml config)
# ------------------------------------------------------------------
def build_model(input_dim=16):
    model = Sequential([
        Dense(16, activation='relu', input_shape=(input_dim,), name='dense1'),
        Dense(8,  activation='relu', name='dense2'),
        Dense(1,  activation='sigmoid', name='output')
    ])
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return model

# ------------------------------------------------------------------
# 5. Main
# ------------------------------------------------------------------
if __name__ == "__main__":

    # Download and extract
    data_dir, records = download_mitbih()
    X, y = extract_features(data_dir, records)

    # Normalize features
    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    # Save scaler for later use on FPGA
    np.save('scaler_mean.npy', scaler.mean_)
    np.save('scaler_std.npy',  scaler.scale_)

    # Balance classes (undersample majority)
    n_abnormal = np.sum(y == 1)
    normal_idx = np.where(y == 0)[0]
    abnormal_idx = np.where(y == 1)[0]
    normal_idx_sampled = np.random.choice(normal_idx, size=n_abnormal, replace=False)
    idx = np.concatenate([normal_idx_sampled, abnormal_idx])
    np.random.shuffle(idx)
    X, y = X[idx], y[idx]
    print(f"Balanced dataset: {len(X)} samples ({np.sum(y==0)} normal, {np.sum(y==1)} abnormal)")

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Save test data for compare.py
    np.save('X_test.npy', X_test)
    np.save('y_test.npy', y_test)

    # Train
    model = build_model()
    model.summary()

    callbacks = [
        EarlyStopping(patience=10, restore_best_weights=True, verbose=1),
        ModelCheckpoint('model.h5', save_best_only=True, verbose=1)
    ]

    history = model.fit(
        X_train, y_train,
        epochs=100,
        batch_size=32,
        validation_split=0.2,
        callbacks=callbacks,
        verbose=1
    )

    # Evaluate
    y_pred = (model.predict(X_test) > 0.5).astype(int).flatten()
    print("\n--- Test Results ---")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print(classification_report(y_test, y_pred, target_names=['Normal', 'Abnormal']))

    # Plot training history
    plt.figure(figsize=(12, 4))
    plt.subplot(1, 2, 1)
    plt.plot(history.history['accuracy'],     label='Train')
    plt.plot(history.history['val_accuracy'], label='Val')
    plt.title('Model Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(history.history['loss'],     label='Train')
    plt.plot(history.history['val_loss'], label='Val')
    plt.title('Model Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()

    plt.tight_layout()
    plt.savefig('training_history.png', dpi=150)
    plt.show()
    print("Saved: training_history.png")
    print("Saved: model.h5")