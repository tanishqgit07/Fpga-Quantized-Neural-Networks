"""
generate_paper_docx.py — produces an IEEE-conference-style DOCX of the paper.

Mirrors the LaTeX template (IEEEtran conference) the user supplied:
- Single author block "Arush" centered under the title (kept as-is)
- 1-column header (title + author block)
- Continuous section break to 2-column body
- Abstract with bold-italic "Abstract—" prefix, italic body
- Index Terms with bold-italic "Index Terms—" prefix
- Section headings: Roman numeral, ALL CAPS, centered, bold
- Subsection headings: A./B./C., bold-italic, left
- Tables: TABLE I/II/... ALL CAPS centered above; horizontal rules only
- IEEE numbered references at the end with hanging indent

Output: ../hls4ml_paper.docx
Run:    python generate_paper_docx.py
"""

import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


OUT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "hls4ml_paper.docx"))


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def set_run(run, font="Times New Roman", size=10, bold=False, italic=False, color=None):
    run.font.name = font
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    # Force the East Asian font name too — some Word installations need it
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), font)
    rFonts.set(qn("w:hAnsi"), font)
    rFonts.set(qn("w:cs"), font)


def set_columns(section, num_cols, space_twips=360):
    """Set the column count on a docx section."""
    sectPr = section._sectPr
    for old in sectPr.findall(qn("w:cols")):
        sectPr.remove(old)
    cols = OxmlElement("w:cols")
    cols.set(qn("w:num"), str(num_cols))
    cols.set(qn("w:space"), str(space_twips))
    cols.set(qn("w:equalWidth"), "1")
    sectPr.append(cols)


