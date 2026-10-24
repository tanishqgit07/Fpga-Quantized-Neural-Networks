import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.metrics import accuracy_score, roc_curve, auc
from tensorflow import keras
import hls4ml
import json

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
MODEL_PATH = "model.h5"
FPGA_PART  = "xc7z020clg400-1"

# NOTE: lut/ff/dsp/latency below are hand-copied HLS (csynth) estimates from
# April 2026, not post-implementation results. Only the accuracy/AUC values
# this script computes are measurements.
CONFIGS = {
    'Uniform\nap_fixed<8,4>': {
        'module':   'configs.uniform_8bit',
        'proj_dir': 'hls_project_uniform_8bit',
        'color':    'steelblue',
        'lut':      9397,
        'ff':       3417,
        'dsp':      0,
        'latency':  14,
    },
    'Low Mixed\nap_fixed<6-12>': {
        'module':   'configs.low_mixed',
        'proj_dir': 'hls_project_low_mixed',
        'color':    'orange',
        'lut':      11779,
        'ff':       3861,
        'dsp':      0,
        'latency':  16,
    },
    'High Mixed\nRF=1': {
        'module':   'configs.high_mixed_rf1',
        'proj_dir': 'hls_project_high_mixed_rf1',
        'color':    'green',
        'lut':      13988,
        'ff':       10484,
        'dsp':      234,
        'latency':  19,
    },
    'High Mixed\nRF=2': {
        'module':   'configs.high_mixed_rf2',
        'proj_dir': 'hls_project_high_mixed_rf2',
        'color':    'red',
        'lut':      14563,
        'ff':       8599,
        'dsp':      192,
        'latency':  16,
    },
}

AVAILABLE = {
    'lut': 53200,
    'ff':  106400,
    'dsp': 220,
}

# ------------------------------------------------------------------
# 1. Load model and data
# ------------------------------------------------------------------
print("Loading model and data...")
model  = keras.models.load_model(MODEL_PATH)
X_test = np.load('X_test.npy')
y_test = np.load('y_test.npy')

y_keras_prob = model.predict(X_test).flatten()
y_keras      = (y_keras_prob > 0.5).astype(int)
keras_acc    = accuracy_score(y_test, y_keras)
fpr_k, tpr_k, _ = roc_curve(y_test, y_keras_prob)
auc_k = auc(fpr_k, tpr_k)
print(f"Keras baseline — Accuracy: {keras_acc:.4f}  AUC: {auc_k:.4f}")

# ------------------------------------------------------------------
# 2. Run each hls4ml config and collect predictions
# ------------------------------------------------------------------
import importlib

results = {}
for name, cfg in CONFIGS.items():
    print(f"\nRunning: {name.replace(chr(10), ' ')}")

    # Load config
    mod         = importlib.import_module(cfg['module'])
    user_config = mod.hls_config

    # Merge with hls4ml auto config
    hls_cfg = hls4ml.utils.config_from_keras_model(model, granularity='name')
    for k, v in user_config.get('Model', {}).items():
        hls_cfg['Model'][k] = v
    for layer, layer_cfg in user_config.get('LayerName', {}).items():
        if layer in hls_cfg['LayerName']:
            for k, v in layer_cfg.items():
                hls_cfg['LayerName'][layer][k] = v

    # Convert and compile
    hls_model = hls4ml.converters.convert_from_keras_model(
        model,
        hls_config=hls_cfg,
        backend='Vitis',
        output_dir=cfg['proj_dir'],
        part=FPGA_PART,
        clock_period=10,
        io_type='io_parallel'
    )
    hls_model.compile()

    # Predict
    y_prob = hls_model.predict(X_test).flatten()
    y_pred = (y_prob > 0.5).astype(int)

    acc  = accuracy_score(y_test, y_pred)
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    auc_val = auc(fpr, tpr)

    results[name] = {
        'acc':     acc,
        'auc':     auc_val,
        'fpr':     fpr,
        'tpr':     tpr,
        'y_prob':  y_prob,
        'lut':     cfg['lut'],
        'ff':      cfg['ff'],
        'dsp':     cfg['dsp'],
        'latency': cfg['latency'],
        'color':   cfg['color'],
    }
    print(f"  Accuracy: {acc:.4f}  AUC: {auc_val:.4f}  LUT: {cfg['lut']}  DSP: {cfg['dsp']}")

# ------------------------------------------------------------------
# 3. Print summary table
# ------------------------------------------------------------------
print("\n" + "="*75)
print(f"{'Config':<22} {'Accuracy':>10} {'AUC':>8} {'LUT':>8} {'FF':>8} {'DSP':>6} {'Latency':>9}")
print("-"*75)
print(f"{'Keras (baseline)':<22} {keras_acc:>10.4f} {auc_k:>8.4f} {'N/A':>8} {'N/A':>8} {'N/A':>6} {'N/A':>9}")
for name, r in results.items():
    label = name.replace('\n', ' ')
    print(f"{label:<22} {r['acc']:>10.4f} {r['auc']:>8.4f} "
          f"{r['lut']:>8} {r['ff']:>8} {r['dsp']:>6} {r['latency']:>7} cy")
