# FPGA-Accelerated Quantized Neural Networks on PYNQ-Z2

**ECG arrhythmia detection and network intrusion detection via hls4ml**

Quantized MLPs trained in Keras/QKeras, converted to HLS with [hls4ml](https://github.com/fastmachinelearning/hls4ml),
and deployed as AXI-Stream accelerators on the Xilinx Zynq-7020 (PYNQ-Z2).

📄 **Paper:** [`paper/Research_Paper.docx`](paper/Research_Paper.docx). This is the corrected version, see [`VERIFICATION.md`](VERIFICATION.md).

## Authors

- **Vedant Nandanwar**, Vishwakarma Institute of Technology, Pune
- **Tanishq Swami**, Vishwakarma Institute of Technology, Pune
- **Arush Wangikar**, Vishwakarma Institute of Technology, Pune

**Guide:** Dr. Abhay Chopde, Dept. of Electronics & Telecommunication Engineering, VIT Pune

## Highlights

- An end-to-end flow from Keras/QKeras to hls4ml, Vitis HLS / Vivado HLS, a Vivado block design, a `.bit`/`.hwh` bitstream, and PYNQ.
- A precision-adaptive Vivado TCL script (`deploy.tcl`) that builds the block design for any hls4ml precision config.
- A custom Verilog `tlast_gen` IP that generates AXI-Stream TLAST for the DMA.
- None of the 8-bit or low-mixed builds use any DSP slices. Every multiply-accumulate (MAC) maps to LUT logic.

### Accuracy (recorded results only)

| Model / Config | Split | Float (Keras) | csim | On-board HW |
|---|---|---|---|---|
| ECG-v1 baseline / uniform_8bit (16→16→8→1) | stratified random 80/20 | 0.93 | 0.80 | 0.81 |
| ECG-v1 QAT / uniform_8bit (16→32→16→1) | stratified random 80/20 | 0.92 | — | — |
| ECG-v2 / uniform_8bit | intra-patient random 80/20 | 0.96 | — | — |
| NID / uniform_8bit | canonical KDDTrain+ → KDDTest+ | — | — | — |

"—" means the value was not measured or recorded. The ECG splits are beat-level splits (intra-patient), so they are
not comparable to inter-patient (AAMI DS1/DS2) results. NID now uses the canonical NSL-KDD split, but it hasn't been
re-run yet. The NID bitstream in `prebuilt/` came from an earlier pooled random split, so it's a demo, not a benchmark.

Resource utilisation, HLS latency and timing figures are still being checked against the original Vivado reports.
See [`VERIFICATION.md`](VERIFICATION.md) for the status of every number in the paper.

## Run it without Vivado: prebuilt bitstreams

[`prebuilt/`](prebuilt/) contains ready-to-run bundles that were tested on the board. Each folder holds a `.bit`, a `.hwh`,
`X_test.npy`, `y_test.npy` and a preconfigured `run_inference.ipynb`. You only need a PYNQ-Z2. Vivado and Vitis are not required.

```bash
scp -r prebuilt/ecg_v2_uniform_8bit/ xilinx@<BOARD_IP>:~/
# open http://<BOARD_IP>:9090 (default password: xilinx) → run_inference.ipynb → Run All
```

See [`prebuilt/README.md`](prebuilt/README.md) for the full list of bundles and for troubleshooting.

## Repository layout

| Folder | Contents |
|---|---|
| [`ecg_v1/`](ecg_v1/) | MLP on 16 hand-crafted MIT-BIH features, with training, hls4ml configs, the bitstream build and a comparison script |
| [`ecg_v2/`](ecg_v2/) | Larger MLP on 64 raw R-peak samples, trained with QAT and 50% pruning |
| [`nid/`](nid/) | NSL-KDD network intrusion detection MLP |
| `*/configs/` | Precision configs: `uniform_8bit`, `low_mixed`, `high_mixed_rf1/rf2/rf8` |
| `*/ip_repo/tlast_gen/` | Custom Verilog TLAST generator IP and its packaging script |
| `*/deploy.tcl`, `*/build_bitstream.sh` | Generates the Vivado block design and the bitstream |
| [`board/`](board/) | Generic PYNQ-Z2 inference notebook and packaging script |
| [`prebuilt/`](prebuilt/) | Board-tested bitstream bundles |
| [`docs/`](docs/) | Toolchain notes, figures and older paper-generator drafts (outdated numbers, see `VERIFICATION.md`) |
| [`paper/`](paper/) | Research paper (corrected `.docx`) |

## Rebuilding from source (requires Xilinx tools)

```bash
python -m venv .venv && source .venv/bin/activate   # Python 3.11
pip install -r requirements.txt

cd ecg_v1
python train_qkeras_ecg.py              # → model.h5, X_test.npy, y_test.npy
python main.py configs.uniform_8bit     # hls4ml → HLS synthesis
bash build_bitstream.sh uniform_8bit    # block design + bitstream → deploy/uniform_8bit/
```

The project was built with two toolchains:

- **Path A:** Vivado 2020.1 with the `VivadoAccelerator` backend (`main_path_a.py`, `activate.ps1`, `build_queue.ps1`).
- **Path B:** Vitis HLS 2025.2 with the `Vitis` backend and a hand-written `deploy.tcl` (`main.py`, `build_bitstream.sh`).

Both are described in [`docs/TRANSFER_AND_RUN.md`](docs/TRANSFER_AND_RUN.md).

### Datasets (not committed)

- **MIT-BIH Arrhythmia DB:** `wfdb.dl_database('mitdb', 'mitdb/')` (see `ecg_v2/prep_mit_bih.py`)
- **NSL-KDD:** `nid/prep_nsl_kdd.py` downloads `KDDTrain+.txt` and `KDDTest+.txt` automatically ([official source](https://www.unb.ca/cic/datasets/nsl.html))

## Acknowledgements

This work was carried out at the Department of Electronics & Telecommunication Engineering, **Vishwakarma Institute
of Technology, Pune**, under the guidance of **Dr. Abhay Chopde**. We thank the department faculty for infrastructure support.

We also thank:

- The [Fast Machine Learning (FastML)](https://fastmachinelearning.org/) collaboration for [hls4ml](https://github.com/fastmachinelearning/hls4ml)
- The [QKeras](https://github.com/google/qkeras) maintainers
- The [PYNQ](http://www.pynq.io/) project and AMD/Xilinx
- PhysioNet for the [MIT-BIH Arrhythmia Database](https://physionet.org/content/mitdb/) and the Canadian Institute for Cybersecurity (UNB) for [NSL-KDD](https://www.unb.ca/cic/datasets/nsl.html)

## Citation

```bibtex
@misc{nandanwar_swami_wangikar_hls4ml_pynq,
  title  = {FPGA-Accelerated Quantized Neural Networks on PYNQ-Z2: ECG Arrhythmia
            Detection and Network Intrusion Detection via hls4ml},
  author = {Nandanwar, Vedant and Swami, Tanishq and Wangikar, Arush and Chopde, Abhay},
  institution = {Vishwakarma Institute of Technology, Pune}
}
```
