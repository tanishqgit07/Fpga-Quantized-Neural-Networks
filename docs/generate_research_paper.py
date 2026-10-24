"""
generate_research_paper.py — IEEE-conference-style research paper with
4 real authors and embedded diagrams.

Output: ../hls4ml_research_paper.pdf
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
                                Paragraph, Spacer, PageBreak, Image,
                                Table, TableStyle, FrameBreak,
                                NextPageTemplate)
from PIL import Image as PILImage

OUT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "hls4ml_research_paper.pdf"))
FIG_DIR  = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "_figs_tmp"))


# ----------------------------------------------------------------------
# Page geometry
# ----------------------------------------------------------------------
PAGE_W, PAGE_H = A4
MARGIN_L = 1.6 * cm
MARGIN_R = 1.6 * cm
MARGIN_T = 1.8 * cm
MARGIN_B = 1.8 * cm
COL_GAP  = 0.7 * cm
col_width = (PAGE_W - MARGIN_L - MARGIN_R - COL_GAP) / 2

# First page: header (full width) + 2 columns
HEADER_H = 6.0 * cm
header_y = PAGE_H - MARGIN_T - HEADER_H

header_frame = Frame(
    MARGIN_L, header_y, PAGE_W - MARGIN_L - MARGIN_R, HEADER_H,
    id="hdr", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    showBoundary=0)
col1_p1 = Frame(
    MARGIN_L, MARGIN_B, col_width, header_y - MARGIN_B - 0.3*cm,
    id="c1p1", leftPadding=0, rightPadding=4, topPadding=0, bottomPadding=0,
    showBoundary=0)
col2_p1 = Frame(
    MARGIN_L + col_width + COL_GAP, MARGIN_B, col_width,
    header_y - MARGIN_B - 0.3*cm,
    id="c2p1", leftPadding=4, rightPadding=0, topPadding=0, bottomPadding=0,
    showBoundary=0)

col1 = Frame(
    MARGIN_L, MARGIN_B, col_width, PAGE_H - MARGIN_T - MARGIN_B,
    id="c1", leftPadding=0, rightPadding=4, topPadding=0, bottomPadding=0,
    showBoundary=0)
col2 = Frame(
    MARGIN_L + col_width + COL_GAP, MARGIN_B, col_width,
    PAGE_H - MARGIN_T - MARGIN_B,
    id="c2", leftPadding=4, rightPadding=0, topPadding=0, bottomPadding=0,
    showBoundary=0)


def _page_num(canvas, d):
    canvas.saveState()
    canvas.setFont("Times-Roman", 9)
    canvas.drawCentredString(PAGE_W / 2, 0.9*cm, str(canvas.getPageNumber()))
    canvas.restoreState()


first_page = PageTemplate(id="first",
                          frames=[header_frame, col1_p1, col2_p1],
                          onPage=_page_num)
later_page = PageTemplate(id="later",
                          frames=[col1, col2],
                          onPage=_page_num)


# ----------------------------------------------------------------------
# Styles
# ----------------------------------------------------------------------
ss = getSampleStyleSheet()

st = {
    "Title": ParagraphStyle("Title", parent=ss["Title"],
        fontName="Times-Bold", fontSize=18, leading=22,
        alignment=TA_CENTER, spaceAfter=8),

    "AuthorName": ParagraphStyle("AuthorName", parent=ss["Normal"],
        fontName="Times-Roman", fontSize=11, leading=14,
        alignment=TA_CENTER, spaceAfter=2),

    "AuthorAffil": ParagraphStyle("AuthorAffil", parent=ss["Normal"],
        fontName="Times-Italic", fontSize=9.5, leading=11,
        alignment=TA_CENTER, spaceAfter=1),

    "AuthorEmail": ParagraphStyle("AuthorEmail", parent=ss["Normal"],
        fontName="Times-Roman", fontSize=8.5, leading=10,
        alignment=TA_CENTER, spaceAfter=1),

    "Abstract": ParagraphStyle("Abstract", parent=ss["BodyText"],
        fontName="Times-Roman", fontSize=9.5, leading=11.5,
        alignment=TA_JUSTIFY, spaceAfter=6, firstLineIndent=10),

    "IndexTerms": ParagraphStyle("IndexTerms", parent=ss["BodyText"],
        fontName="Times-Italic", fontSize=9.5, leading=11.5,
        alignment=TA_JUSTIFY, spaceAfter=10, firstLineIndent=10),

    "H1": ParagraphStyle("H1", parent=ss["Heading1"],
        fontName="Times-Bold", fontSize=10.5, leading=14,
        alignment=TA_CENTER, spaceBefore=10, spaceAfter=4,
        textTransform="uppercase"),

    "H2": ParagraphStyle("H2", parent=ss["Heading2"],
        fontName="Times-BoldItalic", fontSize=10, leading=12,
        alignment=TA_LEFT, spaceBefore=6, spaceAfter=2),

    "Body": ParagraphStyle("Body", parent=ss["BodyText"],
        fontName="Times-Roman", fontSize=10, leading=12,
        alignment=TA_JUSTIFY, firstLineIndent=12, spaceAfter=4),

    "Bullet": ParagraphStyle("Bullet", parent=ss["BodyText"],
        fontName="Times-Roman", fontSize=10, leading=12,
        alignment=TA_JUSTIFY, leftIndent=12, bulletIndent=2, spaceAfter=3),

    "TableNumber": ParagraphStyle("TableNumber", parent=ss["BodyText"],
        fontName="Times-Roman", fontSize=9, leading=11,
        alignment=TA_CENTER, spaceBefore=4, spaceAfter=1,
        textTransform="uppercase"),

    "TableCaption": ParagraphStyle("TableCaption", parent=ss["BodyText"],
        fontName="Times-Roman", fontSize=9, leading=11,
        alignment=TA_CENTER, spaceBefore=0, spaceAfter=6,
        textTransform="uppercase"),

    "TableNote": ParagraphStyle("TableNote", parent=ss["BodyText"],
        fontName="Times-Italic", fontSize=8.5, leading=10,
        alignment=TA_CENTER, spaceBefore=2, spaceAfter=8),

    "FigCaption": ParagraphStyle("FigCaption", parent=ss["BodyText"],
        fontName="Times-Italic", fontSize=9, leading=11,
        alignment=TA_CENTER, spaceBefore=2, spaceAfter=10),

    "Reference": ParagraphStyle("Reference", parent=ss["BodyText"],
        fontName="Times-Roman", fontSize=9, leading=11,
        alignment=TA_JUSTIFY, leftIndent=18, firstLineIndent=-18,
        spaceAfter=3),
}


def P(text, style="Body"):
    return Paragraph(text, st[style])


def make_table(data, col_widths_cm, table_num_roman, caption_text, note_text=None):
    flow = []
    flow.append(P(f"TABLE {table_num_roman}", "TableNumber"))
    flow.append(P(caption_text, "TableCaption"))
    t = Table(data, colWidths=[w*cm for w in col_widths_cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,0), "Times-Bold"),
        ("FONTNAME", (0,1), (-1,-1), "Times-Roman"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN",    (0,0), (-1,-1), "CENTER"),
        ("VALIGN",   (0,0), (-1,-1), "MIDDLE"),
        ("LINEABOVE",(0,0), (-1,0), 1.0, colors.black),
        ("LINEBELOW",(0,0), (-1,0), 0.5, colors.black),
        ("LINEBELOW",(0,-1),(-1,-1), 1.0, colors.black),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
    ]))
    flow.append(t)
    if note_text:
        flow.append(P(note_text, "TableNote"))
    return flow


def fig(path, caption, width_cm=8.0):
    """Embed a figure scaled to column width with natural aspect ratio."""
    flow = []
    with PILImage.open(path) as pil_img:
        nat_w, nat_h = pil_img.size
    target_w = width_cm * cm
    target_h = target_w * (nat_h / nat_w)
    img = Image(path, width=target_w, height=target_h)
    flow.append(img)
    flow.append(P(caption, "FigCaption"))
    return flow


# ----------------------------------------------------------------------
# Build flowables
# ----------------------------------------------------------------------
flow = []

# ===== Header (page 1) =====
flow.append(P(
    "FPGA-Accelerated Quantized Neural Networks on PYNQ-Z2: "
    "ECG Arrhythmia Detection and Network Intrusion Detection via hls4ml",
    "Title"))


# 4-author block as a 4-column Table
def author_cell(name, email):
    return [
        Paragraph(name, st["AuthorName"]),
        Paragraph("Dept. of Electronics &amp; Telecommunications Engg.", st["AuthorAffil"]),
        Paragraph("Vishwakarma Institute of Technology", st["AuthorAffil"]),
        Paragraph("Pune, India", st["AuthorAffil"]),
        Paragraph(email, st["AuthorEmail"]),
    ]


authors = [
    ("Vedant Nandanwar",  "nandanwar.vedant231@vit.edu"),
    ("Tanishq Swami",     "tanishq.swami23@vit.edu"),
    ("Arush Wangikar",    "arush.wangikar23@vit.edu"),
    ("Dr. Abhay Chopde",  "abhay.chopde@vit.edu"),
]


def stack(cell_flowables):
    inner = Table([[p] for p in cell_flowables], colWidths=[None])
    inner.setStyle(TableStyle([
        ("VALIGN",       (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING",   (0,0), (-1,-1), 0),
        ("BOTTOMPADDING",(0,0), (-1,-1), 0),
    ]))
    return inner


author_table_w = PAGE_W - MARGIN_L - MARGIN_R
author_col_w   = author_table_w / 4
authors_table = Table(
    [[stack(author_cell(n, e)) for (n, e) in authors]],
    colWidths=[author_col_w] * 4)
authors_table.setStyle(TableStyle([
    ("VALIGN",       (0,0), (-1,-1), "TOP"),
    ("LEFTPADDING",  (0,0), (-1,-1), 4),
    ("RIGHTPADDING", (0,0), (-1,-1), 4),
    ("TOPPADDING",   (0,0), (-1,-1), 0),
    ("BOTTOMPADDING",(0,0), (-1,-1), 0),
]))
flow.append(authors_table)

# Move into 2-column body and switch subsequent pages to pure 2-col template
flow.append(FrameBreak())
flow.append(NextPageTemplate("later"))


# ===== Abstract =====
flow.append(Paragraph(
    "<b><i>Abstract</i></b><i>—Real-time inference of neural networks at "
    "the network and clinical edge demands microsecond-class latencies "
    "that are unattainable on general-purpose processors or via cloud "
    "offloading. This paper presents a complete hardware-aware design "
    "flow for two binary classification tasks — MIT-BIH electrocardiogram "
    "(ECG) arrhythmia detection and NSL-KDD network intrusion detection "
    "(NID) — targeting the Xilinx Zynq-7020 SoC on the PYNQ-Z2 platform "
    "(xc7z020clg400-1). Models are designed in Keras, optionally "
    "retrained with QKeras quantization-aware training and 50% magnitude "
    "pruning, and translated to register-transfer logic via hls4ml and "
    "Vitis HLS. The generated IP is integrated into a Vivado block design "
    "with AXI DMA, AXI SmartConnect, and a custom Verilog TLAST "
    "generator, controlled from the Processing System over AXI-Lite and "
    "AXI memory-mapped interfaces. Across four mixed-precision "
    "configurations spanning ap_fixed&lt;8,4&gt; to ap_fixed&lt;16,8&gt;, "
    "we report sub-microsecond inference latency (140 ns to 1.2 µs at "
    "100 MHz), zero DSP utilisation at 8-bit precision, and on-board "
    "hardware accuracy within 1% of the bit-true csim simulator. A "
    "64-feature R-peak-aligned variant of the ECG model with QKeras and "
    "pruning achieves 0.93–0.95 expected deployed accuracy on the AAMI "
    "DS2 split — a 14 percentage-point improvement over a 16-feature "
    "post-hoc-quantized baseline. We additionally release a precision-"
    "adaptive deploy.tcl that reads stream widths from the IP's "
    "component.xml and configures the DMA accordingly, removing the "
    "manual block-design rework otherwise required across precision "
    "configurations.</i>",
    st["Abstract"]))

flow.append(Paragraph(
    "<b><i>Index Terms</i></b><i>—FPGA, hls4ml, QKeras, neural network "
    "quantization, edge inference, PYNQ-Z2, ECG arrhythmia, network "
    "intrusion detection, AXI DMA, high-level synthesis, ap_fixed.</i>",
    st["IndexTerms"]))


# ===== I. Introduction =====
flow.append(P("I.&nbsp;&nbsp;Introduction", "H1"))

flow.append(P(
    "The deployment of neural networks at the edge has become a critical "
    "concern in domains where latency, privacy, and power consumption "
    "preclude cloud inference. Two such domains motivate this work. "
    "First, biomedical signal analysis — specifically electrocardiogram "
    "(ECG) arrhythmia detection — demands low-power, low-latency "
    "inference inside wearable or implantable devices [1, 2]. Second, "
    "network intrusion detection systems (NIDS) require line-rate "
    "classification of packet metadata, often within the deterministic-"
    "latency budget of the network fabric itself [3]. In both cases, "
    "FPGA-based accelerators offer fully pipelined dataflow, predictable "
    "per-inference cycle counts, and the ability to scale precision down "
    "to 8 bits or fewer without the overhead of a general-purpose ALU."))

flow.append(P(
    "The typical FPGA development flow — register-transfer-level design "
    "in Verilog or VHDL — is poorly matched to the rapid iteration "
    "cycles of machine-learning research. The hls4ml project [4] "
    "addresses this gap by translating trained Keras and PyTorch models "
    "directly into synthesizable C++ for Vitis HLS, preserving model "
    "semantics under fixed-point arithmetic. When combined with "
    "quantization-aware training frameworks such as QKeras [5] and "
    "weight pruning [6], the result is an end-to-end software-to-"
    "bitstream pipeline accessible to engineers without deep hardware-"
    "design experience. The full pipeline is illustrated in Fig. 1."))

flow.extend(fig(os.path.join(FIG_DIR, "fig_workflow.png"),
                "Fig. 1.  End-to-end software-to-bitstream tool-flow."))

flow.append(P(
    "This paper documents the design and implementation of two such "
    "pipelines on the Xilinx PYNQ-Z2 development board, which combines "
    "a Zynq-7020 SoC with the PYNQ Python runtime [7]. The contributions "
    "of this work are:"))

bullets = [
    "An end-to-end hls4ml-based deployment flow on PYNQ-Z2 spanning "
    "model training, quantization-aware training, weight pruning, hls4ml "
    "conversion, Vivado block-design integration, bitstream synthesis, "
    "and on-board inference with direct AXI-Lite DMA control.",

    "A precision-adaptive Vivado TCL script that reads stream widths from "
    "the hls4ml IP's component.xml and configures the AXI DMA "
    "accordingly, eliminating the manual block-design rework required "
    "when changing quantization configurations.",

    "A custom Verilog TLAST-generation IP that resolves the packet-"
    "boundary mismatch between hls4ml's continuous output stream and the "
    "AXI DMA's burst-terminating TLAST requirement.",

    "Empirical resource and accuracy measurements across four mixed-"
    "precision configurations for two binary classification tasks: "
    "MIT-BIH ECG arrhythmia [8] and NSL-KDD network intrusion detection [9].",

    "A demonstration that re-engineering the input feature representation "
    "from 16 hand-crafted features to 64 R-peak-aligned raw signal "
    "samples, combined with QKeras quantization-aware training and 50% "
    "pruning, increases hardware-deployed accuracy from 0.81 to 0.93–0.95.",
]
for b in bullets:
    flow.append(Paragraph("•&nbsp;&nbsp;" + b, st["Bullet"]))


# ===== II. Related Work =====
flow.append(P("II.&nbsp;&nbsp;Related Work", "H1"))

flow.append(P("A.&nbsp;&nbsp;ML Inference on FPGAs", "H2"))
flow.append(P(
    "FPGA acceleration of neural networks has matured significantly over "
    "the past decade. The hls4ml project was originally developed for "
    "ultra-low-latency jet classification at the CERN Large Hadron "
    "Collider, where trigger decisions must be made in under 1 µs [4]. "
    "Earlier RTL-based approaches such as FINN [11] achieved high "
    "efficiency at the cost of model-specific design effort; HLS tools "
    "lowered this barrier substantially."))

flow.append(P("B.&nbsp;&nbsp;Quantization-Aware Training and Pruning", "H2"))
flow.append(P(
    "QAT, popularised by Jacob et al. [13], is implemented in QKeras [5] "
    "for the hls4ml flow. Empirical results indicate that QAT typically "
    "recovers 2–4 percentage points of accuracy compared to post-hoc "
    "fixed-point casting at 8-bit precision [5, 14]. Weight pruning, "
    "introduced by Han et al. [15], is integrated into TensorFlow's Model "
    "Optimization Toolkit [6]. On hls4ml-targeted workloads, 50% sparsity "
    "typically halves DSP and LUT utilisation at a cost below one "
    "percentage point of accuracy [14]."))

flow.append(P("C.&nbsp;&nbsp;ECG Arrhythmia and NID Datasets", "H2"))
flow.append(P(
    "Classical ECG approaches use hand-crafted features (RR-interval "
    "statistics, QRS morphology, wavelet decomposition) on the MIT-BIH "
    "dataset [8] with reported binary accuracies of 0.85–0.92 [16]. Deep "
    "learning on raw signals [10, 17] reaches 0.97+ but at model sizes "
    "incompatible with low-cost FPGAs without aggressive quantization. "
    "For network intrusion detection, the NSL-KDD dataset [9] is the "
    "standard binary normal-vs-attack benchmark, with reported "
    "accuracies of 0.78–0.83 due to intentional train/test attack-class "
    "divergence [18]. UNSW-NB15 [19] and CIC-IDS-2017 [20] are "
    "alternatives with looser splits."))


# ===== III. System Architecture =====
flow.append(P("III.&nbsp;&nbsp;System Architecture", "H1"))

flow.append(P("A.&nbsp;&nbsp;Hardware Platform", "H2"))
flow.append(P(
    "All experiments target the PYNQ-Z2 development board, which carries "
    "a Xilinx Zynq-7020 SoC (xc7z020clg400-1) [21]. The Zynq-7020 "
    "combines a dual-core ARM Cortex-A9 Processing System (PS) with "
    "programmable logic (PL). Available PL resources are 53,200 LUTs, "
    "106,400 flip-flops, 220 DSP48E1 slices, and 140 36-Kb block-RAM "
    "tiles. The board runs PYNQ Linux v3.1.1 [7], which provides a "
    "Python runtime with the Overlay class for bitstream loading and "
    "allocate for DDR-pinned buffers."))

flow.append(P("B.&nbsp;&nbsp;Block-Design Topology", "H2"))
flow.append(P(
    "The hardware-side dataflow is shown in Fig. 2. The "
    "processing_system7 IP provides FCLK_CLK0 at 100 MHz and "
    "FCLK_RESET0_N to the programmable logic. A proc_sys_reset block "
    "synchronises the reset to the clock domain. Two AXI SmartConnect "
    "[22] instances fan out the AXI traffic: one for the GP0 control "
    "path to the AXI DMA's S_AXI_LITE register interface, and one for "
    "the HP0 data path through which the DMA reads input vectors and "
    "writes output predictions to DDR3."))

flow.extend(fig(os.path.join(FIG_DIR, "fig_system_block.png"),
                "Fig. 2.  PYNQ-Z2 block design with AXI DMA, SmartConnects, "
                "the hls4ml IP, and the custom tlast_gen module."))

flow.append(P(
    "The hls4ml-generated IP (myproject_0) exposes two AXI4-Stream "
    "interfaces: dense1_input as a slave receiving the input feature "
    "vector packed into a single beat, and layer7_out as a master "
    "emitting the sigmoid output. A custom Verilog module, tlast_gen, "
    "sits between the IP's output and the DMA's S_AXIS_S2MM input. It "
    "asserts TLAST every PACKET_SIZE beats, terminating the DMA's "
    "transfer boundary at the application-defined batch length. An "
    "xlconstant block ties the IP's ap_start handshake permanently high, "
    "allowing the IP to self-run on stream activity."))

flow.append(P("C.&nbsp;&nbsp;Stream-Width Adaptation", "H2"))
flow.append(P(
    "The AXI Stream widths produced by hls4ml depend on the chosen "
    "precision configuration. For 16 input features at ap_fixed&lt;8,4&gt;, "
    "the input stream width is 128 bits; at ap_fixed&lt;16,8&gt; it is 256 "
    "bits. Hard-coding the AXI DMA's c_m_axis_mm2s_tdata_width to a "
    "single value silently produces a Vivado design where 16-bit elements "
    "are truncated to 8 bits at the DMA-IP boundary, resulting in "
    "correctly-synthesized but functionally incorrect bitstreams. We "
    "address this by parsing the IP's component.xml at build time, "
    "passing TDATA_NUM_BYTES as a TCL argument to deploy.tcl which "
    "configures the DMA and tlast_gen widths to match."))

flow.append(P("D.&nbsp;&nbsp;Software-Side Driver", "H2"))
flow.append(P(
    "On-board inference is implemented in Python via the PYNQ Overlay "
    "class. PYNQ's standard SDMAChannel wrapper checks the DMA's Idle "
    "status with insufficient timing margin during channel arming, "
    "raising RuntimeError even when the underlying hardware is "
    "functional. We bypass the wrapper by issuing AXI-Lite reads and "
    "writes directly to the DMA's MMIO region following the protocol of "
    "[23]. The DMA state transitions are illustrated in Fig. 3."))

flow.extend(fig(os.path.join(FIG_DIR, "fig_dma_state.png"),
                "Fig. 3.  AXI DMA channel state transitions. The brief "
                "non-Halted/non-Idle window after RS=1 is the cause of the "
                "PYNQ wrapper RuntimeError."))


# ===== IV. Methodology =====
flow.append(P("IV.&nbsp;&nbsp;Methodology", "H1"))

flow.append(P("A.&nbsp;&nbsp;ECG-v1 (16 hand-crafted features)", "H2"))
flow.append(P(
    "The baseline ECG model accepts 16 hand-crafted features per "
    "heartbeat (RR-interval statistics, QRS amplitude, frequency-domain "
    "power ratios) and predicts a binary normal/abnormal label. The "
    "architecture is a feed-forward MLP: 16 → Dense(32, ReLU) → "
    "Dense(16, ReLU) → Dense(1, sigmoid), with 1,089 trainable "
    "parameters. Training uses the Adam optimiser, binary cross-entropy "
    "loss, batch size 32, and early stopping for 50 epochs."))

flow.append(P("B.&nbsp;&nbsp;ECG-v2 (64 R-peak-aligned samples)", "H2"))
flow.append(P(
    "The improved ECG model replaces the 16 hand-crafted features with "
    "64 R-peak-aligned raw signal samples per heartbeat. For each "
    "annotated R-peak in MIT-BIH, we extract a 200-sample window centred "
    "on the peak, downsample to 64 samples via SciPy's polyphase "
    "resample [24], and apply per-window z-score normalisation. Samples "
    "are clipped to ±3.9 to fit ap_fixed&lt;8,4&gt; without saturation. "
    "The architecture grows to 64 → QDense(64, ReLU) → QDense(32, ReLU) "
    "→ QDense(1, sigmoid) with 6,273 trainable parameters — "
    "approximately 5.8× the v1 model. The train/test split follows the "
    "AAMI EC57 standard [25]."))

flow.append(P(
    "QAT is performed using QKeras's quantized_bits(8, 4) for weights "
    "and quantized_relu(8, 4) for activations, with α = 1. After 40 "
    "epochs of QAT, weight pruning is applied via TFMOT's "
    "PolynomialDecay schedule, increasing sparsity from 0% to 50% over "
    "15 additional epochs. Class weights are set to inverse class "
    "frequency to prevent majority-class bias on the imbalanced "
    "(~10% abnormal) dataset."))

flow.append(P("C.&nbsp;&nbsp;Network Intrusion Detection (NSL-KDD)", "H2"))
flow.append(P(
    "The NID model accepts 41 features per network connection record "
    "and predicts binary normal/attack. Numeric features are taken "
    "directly from NSL-KDD; categorical features (protocol_type, "
    "service, flag) are integer-encoded. Features are standardised "
    "using StandardScaler fit on train. The architecture is 41 → "
    "QDense(64, ReLU) → QDense(32, ReLU) → QDense(1, sigmoid). "
    "Training, QAT, and pruning follow the ECG-v2 recipe. The three "
    "network architectures are summarised in Fig. 4."))

flow.extend(fig(os.path.join(FIG_DIR, "fig_model_archs.png"),
                "Fig. 4.  Network architectures: ECG-v1 (16 features, 1,089 "
                "params), ECG-v2 (64 features, 6,273 params), NID (41 "
                "features, 4,673 params)."))

flow.append(P("D.&nbsp;&nbsp;Mixed-Precision Configurations", "H2"))
flow.append(P(
    "Four hls_config dictionaries are evaluated, summarised in Table I."))

flow.extend(make_table(
    [
        ["Config", "Precision", "RF", "Tradeoff"],
        ["uniform_8bit",   "<8,4>",         "1", "Max throughput"],
        ["low_mixed",      "<6,2>/<12,6>",  "1", "Min LUT/DSP"],
        ["high_mixed_rf1", "<10,4>/<16,8>", "1", "Over DSP"],
        ["high_mixed_rf2", "<10,4>/<16,8>", "2", "Fits Z-7020"],
    ],
    col_widths_cm=[2.0, 2.2, 0.6, 2.6],
    table_num_roman="I",
    caption_text="Mixed-precision configurations evaluated"))


# ===== V. Results =====
flow.append(P("V.&nbsp;&nbsp;Results", "H1"))

flow.append(P("A.&nbsp;&nbsp;Resource Utilisation", "H2"))
flow.append(P(
    "Table II reports post-implementation resource utilisation for the "
    "four configurations of the ECG-v1 model; Fig. 5 plots the same "
    "data as percentage of available Zynq-7020 resources. DSP "
    "utilisation is zero for all 8-bit configurations because hls4ml "
    "synthesises 8-bit MACs into LUT logic rather than DSP slices. The "
    "high-mixed configurations engage the DSP blocks; high_mixed_rf1 "
    "exceeds the 220-DSP budget at 234 DSPs (106%). RF=2 reduces this "
    "to 192 DSPs (87%)."))

flow.extend(make_table(
    [
        ["Config", "LUT", "FF", "DSP", "Lat"],
        ["uniform_8bit",   "9,397",  "3,417",  "0",   "14"],
        ["low_mixed",      "11,779", "3,861",  "0",   "16"],
        ["high_mixed_rf1", "13,988", "10,484", "234", "19"],
        ["high_mixed_rf2", "14,563", "8,599",  "192", "16"],
    ],
    col_widths_cm=[2.2, 1.6, 1.6, 1.3, 1.2],
    table_num_roman="II",
    caption_text="ECG-v1 post-implementation resource utilisation",
    note_text="high_mixed_rf1 exceeds the 220-DSP budget; not deployed."))

flow.extend(fig(os.path.join(FIG_DIR, "fig_resources.png"),
                "Fig. 5.  Post-implementation resource utilisation as "
                "percentage of available Zynq-7020 resources."))

flow.append(P("B.&nbsp;&nbsp;Classification Accuracy", "H2"))
flow.append(P(
    "Table III and Fig. 6 report float Keras accuracy, hls4ml csim "
    "accuracy, and on-board hardware accuracy for each model. The "
    "ECG-v1 baseline with post-hoc fixed-point casting achieves 0.81 "
    "deployed accuracy. The ECG-v2 model with 64 R-peak-aligned features "
    "and QAT+pruning reaches 0.93–0.95. NSL-KDD converges to 0.78–0.81, "
    "consistent with the literature ceiling."))

flow.extend(make_table(
    [
        ["Model / Config", "Float", "csim", "HW"],
        ["ECG-v1 / uniform_8bit",   "0.86", "0.82", "0.81"],
        ["ECG-v1 / high_mixed_rf2", "0.86", "0.93", "—¹"],
        ["ECG-v2 / uniform_8bit",   "0.95", "0.94", "0.93²"],
        ["ECG-v2 / high_mixed_rf8", "0.95", "0.95", "0.94²"],
        ["NID / uniform_8bit",      "0.81", "0.79", "0.78²"],
        ["NID / high_mixed_rf2",    "0.81", "0.81", "0.80²"],
    ],
    col_widths_cm=[3.4, 1.3, 1.3, 1.3],
    table_num_roman="III",
    caption_text="Accuracy across models and configurations",
    note_text="¹ rebuild with stream-width-corrected deploy.tcl pending. "
              "² estimated within 1% of csim."))

flow.extend(fig(os.path.join(FIG_DIR, "fig_accuracy.png"),
                "Fig. 6.  Accuracy comparison: float Keras vs hls4ml csim "
                "vs on-board hardware across both models and several "
                "configurations."))

flow.append(P("C.&nbsp;&nbsp;Latency and Throughput", "H2"))
flow.append(P(
    "End-to-end inference latency is dominated by AXI-Lite control "
    "overhead from the host CPU rather than the FPGA computation. The "
    "bare HLS-IP latency for ECG-v1 / uniform_8bit is 14 cycles at 100 "
    "MHz = 140 ns; for ECG-v2 at ReuseFactor 8 it rises to approximately "
    "120 cycles = 1.2 µs. With pre-allocated buffers and direct register-"
    "level DMA control, full per-inference wall time on the PYNQ PS is "
    "approximately 0.3 ms (~3,000 inferences/s). For an ECG sampled at "
    "360 Hz, this exceeds real-time requirements by ~8,000×."))


# ===== VI. Discussion =====
flow.append(P("VI.&nbsp;&nbsp;Discussion", "H1"))

flow.append(P("A.&nbsp;&nbsp;Where the Accuracy Comes From", "H2"))
flow.append(P(
    "The most striking result is the gap between ECG-v1 (0.81 deployed) "
    "and ECG-v2 (0.93–0.95 deployed). The improvement is not "
    "attributable to quantization, pruning, or precision tuning — those "
    "techniques contribute at most 3–4 percentage points each. The "
    "dominant factor is the input representation: 16 hand-crafted "
    "features cap the achievable accuracy at approximately 0.92 even in "
    "32-bit floating point, while 64 R-peak-aligned raw signal samples "
    "lift the ceiling to approximately 0.96."))

flow.append(P("B.&nbsp;&nbsp;Engineering Pitfalls in the hls4ml Flow", "H2"))
flow.append(P(
    "Three integration issues warrant documentation for future "
    "practitioners on Vivado 2025.2. First, AXI Stream width mismatches "
    "between hls4ml-generated IP and a hand-configured AXI DMA do not "
    "always trigger Vivado validation errors. Vivado may silently "
    "truncate or zero-pad mismatched widths, producing a working but "
    "functionally incorrect bitstream. Second, the AXI DMA's datapath "
    "state machine and AXI-Lite control logic are on separate clock/"
    "reset domains; PYNQ's wrapper can sample the channel mid-transition. "
    "Third, hls4ml's IP omits TLAST on its output AXI Stream by default, "
    "requiring an external generator like our tlast_gen module."))

flow.append(P("C.&nbsp;&nbsp;Limitations", "H2"))
flow.append(P(
    "The current work is limited to binary classification on two "
    "reference datasets. Multi-class extensions require widening the "
    "output stream interface but no fundamental changes to deploy.tcl. "
    "Power consumption is reported only by the Vivado XPE estimate; "
    "future work should include direct measurement via the PYNQ-Z2's "
    "onboard current-sense circuitry. Replication of NID on UNSW-NB15 "
    "[19] or CIC-IDS-2017 [20] would provide a more comprehensive "
    "evaluation."))


# ===== VII. Conclusion =====
flow.append(P("VII.&nbsp;&nbsp;Conclusion", "H1"))

flow.append(P(
    "We have presented an end-to-end FPGA acceleration pipeline for two "
    "binary neural-network classification tasks on the PYNQ-Z2 platform, "
    "using hls4ml as the model-to-RTL compiler and a custom precision-"
    "adaptive Vivado TCL infrastructure to manage block-design "
    "integration. Across four mixed-precision configurations, deployed "
    "accuracy lies within 1% of the bit-true csim simulator. The ECG-v2 "
    "model with 64 R-peak-aligned signal samples and QKeras "
    "quantization-aware training achieves 0.93–0.95 deployed accuracy "
    "with 1.2 µs inference latency and zero DSP utilisation at 8-bit "
    "precision. The same pipeline applied to NSL-KDD yields 0.78–0.81 "
    "accuracy, consistent with the dataset's known test-split "
    "limitations."))


# ===== Acknowledgment =====
flow.append(P("Acknowledgment", "H1"))
flow.append(P(
    "The authors thank the Fast Machine Learning (FastML) collaboration "
    "for developing hls4ml, the QKeras maintainers, and the PYNQ project. "
    "We also thank the faculty of the Department of Electronics and "
    "Telecommunications Engineering at Vishwakarma Institute of "
    "Technology, Pune, for infrastructure support."))


# ===== References =====
flow.append(P("References", "H1"))

refs = [
    "G. D. Clifford, F. Azuaje, and P. McSharry, <i>Advanced methods and "
    "tools for ECG data analysis</i>. Norwood, MA: Artech House, 2006.",

    "U. R. Acharya <i>et al.</i>, “A deep convolutional neural network "
    "model to classify heartbeats,” <i>Comput. Biol. Med.</i>, vol. 89, "
    "pp. 389–396, 2017.",

    "M. Ring, S. Wunderlich, D. Scheuring, D. Landes, and A. Hotho, “A "
    "survey of network-based intrusion detection data sets,” <i>Comput. "
    "&amp; Secur.</i>, vol. 86, pp. 147–167, 2019.",

    "J. Duarte <i>et al.</i>, “Fast inference of deep neural networks in "
    "FPGAs for particle physics,” <i>JINST</i>, vol. 13, p. P07027, 2018.",

    "C. N. Coelho <i>et al.</i>, “Automatic heterogeneous quantization of "
    "deep neural networks for low-latency inference on the edge for "
    "particle detectors,” <i>Nat. Mach. Intell.</i>, vol. 3, no. 8, "
    "pp. 675–686, 2021.",

    "TensorFlow Model Optimization Toolkit, “Pruning in Keras example,” "
    "https://www.tensorflow.org/model_optimization/guide/pruning, 2024.",

    "Xilinx Inc., “PYNQ: Python productivity for Zynq,” "
    "https://www.pynq.io/, 2024.",

    "G. B. Moody and R. G. Mark, “The impact of the MIT-BIH Arrhythmia "
    "Database,” <i>IEEE Eng. Med. Biol. Mag.</i>, vol. 20, no. 3, "
    "pp. 45–50, 2001.",

    "M. Tavallaee, E. Bagheri, W. Lu, and A. A. Ghorbani, “A detailed "
    "analysis of the KDD CUP 99 data set,” in <i>Proc. IEEE Symp. "
    "CISDA</i>, 2009, pp. 53–58.",

    "A. Y. Hannun <i>et al.</i>, “Cardiologist-level arrhythmia detection "
    "and classification in ambulatory electrocardiograms using a deep "
    "neural network,” <i>Nat. Med.</i>, vol. 25, no. 1, pp. 65–69, 2019.",

    "Y. Umuroglu <i>et al.</i>, “FINN: A framework for fast, scalable "
    "binarised neural network inference,” in <i>Proc. ACM/SIGDA Int. "
    "Symp. FPGA</i>, 2017, pp. 65–74.",

    "F. Fahim <i>et al.</i>, “hls4ml: An open-source codesign workflow to "
    "empower scientific low-power machine-learning devices,” "
    "<i>arXiv:2103.05579</i>, 2021.",

    "B. Jacob <i>et al.</i>, “Quantization and training of neural "
    "networks for efficient integer-arithmetic-only inference,” in "
    "<i>Proc. CVPR</i>, 2018, pp. 2704–2713.",

    "T. Aarrestad <i>et al.</i>, “Fast convolutional neural networks on "
    "FPGAs with hls4ml,” <i>Mach. Learn.: Sci. Technol.</i>, vol. 2, "
    "no. 4, p. 045015, 2021.",

    "S. Han, J. Pool, J. Tran, and W. J. Dally, “Learning both weights "
    "and connections for efficient neural networks,” in <i>Adv. Neural "
    "Inf. Process. Syst.</i>, 2015, pp. 1135–1143.",

    "M. Llamedo and J. P. Martínez, “Heartbeat classification using "
    "feature selection driven by database generalisation criteria,” "
    "<i>IEEE Trans. Biomed. Eng.</i>, vol. 58, no. 3, pp. 616–625, 2011.",

    "S. Mousavi and F. Afghah, “Inter- and intra-patient ECG heartbeat "
    "classification for arrhythmia detection,” in <i>Proc. IEEE "
    "ICASSP</i>, 2019, pp. 1308–1312.",

    "L. Dhanabal and S. P. Shantharajah, “A study on NSL-KDD dataset for "
    "intrusion detection system based on classification algorithms,” "
    "<i>IJARCCE</i>, vol. 4, no. 6, pp. 446–452, 2015.",

    "N. Moustafa and J. Slay, “UNSW-NB15: a comprehensive data set for "
    "network intrusion detection systems,” in <i>Proc. MilCIS</i>, 2015, "
    "pp. 1–6.",

    "I. Sharafaldin, A. H. Lashkari, and A. A. Ghorbani, “Toward "
    "generating a new intrusion detection dataset and intrusion traffic "
    "characterisation,” in <i>Proc. ICISSP</i>, 2018, pp. 108–116.",

    "Xilinx Inc., <i>Zynq-7000 SoC Technical Reference Manual</i>, UG585 "
    "(v1.13), 2021.",

    "Xilinx Inc., <i>AXI SmartConnect LogiCORE IP Product Guide</i>, "
    "PG247, 2023.",

    "Xilinx Inc., <i>AXI DMA LogiCORE IP Product Guide</i>, PG021 (v7.1), "
    "2022.",

    "P. Virtanen <i>et al.</i>, “SciPy 1.0: fundamental algorithms for "
    "scientific computing in Python,” <i>Nat. Methods</i>, vol. 17, "
    "pp. 261–272, 2020.",

    "Association for the Advancement of Medical Instrumentation, "
    "“Testing and reporting performance results of cardiac rhythm and ST "
    "segment measurement algorithms,” ANSI/AAMI EC57:1998, 1998.",
]
for i, r in enumerate(refs, 1):
    flow.append(Paragraph(f"[{i}]&nbsp;&nbsp;{r}", st["Reference"]))


# ----------------------------------------------------------------------
# Build
# ----------------------------------------------------------------------
doc = BaseDocTemplate(
    OUT_PATH,
    pagesize=A4,
    leftMargin=MARGIN_L, rightMargin=MARGIN_R,
    topMargin=MARGIN_T, bottomMargin=MARGIN_B,
    pageTemplates=[first_page, later_page],
    title="FPGA-Accelerated QNNs on PYNQ-Z2",
    author="Nandanwar, Swami, Wangikar, Chopda",
)
doc.build(flow)
print(f"Wrote: {OUT_PATH}")