print("="*75)

# ------------------------------------------------------------------
# 4. Plot 1 — ROC Curves
# ------------------------------------------------------------------
plt.figure(figsize=(8, 8))
plt.plot(fpr_k, tpr_k,
         label=f'Keras baseline (AUC={auc_k:.3f})',
         color='black', linewidth=2)

for name, r in results.items():
    label = name.replace('\n', ' ')
    plt.plot(r['fpr'], r['tpr'],
             label=f"{label} (AUC={r['auc']:.3f})",
             color=r['color'], linestyle='--', linewidth=1.5)

plt.plot([0,1],[0,1], 'k:', alpha=0.3)
plt.xlabel('False Positive Rate', fontsize=12)
plt.ylabel('True Positive Rate', fontsize=12)
plt.title('ROC Curve — ECG Arrhythmia Detection\nKeras vs hls4ml Configurations', fontsize=13)
plt.legend(fontsize=9)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('plot_roc.png', dpi=150)
plt.show()
print("Saved: plot_roc.png")

# ------------------------------------------------------------------
# 5. Plot 2 — Accuracy Bar Chart
# ------------------------------------------------------------------
labels = ['Keras\nbaseline'] + list(results.keys())
accs   = [keras_acc] + [r['acc'] for r in results.values()]
colors = ['black'] + [r['color'] for r in results.values()]

plt.figure(figsize=(11, 5))
bars = plt.bar(labels, accs, color=colors, edgecolor='white', linewidth=0.5)
plt.ylim(min(accs) - 0.05, 1.02)
plt.ylabel('Accuracy', fontsize=12)
plt.title('ECG Arrhythmia Detection\nAccuracy Across Configurations', fontsize=13)
plt.axhline(y=keras_acc, color='black', linestyle='--', alpha=0.4, linewidth=1)
for bar, acc in zip(bars, accs):
    plt.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 0.003,
             f'{acc:.4f}', ha='center', fontsize=9, fontweight='bold')
plt.tight_layout()
plt.savefig('plot_accuracy.png', dpi=150)
plt.show()
print("Saved: plot_accuracy.png")

# ------------------------------------------------------------------
# 6. Plot 3 — Resource Usage (LUT, FF, DSP)
# ------------------------------------------------------------------
config_labels = list(results.keys())
luts  = [r['lut'] for r in results.values()]
ffs   = [r['ff']  for r in results.values()]
dsps  = [r['dsp'] for r in results.values()]
cols  = [r['color'] for r in results.values()]

x = np.arange(len(config_labels))
w = 0.25

fig, ax = plt.subplots(figsize=(12, 6))
b1 = ax.bar(x - w,   luts, w, label='LUT',  color=[c for c in cols], alpha=0.9)
b2 = ax.bar(x,        ffs, w, label='FF',   color=[c for c in cols], alpha=0.6)
b3 = ax.bar(x + w,   dsps, w, label='DSP',  color=[c for c in cols], alpha=0.3)

ax.axhline(y=AVAILABLE['lut'], color='steelblue', linestyle='--',
           alpha=0.5, label=f"LUT limit ({AVAILABLE['lut']})")
ax.axhline(y=AVAILABLE['dsp'], color='purple', linestyle='-.',
           alpha=0.7, label=f"DSP limit ({AVAILABLE['dsp']})", linewidth=2)

# Annotate DSP overutilization
for i, dsp in enumerate(dsps):
    if dsp > AVAILABLE['dsp']:
        ax.annotate('OVER\nLIMIT', xy=(x[i] + w, dsp),
                    xytext=(x[i] + w + 0.1, dsp + 5000),
                    fontsize=8, color='red', fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color='red'))

ax.set_xticks(x)
ax.set_xticklabels(config_labels, fontsize=10)
ax.set_ylabel('Resource Count', fontsize=12)
ax.set_title('FPGA Resource Usage — PYNQ-Z2 (xc7z020clg400-1)', fontsize=13)

# Custom legend
lut_patch = mpatches.Patch(color='gray', alpha=0.9, label='LUT (solid)')
ff_patch  = mpatches.Patch(color='gray', alpha=0.6, label='FF (medium)')
dsp_patch = mpatches.Patch(color='gray', alpha=0.3, label='DSP (light)')
ax.legend(handles=[lut_patch, ff_patch, dsp_patch,
                   plt.Line2D([0],[0], color='steelblue', linestyle='--', label=f"LUT limit ({AVAILABLE['lut']})"),
                   plt.Line2D([0],[0], color='purple',    linestyle='-.', label=f"DSP limit ({AVAILABLE['dsp']})")],
          fontsize=9)