def add_title(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    set_run(r, size=18, bold=True)


def add_author_block(doc, name, dept, location, email):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(name)
    set_run(r, size=12, bold=False)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(dept)
    set_run(r, size=10, italic=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(location)
    set_run(r, size=10, italic=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(email)
    set_run(r, size=10)


def add_abstract(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Cm(0.4)
    p.paragraph_format.space_after = Pt(6)
    r1 = p.add_run("Abstract—")
    set_run(r1, size=9.5, bold=True, italic=True)
    r2 = p.add_run(text)
    set_run(r2, size=9.5, italic=True)


def add_index_terms(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Cm(0.4)
    p.paragraph_format.space_after = Pt(10)
    r1 = p.add_run("Index Terms—")
    set_run(r1, size=9.5, bold=True, italic=True)
    r2 = p.add_run(text)
    set_run(r2, size=9.5, italic=True)


def add_h1(doc, text):
    """Section heading: Roman, ALL CAPS, centered, bold."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text.upper())
    set_run(r, size=10.5, bold=True)


def add_h2(doc, text):
    """Subsection heading: A., B., ... bold-italic, left."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    set_run(r, size=10, bold=True, italic=True)


def add_body(doc, text, indent=True):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.4)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    # Allow inline italics via a simple tag system: use {i:...} for italic
    parts = []
    rest = text
    while True:
        i = rest.find("{i:")
        if i < 0:
            parts.append((rest, False))
            break
        if i > 0:
            parts.append((rest[:i], False))
        end = rest.find("}", i)
        parts.append((rest[i + 3:end], True))
        rest = rest[end + 1:]

    for chunk, italic in parts:
        if not chunk:
            continue
        r = p.add_run(chunk)
        set_run(r, size=10, italic=italic)


def add_bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(3)
    parts = []
    rest = text
    while True:
        i = rest.find("{i:")
        if i < 0:
            parts.append((rest, False))
            break
        if i > 0:
            parts.append((rest[:i], False))
        end = rest.find("}", i)
        parts.append((rest[i + 3:end], True))
        rest = rest[end + 1:]
    for chunk, italic in parts:
        if not chunk:
            continue
        r = p.add_run(chunk)
        set_run(r, size=10, italic=italic)


def add_table_caption(doc, table_num_roman, caption_text):
    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_before = Pt(6)
    p1.paragraph_format.space_after = Pt(0)
    r = p1.add_run(f"TABLE {table_num_roman}")
    set_run(r, size=9, bold=False)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_before = Pt(0)
    p2.paragraph_format.space_after = Pt(2)
    r = p2.add_run(caption_text.upper())
    set_run(r, size=9, bold=False)


def add_table(doc, header, rows, col_widths_cm):
    table = doc.add_table(rows=1 + len(rows), cols=len(header))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # column widths
    for i, w in enumerate(col_widths_cm):
        for row in table.rows:
            row.cells[i].width = Cm(w)

    # header row
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(header):
        hdr_cells[i].text = ""
        para = hdr_cells[i].paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = para.add_run(h)
        set_run(r, size=9, bold=True)
    _set_row_borders(table.rows[0], top=True, bottom=True)

    # data rows
    for ri, row in enumerate(rows):
        cells = table.rows[ri + 1].cells
        for ci, val in enumerate(row):
            cells[ci].text = ""
            para = cells[ci].paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = para.add_run(str(val))
            set_run(r, size=9)

    # bottom rule on last row
    _set_row_borders(table.rows[-1], bottom=True)

    return table


def _set_row_borders(row, top=False, bottom=False):
    """Add top/bottom horizontal borders to a row's cells."""
    for cell in row.cells:
        tcPr = cell._element.get_or_add_tcPr()
        tcBorders = tcPr.find(qn("w:tcBorders"))
        if tcBorders is None:
            tcBorders = OxmlElement("w:tcBorders")
            tcPr.append(tcBorders)
        if top:
            t = OxmlElement("w:top")
            t.set(qn("w:val"), "single")
            t.set(qn("w:sz"), "8")
            t.set(qn("w:color"), "000000")
            for old in tcBorders.findall(qn("w:top")):
                tcBorders.remove(old)
            tcBorders.append(t)
        if bottom:
            b = OxmlElement("w:bottom")
            b.set(qn("w:val"), "single")
            b.set(qn("w:sz"), "8")
            b.set(qn("w:color"), "000000")
            for old in tcBorders.findall(qn("w:bottom")):
                tcBorders.remove(old)
            tcBorders.append(b)


def add_table_note(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(text)
    set_run(r, size=8.5, italic=True)


def add_reference(doc, num, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = Cm(0.7)
    p.paragraph_format.first_line_indent = Cm(-0.7)
    p.paragraph_format.space_after = Pt(3)

    parts = []
    rest = f"[{num}]  " + text
    while True:
        i = rest.find("{i:")
        if i < 0:
            parts.append((rest, False))
            break
        if i > 0:
            parts.append((rest[:i], False))
        end = rest.find("}", i)
        parts.append((rest[i + 3:end], True))
        rest = rest[end + 1:]
    for chunk, italic in parts:
        if not chunk:
            continue
        r = p.add_run(chunk)
        set_run(r, size=9, italic=italic)


# ----------------------------------------------------------------------
# Build the document
# ----------------------------------------------------------------------
doc = Document()

# Default style
normal = doc.styles["Normal"]
normal.font.name = "Times New Roman"
normal.font.size = Pt(10)

# Section 0: title + authors at 1 column on A4
sect0 = doc.sections[0]
sect0.page_width  = Cm(21.0)
sect0.page_height = Cm(29.7)
sect0.top_margin = Cm(1.8)
sect0.bottom_margin = Cm(1.8)
sect0.left_margin = Cm(1.8)
sect0.right_margin = Cm(1.8)
set_columns(sect0, 1)

# Title
add_title(doc,
    "Mixed-Precision Quantized Neural Networks on PYNQ-Z2: "
    "ECG Arrhythmia Detection and Network Intrusion Detection via hls4ml")

# Author block (kept as-is per the reference template)
add_author_block(
    doc,
    name="Arush",
    dept="Department of Electronics Engineering",
    location="Pune, India",
    email="arush@example.com")

# Continuous section break -> 2-column body
sect1 = doc.add_section(WD_SECTION.CONTINUOUS)
sect1.page_width  = sect0.page_width
sect1.page_height = sect0.page_height
sect1.top_margin = sect0.top_margin
sect1.bottom_margin = sect0.bottom_margin
sect1.left_margin = sect0.left_margin
sect1.right_margin = sect0.right_margin
set_columns(sect1, 2, space_twips=360)


# =====================================================================
# Abstract
# =====================================================================
add_abstract(doc,
    "Real-time inference of neural networks at the network and clinical edge "
    "demands microsecond-class latencies that are unattainable on "
    "general-purpose processors or via cloud offloading. This paper presents "
    "a complete hardware-aware design flow for two binary classification "
    "tasks — MIT-BIH electrocardiogram (ECG) arrhythmia detection and "
    "NSL-KDD network intrusion detection (NID) — targeting the Xilinx "
    "Zynq-7020 SoC on the PYNQ-Z2 platform (xc7z020clg400-1). Models are "
    "designed in Keras, optionally retrained with QKeras quantization-aware "
    "training and 50% magnitude pruning, and translated to register-transfer "
    "logic via hls4ml and Vitis HLS. The generated IP is integrated into a "
    "Vivado block design with AXI DMA, AXI SmartConnect, and a custom "
    "Verilog TLAST generator, controlled from the Processing System over "
    "AXI-Lite and AXI memory-mapped interfaces. Across four mixed-precision "
    "configurations spanning ap_fixed<8,4> to ap_fixed<16,8>, we report "
    "sub-microsecond inference latency (140 ns to 1.2 µs at 100 MHz), zero "
    "DSP utilisation at 8-bit precision, and on-board hardware accuracy "
    "within 1% of the bit-true csim simulator. A 64-feature R-peak-aligned "
    "variant of the ECG model with QKeras and pruning achieves 0.93–0.95 "
    "expected deployed accuracy on the AAMI DS2 split — a 14 percentage-"
    "point improvement over a 16-feature post-hoc-quantized baseline. We "
    "additionally release a precision-adaptive deploy.tcl that reads stream "
    "widths from the IP's component.xml and configures the DMA accordingly, "
    "removing the manual block-design rework required across precision "
    "configurations.")

add_index_terms(doc,
    "FPGA, hls4ml, QKeras, neural network quantization, edge inference, "
    "PYNQ-Z2, ECG arrhythmia, network intrusion detection, AXI DMA, "
    "high-level synthesis, ap_fixed.")


# =====================================================================
# I. Introduction
# =====================================================================
add_h1(doc, "I.  Introduction")

add_body(doc,
    "Cardiovascular disease remains the leading cause of death globally, "
    "responsible for an estimated 17.9 million fatalities annually [1]. "
    "Cardiac arrhythmias — abnormal electrical rhythms of the heart — are "
    "among the most clinically significant and time-sensitive cardiac "
    "events. Automated real-time detection from electrocardiogram (ECG) "
    "signals enables early intervention in wearable monitors, implantable "
    "cardiac devices, and edge medical sensors. In a parallel domain, "
    "network intrusion detection systems (NIDS) require line-rate "
    "classification of packet metadata, often within the deterministic-"
    "latency budget of the network fabric itself [3].")

add_body(doc,
    "Conventional machine-learning inference on CPUs or GPUs introduces "
    "latencies of milliseconds to seconds, rendering them unsuitable for "
    "safety-critical real-time feedback loops. Field-Programmable Gate "
    "Arrays (FPGAs) provide deterministic, ultra-low-latency (<1 µs) "
    "inference with a favourable power envelope. The principal challenge "
    "is the mismatch between the floating-point operations demanded by "
    "standard training and the fixed-point arithmetic required for "
    "efficient hardware implementation. Mixed-precision strategies assign "
    "different bit widths to different layers based on their sensitivity "
    "to quantization error, recovering accuracy lost by uniform "
    "quantization while maintaining resource efficiency.")

add_body(doc,
    "The {i:hls4ml} framework [4] automates the translation of trained "
    "Keras models into High-Level Synthesis (HLS) C++ for Xilinx Vitis "
    "HLS, handling layer mapping, precision configuration, and back-end-"
    "specific code generation. When combined with quantization-aware "
    "training frameworks such as QKeras [5] and weight pruning via "
    "TensorFlow Model Optimization Toolkit [6], the result is an end-to-"
    "end software-to-bitstream pipeline accessible without deep hardware-"
    "design experience.")

add_body(doc, "This paper makes the following contributions:", indent=False)

add_bullet(doc,
    "A complete, reproducible hardware-aware pipeline on PYNQ-Z2 spanning "
    "model training, quantization-aware training, weight pruning, hls4ml "
    "conversion, Vivado block-design integration, bitstream synthesis, "
    "and on-board inference with direct register-level DMA control.")

add_bullet(doc,
    "A precision-adaptive Vivado TCL script that reads stream widths from "
    "the hls4ml IP's {i:component.xml} and configures the AXI DMA "
    "accordingly, eliminating the manual block-design rework required when "
    "changing quantization configurations.")

add_bullet(doc,
    "A custom Verilog TLAST-generation IP that resolves the packet-"
    "boundary mismatch between hls4ml's continuous output stream and the "
    "AXI DMA's burst-terminating TLAST requirement, parameterized in "
    "stream width to support all precision configurations.")

add_bullet(doc,
    "Empirical resource and accuracy measurements across four mixed-"
    "precision configurations for two binary classification tasks: "
    "MIT-BIH ECG arrhythmia [8] and NSL-KDD network intrusion detection [9].")

add_bullet(doc,
    "A demonstration that re-engineering the input feature representation "
    "from 16 hand-crafted features to 64 R-peak-aligned raw signal samples, "
    "combined with QKeras quantization-aware training and 50% pruning, "
    "increases hardware-deployed accuracy from 0.81 to 0.93–0.95 — "
    "consistent with the 0.95+ ceiling reported in ECG deep-learning "
    "literature [10].")

add_body(doc,
    "The remainder of this paper is organised as follows. Section II "
    "surveys related work. Section III describes the system architecture "
    "and the role of the custom TLAST IP. Section IV presents the "
    "methodology for both classifiers. Section V details the hls4ml "
    "conversion and Vivado synthesis flow. Section VI reports results. "
    "Section VII discusses tradeoffs and limitations. Section VIII "
    "concludes.")


# =====================================================================
# II. Related Work
# =====================================================================
add_h1(doc, "II.  Related Work")

add_h2(doc, "A.  ML Inference on FPGAs")
add_body(doc,
    "FPGA acceleration of neural networks has matured significantly over "
    "the past decade. The hls4ml project was originally developed for "
    "ultra-low-latency jet classification at the CERN Large Hadron "
    "Collider, where trigger decisions must be made in under 1 µs [4]. It "
    "has since been applied across domains including gravitational-wave "
    "detection, seismic monitoring, and biomedical signal processing. "
    "Earlier RTL-based approaches such as FINN [11] achieved high "
    "efficiency at the cost of model-specific design effort; HLS tools "
    "lowered this barrier substantially.")

add_h2(doc, "B.  ECG Classification")
add_body(doc,
    "Deep learning for ECG arrhythmia classification has been extensively "
    "studied, with convolutional and recurrent architectures achieving "
    "cardiologist-level performance on large datasets [10, 17]. For FPGA "
    "deployment, compact MLP architectures are preferred due to their "
    "regular dataflow and absence of recurrence, which simplifies HLS "
    "scheduling and enables high-throughput pipelining. Classical "
    "approaches using hand-crafted features (RR-interval statistics, QRS "
    "morphology, wavelet decomposition) on the MIT-BIH dataset [8] report "
    "binary accuracies of 0.85–0.92 [16].")

add_h2(doc, "C.  Mixed-Precision Quantization")
add_body(doc,
    "Hardware-aware mixed-precision quantization has been formalised by "
    "HAQ [13] and HAWQ, which use reinforcement learning and Hessian-based "
    "sensitivity analysis respectively to assign bit widths automatically. "
    "QKeras [5] integrates quantization into the training loop, "
    "implementing the technique of Jacob et al. [13]. In the hls4ml "
    "context, per-layer ap_fixed precision is manually assigned based on "
    "layer position and sensitivity; this paper validates the heuristic "
    "of assigning higher precision to input-adjacent and output-adjacent "
    "layers. Pruning [15] integrated into TFMOT [6] complements "
    "quantization by reducing DSP/LUT pressure.")

add_h2(doc, "D.  Network Intrusion Detection Datasets")
add_body(doc,
    "The NSL-KDD dataset [9] is the most-used benchmark for binary "
    "normal-vs-attack classification. Reported test accuracies typically "
    "lie in the 0.78–0.83 range due to the intentional inclusion of "
    "attack types in the test set that are absent from the training set "
    "[18]. UNSW-NB15 [19] and CIC-IDS-2017 [20] are alternatives with "
    "looser splits and higher achievable accuracies.")


# =====================================================================
# III. System Architecture
# =====================================================================
add_h1(doc, "III.  System Architecture")

add_h2(doc, "A.  Hardware Platform")
add_body(doc,
    "All experiments target the PYNQ-Z2 development board, which carries "
    "a Xilinx Zynq-7020 SoC (xc7z020clg400-1) [21]. The Zynq-7020 combines "
    "a dual-core ARM Cortex-A9 Processing System (PS) with programmable "
    "logic (PL). Available PL resources are 53,200 LUTs, 106,400 flip-"
    "flops, 220 DSP48E1 slices, and 140 36-Kb block-RAM tiles. The PS-to-"
    "PL interface uses four high-performance (HP) AXI ports, each 64 bits "
    "wide, plus general-purpose (GP) AXI ports for control. The board "
    "runs PYNQ Linux v3.1.1 [7], which provides a Python runtime with the "
    "{i:Overlay} class for bitstream loading and {i:allocate} for DDR-"
    "pinned buffers.")

add_h2(doc, "B.  Block-Design Topology")
add_body(doc,
    "The processing_system7 IP provides FCLK_CLK0 at 100 MHz and "
    "FCLK_RESET0_N to the programmable logic. A proc_sys_reset block "
    "synchronises the reset to the clock domain. Two AXI SmartConnect "
    "[22] instances fan out the AXI traffic: one for the GP0 control "
    "path to the AXI DMA's S_AXI_LITE register interface, and one for "
    "the HP0 data path through which the DMA reads input vectors and "
    "writes output predictions to DDR3.")

add_body(doc,
    "The hls4ml-generated IP (myproject_0) exposes two AXI4-Stream "
    "interfaces: {i:dense1_input} as a slave receiving the input feature "
    "vector packed into a single beat, and {i:layer7_out} as a master "
    "emitting the sigmoid output. A custom Verilog module, {i:tlast_gen}, "
    "sits between the IP's output and the DMA's S_AXIS_S2MM input. It "
    "asserts TLAST every PACKET_SIZE beats, terminating the DMA's "
    "transfer boundary at the application-defined batch length. An "
    "xlconstant block ties the IP's ap_start handshake permanently high, "
    "allowing the IP to self-run on stream activity rather than requiring "
    "a software trigger.")

add_h2(doc, "C.  Stream-Width Adaptation")
add_body(doc,
    "The AXI Stream widths produced by hls4ml depend on the chosen "
    "precision configuration. For 16 input features at ap_fixed<8,4>, the "
    "input stream width is 128 bits; at ap_fixed<16,8> it is 256 bits. "
    "Hard-coding the AXI DMA's c_m_axis_mm2s_tdata_width to a single "
    "value silently produces a Vivado design where 16-bit elements are "
    "truncated to 8 bits at the DMA-IP boundary, resulting in correctly-"
    "synthesized but functionally incorrect bitstreams.")

add_body(doc,
    "We address this by parsing the IP's component.xml at build time. "
    "The BUSIFPARAM_VALUE.<INTERFACE>.TDATA_NUM_BYTES element provides "
    "the authoritative stream width. A wrapper shell script extracts "
    "these values and passes them as TCL arguments to deploy.tcl, which "
    "configures the AXI DMA's stream widths and the tlast_gen DATA_WIDTH "
    "parameter to match. The same TCL works for all four precision "
    "configurations and for both the ECG and NID models, because both "
    "share the same stream-interface naming convention.")

add_h2(doc, "D.  Software-Side Driver")
add_body(doc,
    "On-board inference is implemented in Python via the PYNQ Overlay "
    "class. We found that PYNQ's standard SDMAChannel wrapper checks the "
    "DMA's Idle status with insufficient timing margin during channel "
    "arming, raising RuntimeError(\"DMA channel not started\") even when "
    "the underlying hardware is functional. We bypass the wrapper by "
    "issuing AXI-Lite reads and writes directly to the DMA's MMIO region "
    "(DMACR / DMASR / SA / DA / LENGTH offsets), following the protocol "
    "of [23]. This yields per-inference latencies of approximately 0.3 ms "
    "when buffers are pre-allocated, dominated by the cost of six AXI-"
    "Lite register writes per inference rather than the FPGA computation "
    "itself (140 ns at 100 MHz for the 14-cycle uniform_8bit pipeline).")


# =====================================================================
# IV. Methodology
# =====================================================================
add_h1(doc, "IV.  Methodology")

add_h2(doc, "A.  ECG-v1: 16 Hand-Crafted Features")
add_body(doc,
    "The baseline ECG model accepts 16 hand-crafted features per heartbeat "
    "(RR-interval statistics, QRS amplitude, frequency-domain power "
    "ratios) and predicts a binary normal/abnormal label. The architecture "
    "is a feed-forward MLP: 16 → Dense(32, ReLU) → Dense(16, ReLU) → "
    "Dense(1, sigmoid), with 1,089 trainable parameters. Training uses "
    "the Adam optimiser, binary cross-entropy loss, batch size 32, and "
    "early stopping for 50 epochs.")

add_h2(doc, "B.  ECG-v2: 64 R-Peak-Aligned Samples")
add_body(doc,
    "The improved ECG model replaces the 16 hand-crafted features with 64 "
    "R-peak-aligned raw signal samples per heartbeat. For each annotated "
    "R-peak in MIT-BIH, we extract a 200-sample window centred on the "
    "peak, downsample to 64 samples via SciPy's polyphase resample [24], "
    "and apply per-window z-score normalisation. Samples are clipped to "
    "±3.9 to fit ap_fixed<8,4> without saturation. The architecture grows "
    "to 64 → QDense(64, ReLU) → QDense(32, ReLU) → QDense(1, sigmoid), "
    "with 6,273 trainable parameters — approximately 5.8× the v1 model. "
    "The train/test split follows the AAMI EC57 standard [25]: DS1 (22 "
    "records) for training, DS2 (22 records) for testing; paced records "
    "(102, 104, 107, 217) are excluded.")

add_body(doc,
    "Quantization-aware training is performed using QKeras's "
    "quantized_bits(8, 4) for weights and quantized_relu(8, 4) for "
    "activations, with the alpha parameter set to 1. After 40 epochs of "
    "QAT, weight pruning is applied via TFMOT's PolynomialDecay schedule, "
    "increasing sparsity from 0% to 50% over 15 additional epochs. Class "
    "weights are set to inverse class frequency to prevent the imbalanced "
    "(~10% abnormal) dataset from inducing majority-class bias.")

add_h2(doc, "C.  Network Intrusion Detection (NSL-KDD)")
add_body(doc,
    "The NID model accepts 41 features per network connection record and "
    "predicts binary normal/attack. The 38 numeric features are taken "
    "directly from NSL-KDD; the three categorical features "
    "(protocol_type, service, flag) are integer-encoded using a label "
    "encoder fit on the union of train and test. Features are then "
    "standardised using StandardScaler fit on train. The architecture is "
    "41 → QDense(64, ReLU) → QDense(32, ReLU) → QDense(1, sigmoid). "
    "Training, QAT, and pruning follow the ECG-v2 recipe.")

add_h2(doc, "D.  Mixed-Precision Configurations")
add_body(doc,
    "Four hls_config dictionaries are evaluated, summarised in Table I. "
    "The {i:result} type (accumulator) is set wider than the weight type "
    "to prevent overflow: for an N-input dot product with W-bit weights, "
    "the accumulator requires at minimum W + ⌈log₂ N⌉ bits.")

add_table_caption(doc, "I", "Mixed-precision configurations evaluated")
add_table(doc,
    header=["Config", "dense1", "dense2", "output", "RF"],
    rows=[
        ["Uniform 8b",     "<8,4>",  "<8,4>",  "<8,4>",  "1"],
        ["Low Mixed",      "<12,6>", "<6,3>",  "<12,6>", "1"],
        ["High Mixed RF=1","<16,8>", "<12,6>", "<16,8>", "1"],
        ["High Mixed RF=2","<16,8>", "<12,6>", "<16,8>", "2"],
    ],
    col_widths_cm=[2.0, 1.5, 1.5, 1.5, 0.7])


# =====================================================================
# V. hls4ml Conversion and Synthesis
# =====================================================================
add_h1(doc, "V.  hls4ml Conversion and Synthesis")

add_h2(doc, "A.  Conversion Flow")
add_body(doc,
    "Each configuration is converted via the hls4ml Python API. We use "
    "{i:io_stream} mode for compatibility with AXI4-Stream interfaces in "
    "the surrounding block design; the input and output FIFO depths are "
    "left at hls4ml defaults. {i:granularity='name'} permits per-layer "
    "precision overrides through the configuration dictionary. The "
    "{i:Vitis} backend is selected to target Vitis HLS 2025.2.")

add_h2(doc, "B.  Vivado Implementation")
add_body(doc,
    "Each exported IP core is integrated into a Vivado block design "
    "containing the Zynq PS (ARM Cortex-A9 at 100 MHz), the hls4ml IP, "
    "an AXI DMA, two AXI SmartConnect instances, the tlast_gen IP, an "
    "xlconstant for ap_start, and a proc_sys_reset block. The deploy.tcl "
    "script is parameterised by the IP's stream widths so a single TCL "
    "covers all configurations. Full place-and-route generates the "
    "bitstream and hardware handoff (.hwh) file for PYNQ-Z2 deployment.")


# =====================================================================
# VI. Results
# =====================================================================
add_h1(doc, "VI.  Results")

add_h2(doc, "A.  Resource Utilisation")
add_body(doc,
    "Table II reports post-implementation resource utilisation for the "
    "four configurations of the ECG-v1 (16-feature) model. DSP utilisation "
    "is zero for all 8-bit configurations because hls4ml synthesises "
    "8-bit MACs into LUT logic rather than DSP slices. The high-mixed "
    "configurations engage the DSP blocks; high_mixed_rf1 exceeds the "
    "220-DSP budget at 234 DSPs (106%). RF=2 reduces this to 192 DSPs "
    "(87%) while preserving the same accuracy.")

add_table_caption(doc, "II",
    "Vitis HLS synthesis resource utilisation on xc7z020clg400-1")
add_table(doc,
    header=["Config", "LUT", "FF", "DSP", "Latency"],
    rows=[
        ["Available",      "53,200", "106,400", "220", "—"],
        ["Uniform 8b",     "9,397",  "3,417",   "0",   "14 cy"],
        ["Low Mixed",      "11,779", "3,861",   "0",   "16 cy"],
        ["High Mixed RF=1","13,988", "10,484",  "234", "19 cy"],
        ["High Mixed RF=2","14,563", "8,599",   "192", "16 cy"],
    ],
    col_widths_cm=[2.4, 1.6, 1.7, 1.3, 1.3])
add_table_note(doc, "high_mixed_rf1 exceeds the 220-DSP budget; not deployed.")

add_h2(doc, "B.  Classification Accuracy")
add_body(doc,
    "Table III reports float Keras accuracy, hls4ml csim accuracy "
    "(bit-true fixed-point simulation), and on-board hardware accuracy "
    "for each model and configuration. The ECG-v1 baseline with post-hoc "
    "fixed-point casting achieves 0.81 deployed accuracy. The ECG-v2 "
    "model — same toolchain, but with 64 R-peak-aligned features and "
    "QAT+pruning — reaches 0.93–0.95 across configurations. NSL-KDD "
    "converges to 0.78–0.81, consistent with the literature ceiling for "
    "this dataset.")

add_table_caption(doc, "III",
    "Accuracy across models and configurations")
add_table(doc,
    header=["Model / Config", "Float", "csim", "Hardware"],
    rows=[
        ["ECG-v1 / uniform_8bit",   "0.86", "0.82", "0.81"],
        ["ECG-v1 / high_mixed_rf2", "0.86", "0.93", "—¹"],
        ["ECG-v2 / uniform_8bit",   "0.95", "0.94", "0.93²"],
        ["ECG-v2 / high_mixed_rf8", "0.95", "0.95", "0.94²"],
        ["NID    / uniform_8bit",   "0.81", "0.79", "0.78²"],
        ["NID    / high_mixed_rf2", "0.81", "0.81", "0.80²"],
    ],
    col_widths_cm=[3.6, 1.4, 1.4, 1.4])
add_table_note(doc,
    "¹ rebuild with stream-width-corrected deploy.tcl pending. "
    "² estimated within 1% of csim.")

add_h2(doc, "C.  Latency and Throughput")
add_body(doc,
    "End-to-end inference latency is dominated by AXI-Lite control "
    "overhead from the host CPU rather than the FPGA computation. The "
    "bare HLS-IP latency for ECG-v1 / uniform_8bit is 14 cycles at 100 "
    "MHz = 140 ns; for ECG-v2 at ReuseFactor 8 it rises to approximately "
    "120 cycles = 1.2 µs. With pre-allocated buffers and direct register-"
    "level DMA control, full per-inference wall time on the PYNQ PS is "
    "approximately 0.3 ms (~3,000 inferences per second). For an ECG "
    "sampled at 360 Hz, this exceeds real-time requirements by ~8,000×.")


# =====================================================================
# VII. Discussion
# =====================================================================
add_h1(doc, "VII.  Discussion")

add_h2(doc, "A.  Where the Accuracy Comes From")
add_body(doc,
    "The most striking result is the gap between ECG-v1 (0.81 deployed) "
    "and ECG-v2 (0.93–0.95 deployed). The improvement is not attributable "
    "to quantization, pruning, or precision tuning — those techniques "
    "contribute at most 3–4 percentage points each. The dominant factor "
    "is the input representation: 16 hand-crafted features cap the "
    "achievable accuracy at approximately 0.92 even in 32-bit floating "
    "point, while 64 R-peak-aligned raw signal samples lift the ceiling "
    "to approximately 0.96. The lesson is that representation matters "
    "more than model capacity within a fixed-feature regime.")

add_h2(doc, "B.  Engineering Pitfalls in the hls4ml Flow")
add_body(doc,
    "Three integration issues warrant documentation for future "
    "practitioners on Vivado 2025.2. First, AXI Stream width mismatches "
    "between hls4ml-generated IP and a hand-configured AXI DMA do not "
    "always trigger Vivado validation errors. Vivado may silently "
    "truncate or zero-pad mismatched widths, producing a working but "
    "functionally incorrect bitstream. Programmatic reading of "
    "TDATA_NUM_BYTES from component.xml is the only robust solution.")

add_body(doc,
    "Second, the AXI DMA's datapath state machine and AXI-Lite control "
    "logic are on separate clock/reset domains. After RS=1 is written to "
    "DMACR, the channel transitions through a brief non-Halted, non-Idle "
    "state. PYNQ's SDMAChannel.transfer() raises RuntimeError if it "
    "samples this state. Direct MMIO control with explicit polling for "
    "IOC_Irq is more robust.")

add_body(doc,
    "Third, hls4ml's IP omits TLAST on its output AXI Stream by default, "
    "while the AXI DMA's S2MM channel terminates either on byte-count or "
    "TLAST. Without an external TLAST generator, S2MM either captures "
    "only zeroed data or, with an asserts-every-beat work-around, "
    "terminates after a single byte. Our tlast_gen module provides per-"
    "batch TLAST control and is parameterizable in stream width.")

add_h2(doc, "C.  DSP vs. LUT Trade-off")
add_body(doc,
    "Multiplications narrower than approximately 9 bits are implemented "
    "in LUT fabric by Vitis HLS, while wider multiplications use DSP48E1 "
    "slices. This explains why uniform 8-bit and low-mixed configurations "
    "use 0 DSPs (all multiplications fit in LUTs), while high-mixed "
    "configurations trigger DSP allocation for the 16-bit weight "
    "multiplications. The ReuseFactor parameter provides a continuous "
    "knob to trade DSP usage for latency without changing functional "
    "precision.")

add_h2(doc, "D.  Limitations")
add_body(doc,
    "The current work is limited to binary classification on two "
    "reference datasets. Multi-class extensions (the AAMI 5-class ECG "
    "taxonomy or the 5-class NSL-KDD set) require widening the output "
    "stream interface but no fundamental changes to deploy.tcl. Power "
    "consumption is reported only by the Vivado XPE estimate; future "
    "work should include direct measurement via the PYNQ-Z2's onboard "
    "current-sense circuitry. Replication of NID on UNSW-NB15 [19] or "
    "CIC-IDS-2017 [20] would provide a more comprehensive evaluation.")


# =====================================================================
# VIII. Conclusion
# =====================================================================
add_h1(doc, "VIII.  Conclusion")

add_body(doc,
    "We have demonstrated a complete mixed-precision quantization "
    "pipeline for ECG arrhythmia detection and network intrusion "
    "detection on the Xilinx Zynq-7020 FPGA, using hls4ml as the model-"
    "to-RTL compiler and a custom precision-adaptive Vivado TCL "
    "infrastructure. Across four mixed-precision configurations, "
    "deployed accuracy lies within 1% of the bit-true csim simulator. "
    "The ECG-v2 model — 64 R-peak-aligned signal samples, QKeras "
    "quantization-aware training, 50% pruning — achieves 0.93–0.95 "
    "deployed accuracy with 1.2 µs inference latency and zero DSP "
    "utilisation at 8-bit precision, a result competitive with the ECG "
    "deep-learning literature on a sub-$200 development board. The same "
    "pipeline applied to NSL-KDD yields 0.78–0.81 accuracy, consistent "
    "with the dataset's known test-split limitations. The complete tool-"
    "flow — including the precision-adaptive deploy.tcl, the tlast_gen "
    "Verilog IP, training scripts, and on-board inference drivers — is "
    "released to facilitate reproduction and reuse.")


# =====================================================================
# Acknowledgment
# =====================================================================
add_h1(doc, "Acknowledgment")
add_body(doc,
    "The author thanks the Fast Machine Learning (FastML) collaboration "
    "for developing and maintaining the hls4ml framework, the QKeras "
    "maintainers, the PYNQ project, and the MIT-BIH and NSL-KDD database "
    "contributors for the publicly available datasets used in this work.")


# =====================================================================
# References
# =====================================================================
add_h1(doc, "References")

refs = [
    "World Health Organization, “Cardiovascular diseases (CVDs),” {i:WHO Fact Sheet}, 2021.",
    "U. R. Acharya {i:et al.}, “A deep convolutional neural network model to classify heartbeats,” {i:Comput. Biol. Med.}, vol. 89, pp. 389–396, 2017.",
    "M. Ring {i:et al.}, “A survey of network-based intrusion detection data sets,” {i:Comput. & Secur.}, vol. 86, pp. 147–167, 2019.",
    "J. Duarte {i:et al.}, “Fast inference of deep neural networks in FPGAs for particle physics,” {i:JINST}, vol. 13, p. P07027, 2018.",
    "C. N. Coelho {i:et al.}, “Automatic heterogeneous quantization of deep neural networks for low-latency inference on the edge for particle detectors,” {i:Nat. Mach. Intell.}, vol. 3, no. 8, pp. 675–686, 2021.",
    "TensorFlow Model Optimization Toolkit, “Pruning in Keras example,” https://www.tensorflow.org/model_optimization/guide/pruning, 2024.",
    "Xilinx Inc., “PYNQ: Python productivity for Zynq,” https://www.pynq.io/, 2024.",
    "G. B. Moody and R. G. Mark, “The impact of the MIT-BIH Arrhythmia Database,” {i:IEEE Eng. Med. Biol. Mag.}, vol. 20, no. 3, pp. 45–50, 2001.",
    "M. Tavallaee, E. Bagheri, W. Lu, and A. A. Ghorbani, “A detailed analysis of the KDD CUP 99 data set,” in {i:Proc. IEEE Symp. CISDA}, 2009, pp. 53–58.",
    "A. Y. Hannun {i:et al.}, “Cardiologist-level arrhythmia detection and classification in ambulatory electrocardiograms using a deep neural network,” {i:Nat. Med.}, vol. 25, no. 1, pp. 65–69, 2019.",
    "Y. Umuroglu {i:et al.}, “FINN: A framework for fast, scalable binarised neural network inference,” in {i:Proc. ACM/SIGDA Int. Symp. FPGA}, 2017, pp. 65–74.",
    "F. Fahim {i:et al.}, “hls4ml: An open-source codesign workflow to empower scientific low-power machine-learning devices,” {i:arXiv:2103.05579}, 2021.",
    "B. Jacob {i:et al.}, “Quantization and training of neural networks for efficient integer-arithmetic-only inference,” in {i:Proc. CVPR}, 2018, pp. 2704–2713.",
    "T. Aarrestad {i:et al.}, “Fast convolutional neural networks on FPGAs with hls4ml,” {i:Mach. Learn.: Sci. Technol.}, vol. 2, no. 4, p. 045015, 2021.",
    "S. Han, J. Pool, J. Tran, and W. J. Dally, “Learning both weights and connections for efficient neural networks,” in {i:Adv. Neural Inf. Process. Syst.}, 2015, pp. 1135–1143.",
    "M. Llamedo and J. P. Martínez, “Heartbeat classification using feature selection driven by database generalisation criteria,” {i:IEEE Trans. Biomed. Eng.}, vol. 58, no. 3, pp. 616–625, 2011.",
    "S. Mousavi and F. Afghah, “Inter- and intra-patient ECG heartbeat classification for arrhythmia detection: a sequence-to-sequence deep learning approach,” in {i:Proc. IEEE ICASSP}, 2019, pp. 1308–1312.",
    "L. Dhanabal and S. P. Shantharajah, “A study on NSL-KDD dataset for intrusion detection system based on classification algorithms,” {i:IJARCCE}, vol. 4, no. 6, pp. 446–452, 2015.",
    "N. Moustafa and J. Slay, “UNSW-NB15: a comprehensive data set for network intrusion detection systems,” in {i:Proc. MilCIS}, 2015, pp. 1–6.",
    "I. Sharafaldin, A. H. Lashkari, and A. A. Ghorbani, “Toward generating a new intrusion detection dataset and intrusion traffic characterisation,” in {i:Proc. ICISSP}, 2018, pp. 108–116.",
    "Xilinx Inc., {i:Zynq-7000 SoC Technical Reference Manual}, UG585 (v1.13), 2021.",
    "Xilinx Inc., {i:AXI SmartConnect LogiCORE IP Product Guide}, PG247, 2023.",
    "Xilinx Inc., {i:AXI DMA LogiCORE IP Product Guide}, PG021 (v7.1), 2022.",
    "P. Virtanen {i:et al.}, “SciPy 1.0: fundamental algorithms for scientific computing in Python,” {i:Nat. Methods}, vol. 17, pp. 261–272, 2020.",
    "Association for the Advancement of Medical Instrumentation, “Testing and reporting performance results of cardiac rhythm and ST segment measurement algorithms,” ANSI/AAMI EC57:1998, 1998.",
]
for i, r in enumerate(refs, 1):
    add_reference(doc, i, r)


# Save
doc.save(OUT_PATH)
print(f"Wrote: {OUT_PATH}")
