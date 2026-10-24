# Verification status of reported numbers

Every number in the paper (`paper/Research_Paper.docx`) and the README should trace to a recorded
result: a log, a report or a saved output. This file tracks where each one comes from.

## Verified (source in this repo or the original project archive)

| Claim | Value | Source |
|---|---|---|
| ECG-v1 baseline, float Keras | 0.9331 | `docs/figs_results/plot_accuracy.png` (`ecg_v1/compare_all.py`, 2026-04-20, `model.h5` + `X_test.npy`) |
| ECG-v1 baseline, csim uniform_8bit | 0.8047 | same plot |
| ECG-v1 baseline, on-board uniform_8bit | 0.8094 | measured on PYNQ-Z2 (`docs/README_NEW_WORK.md`, `ecg_v1/train_qkeras_ecg.py`) |
| ECG-v1 baseline architecture | 16→16→8→1, 417 params, Adam, batch 32, ≤100 epochs, early stopping (patience 10) | `ecg_v1/model.py`, `model.h5` |
| ECG-v1 QAT variant, Keras | 0.9176 | `prebuilt/README.md` (deploy notes, 2026-05-22) |
| ECG-v2, Keras (QAT + 50% pruning) | 0.9619 | `prebuilt/README.md` |
| ECG-v2 architecture | 64→64→32→1, 6,273 params; 40 QAT epochs + 15 pruning epochs | `ecg_v2/train_qkeras_ecg_v2.py` |
| NID architecture | 41→64→32→1, 4,801 params; 30% pruning | `nid/train_qkeras_nid.py` |

## Removed from the paper (no record found)

- The ECG-v2 and NID "HW" accuracies (0.93, 0.78). The original paper generator footnoted these as "estimated within 1% of csim", so they were never measured.
- The ECG-v2 csim accuracy (0.94) and the NID float/csim accuracies (0.81 / 0.79). No run log was found. The NID values also claim the canonical split, but the deployed NID model was trained on a pooled random split.
- The ECG-v1 float/csim values 0.86 / 0.82. The recorded values are 0.93 / 0.80.
- "~0.3 ms per inference, ~3,000 inferences/s". No board timing output was saved.

## Still to verify (Vedant: please add the reports)

These numbers are still in the paper. They came from builds on Vedant's machine (Path A), and those reports aren't in the repo:

- [ ] **Table II resources** (LUT / FF / DSP for ECG-v1 uniform_8bit and low_mixed, ECG-v2 uniform_8bit and low_mixed, NID uniform_8bit). Please add `*_utilization_placed.rpt` for each build. For reference, the local Path-B ECG-v1 builds report different numbers (e.g. uniform_8bit: 8,202 LUT / 8,728 FF).
- [ ] **HLS latency** of 10 / 12 / 14 cycles (ECG-v1 / ECG-v2 / NID) and the II values. Please add `myproject_csynth.rpt`. The local Path-B ECG-v1 uniform_8bit csynth reports 27 cycles.
- [ ] **ECG-v2 low_mixed WNS = −4.83 ns.** Please add `*_timing_summary_routed.rpt`.
- [ ] **"0 DSPs" for the 8-bit builds**, from the same utilization reports.
- [ ] **Fig. 5** (resource bar chart), which uses the Table II numbers.
- [ ] Trained `.h5` models for the deployed bundles, so float and csim can be re-measured on the exact `prebuilt/*/X_test.npy`.

Suggested location: `reports/<model>_<config>/`. Once they're added, update Table II, the latency text and this file.

## Not yet run

- [ ] **NID on the canonical split.** Run `nid/prep_nsl_kdd.py` (KDDTrain+ → KDDTest+), then `train_qkeras_nid.py`, then `main.py configs.uniform_8bit` to get float and csim. csim doesn't need Vivado, only g++. Then fill the NID row of Table III.
- [ ] **ECG-v2 csim.** `ecg_v2/main.py configs.uniform_8bit` prints it.
- [ ] **On-board accuracy and timing** for the four `prebuilt/` bundles. Each notebook prints the accuracy, latency and throughput.

## Outdated files

`docs/generate_paper*.py`, `docs/generate_research_paper.py` and `docs/generate_report.py` are earlier draft generators. They still contain the old estimated numbers and shouldn't be used to rebuild the paper.