plt.tight_layout()
plt.savefig('plot_resources.png', dpi=150)
plt.show()
print("Saved: plot_resources.png")

# ------------------------------------------------------------------
# 7. Plot 4 — Pareto Curve (Accuracy vs LUT)
# ------------------------------------------------------------------
plt.figure(figsize=(9, 6))

# Plot each config point
for name, r in results.items():
    label = name.replace('\n', ' ')
    marker = 'X' if r['dsp'] > AVAILABLE['dsp'] else 'o'
    plt.scatter(r['lut'], r['acc'],
                color=r['color'], s=150, zorder=5, marker=marker)
    plt.annotate(label,
                 xy=(r['lut'], r['acc']),
                 xytext=(r['lut'] + 200, r['acc'] - 0.012),
                 fontsize=9,
                 color=r['color'])

# Connect points with line (excluding DSP overutilized)
valid = [(r['lut'], r['acc']) for r in results.values()
         if r['dsp'] <= AVAILABLE['dsp']]
valid.sort()
if valid:
    plt.plot([v[0] for v in valid], [v[1] for v in valid],
             'k--', alpha=0.3, linewidth=1)

plt.axhline(y=keras_acc, color='black', linestyle='--', alpha=0.5,
            label=f'Keras baseline ({keras_acc:.3f})')

plt.xlabel('LUT Usage', fontsize=12)
plt.ylabel('Accuracy', fontsize=12)
plt.title('Pareto Curve — Accuracy vs FPGA Resource Usage\nECG Arrhythmia Detection on PYNQ-Z2', fontsize=13)

# Legend with color patches
patches = [mpatches.Patch(color=r['color'],
           label=n.replace('\n',' ') + (' ❌DSP' if r['dsp'] > AVAILABLE['dsp'] else ''))
           for n, r in results.items()]
patches.append(plt.Line2D([0],[0], color='black', linestyle='--',
               label=f'Keras baseline ({keras_acc:.3f})'))
plt.legend(handles=patches, fontsize=9)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('plot_pareto.png', dpi=150)
plt.show()
print("Saved: plot_pareto.png")

# ------------------------------------------------------------------
# 8. Plot 5 — Latency vs Accuracy
# ------------------------------------------------------------------
plt.figure(figsize=(8, 6))
for name, r in results.items():
    label = name.replace('\n', ' ')
    lat_ns = r['latency'] * 10  # 10ns clock period
    plt.scatter(lat_ns, r['acc'],
                color=r['color'], s=150, zorder=5)
    plt.annotate(label,
                 xy=(lat_ns, r['acc']),
                 xytext=(lat_ns + 1, r['acc'] - 0.01),
                 fontsize=9, color=r['color'])

plt.axhline(y=keras_acc, color='black', linestyle='--', alpha=0.5,
            label=f'Keras baseline ({keras_acc:.3f})')
plt.xlabel('Latency (ns)', fontsize=12)
plt.ylabel('Accuracy', fontsize=12)
plt.title('Latency vs Accuracy\nECG Arrhythmia Detection on PYNQ-Z2', fontsize=13)
patches = [mpatches.Patch(color=r['color'], label=n.replace('\n',' '))
           for n, r in results.items()]
patches.append(plt.Line2D([0],[0], color='black', linestyle='--',
               label=f'Keras baseline ({keras_acc:.3f})'))
plt.legend(handles=patches, fontsize=9)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('plot_latency.png', dpi=150)
plt.show()
print("Saved: plot_latency.png")

# ------------------------------------------------------------------
# 9. Plot 6 — AUC Comparison Bar Chart
# ------------------------------------------------------------------
auc_labels = ['Keras\nbaseline'] + list(results.keys())
aucs       = [auc_k] + [r['auc'] for r in results.values()]
auc_colors = ['black'] + [r['color'] for r in results.values()]

plt.figure(figsize=(11, 5))
bars = plt.bar(auc_labels, aucs, color=auc_colors, edgecolor='white')
plt.ylim(min(aucs) - 0.02, 1.01)
plt.ylabel('AUC', fontsize=12)
plt.title('ECG Arrhythmia Detection\nAUC Comparison Across Configurations', fontsize=13)
plt.axhline(y=auc_k, color='black', linestyle='--', alpha=0.4, linewidth=1)
for bar, a in zip(bars, aucs):
    plt.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 0.002,
             f'{a:.4f}', ha='center', fontsize=9, fontweight='bold')
plt.tight_layout()
plt.savefig('plot_auc.png', dpi=150)
plt.show()
print("Saved: plot_auc.png")

print("\nAll plots saved:")
print("  plot_roc.png")
print("  plot_accuracy.png")
print("  plot_resources.png")
print("  plot_pareto.png")
print("  plot_latency.png")
print("  plot_auc.png")