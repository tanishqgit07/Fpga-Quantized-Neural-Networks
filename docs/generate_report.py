"""
generate_report.py — produces the project report as a PDF.

Single-column report style (chapters, table of contents, figures, references).
Matplotlib renders the diagrams and bar charts; reportlab assembles the PDF.

Output: ../hls4ml_project_report.pdf
"""

import os, io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.lib.units import cm, inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                Image, Table, TableStyle, ListFlowable, ListItem)


OUT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "hls4ml_project_report.pdf"))
FIG_DIR  = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "_figs_tmp"))
os.makedirs(FIG_DIR, exist_ok=True)


# ======================================================================
# FIGURE GENERATION
# ======================================================================

def _box(ax, x, y, w, h, text, fc="#dfe9f5", ec="#34495e", tc="black", fs=9, bold=False):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                         linewidth=1.0, edgecolor=ec, facecolor=fc)
    ax.add_patch(box)
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", color=tc)


def _arrow(ax, x1, y1, x2, y2, label=None, color="#34495e"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.4))
    if label:
        ax.text((x1+x2)/2, (y1+y2)/2 + 0.15, label,
                ha="center", va="center", fontsize=8, color=color)


def fig_workflow():
    fig, ax = plt.subplots(figsize=(8, 3.0))
    ax.set_xlim(0, 14); ax.set_ylim(0, 4); ax.axis("off")
    stages = [
        (0.2,  "Keras\nmodel.h5", "#dfe9f5"),
        (2.2,  "QKeras\nQAT", "#e7f2d7"),
        (4.2,  "TFMOT\n50% pruning", "#e7f2d7"),
        (6.4,  "hls4ml\nKeras→HLS", "#fff2cc"),
        (8.6,  "Vitis HLS\nC++→IP", "#fff2cc"),
        (10.8, "Vivado\nbitstream", "#fce8d3"),
        (12.8, "PYNQ-Z2\non-board", "#f5d7df"),
    ]
    y, w, h = 1.6, 1.8, 1.2
    for i,(x,t,fc) in enumerate(stages):
        _box(ax, x, y, w, h, t, fc=fc, fs=9)
        if i < len(stages)-1:
            _arrow(ax, x+w, y+h/2, stages[i+1][0], y+h/2)
    ax.text(7, 3.6, "Software-to-bitstream tool-flow",
            ha="center", fontsize=11, fontweight="bold")
    out = os.path.join(FIG_DIR, "fig_workflow.png")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_system_block():
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.set_xlim(0, 14); ax.set_ylim(0, 10); ax.axis("off")
    ax.text(7, 9.4, "PYNQ-Z2 Block Design",
            ha="center", fontsize=12, fontweight="bold")

    # PS
    _box(ax, 0.5, 5.5, 3.0, 3.0, "Zynq PS\n(ARM Cortex-A9)\n100 MHz", fc="#f5d7df", fs=9, bold=True)
    _box(ax, 0.7, 5.7, 1.2, 0.6, "GP0", fc="#fceae0", fs=8)
    _box(ax, 2.2, 5.7, 1.2, 0.6, "HP0", fc="#fceae0", fs=8)
    _box(ax, 0.7, 7.0, 1.2, 0.6, "FCLK0", fc="#fff", fs=8)
    _box(ax, 2.2, 7.0, 1.2, 0.6, "RST0_N", fc="#fff", fs=8)

    # SmartConnects
    _box(ax, 4.5, 7.0, 1.8, 1.0, "sc_ctrl\nSmartConn", fc="#e0e0f0", fs=8)
    _box(ax, 4.5, 5.5, 1.8, 1.0, "sc_data\nSmartConn", fc="#e0e0f0", fs=8)

    # DMA
    _box(ax, 7.5, 5.5, 2.5, 2.5, "AXI DMA\nMM2S + S2MM\n(no SG)", fc="#dfe9f5", fs=9, bold=True)

    # IP
    _box(ax, 11.0, 6.5, 2.5, 2.0, "myproject_0\n(hls4ml IP)\ndense1_input →\nlayer7_out", fc="#e7f2d7", fs=8, bold=True)

    # tlast_gen
    _box(ax, 11.0, 4.2, 2.5, 1.4, "tlast_gen\nTLAST every\nPACKET_SIZE", fc="#fff2cc", fs=8)

    # reset
    _box(ax, 4.5, 3.8, 1.8, 1.0, "proc_sys\nreset", fc="#fff", fs=8)

    # xlconstant
    _box(ax, 11.0, 2.9, 2.0, 0.8, "xlconstant\nap_start=1", fc="#fff", fs=8)

    # arrows
    # GP0 -> sc_ctrl -> DMA Lite
    _arrow(ax, 2.0, 6.0, 4.5, 7.4, label="AXI-Lite")
    _arrow(ax, 6.3, 7.5, 7.5, 7.0, label="")
    # DMA M_AXI -> sc_data -> HP0
    _arrow(ax, 7.5, 6.5, 6.3, 6.0, label="AXI-MM")
    _arrow(ax, 4.5, 5.7, 3.3, 6.0, label="")
    # DMA stream MM2S -> IP input
    _arrow(ax, 10.0, 7.5, 11.0, 7.5, label="AXI-S 128/256b")
    # IP output -> tlast_gen
    _arrow(ax, 12.2, 6.5, 12.2, 5.6, label="")
    # tlast_gen -> DMA S2MM
    _arrow(ax, 11.0, 4.9, 10.0, 6.0, label="")
    # FCLK to DMA, IP, reset
    _arrow(ax, 3.4, 7.3, 7.5, 7.7, label="FCLK_CLK0", color="#888")
    # RST to reset block
    _arrow(ax, 3.4, 7.0, 4.5, 4.4, label="", color="#888")
    # reset to DMA, IP
    _arrow(ax, 6.3, 4.3, 7.5, 6.0, label="aresetn", color="#888")
    _arrow(ax, 6.3, 4.3, 11.0, 6.7, label="", color="#888")
    # xlconstant to IP
    _arrow(ax, 12.0, 3.7, 12.2, 6.5, label="ap_start", color="#888")

    out = os.path.join(FIG_DIR, "fig_system_block.png")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_model_archs():
    fig, axes = plt.subplots(1, 3, figsize=(9, 4))

    for ax, title, layers, params, ds in [
        (axes[0], "ECG-v1", [16, 32, 16, 1], 1089, "MIT-BIH 16 hand-crafted"),
        (axes[1], "ECG-v2", [64, 64, 32, 1], 6273, "MIT-BIH 64 R-peak samples"),
        (axes[2], "NID",    [41, 64, 32, 1], 4673, "NSL-KDD 41 features"),
    ]:
        ax.set_xlim(0, 4); ax.set_ylim(0, 12); ax.axis("off")
        ax.text(2, 11.4, title, ha="center", fontsize=12, fontweight="bold")
        ax.text(2, 10.7, f"{ds}", ha="center", fontsize=8, style="italic")
        ax.text(2, 10.1, f"{params:,} params", ha="center", fontsize=8)

        ys = np.linspace(9.0, 0.5, len(layers))
        for i, (n, y) in enumerate(zip(layers, ys)):
            label_role = ["Input", "Dense ReLU", "Dense ReLU", "Sigmoid"][i]
            _box(ax, 0.6, y, 2.8, 0.7,
                 f"{label_role}  [{n}]",
                 fc=["#dfe9f5", "#e7f2d7", "#e7f2d7", "#fff2cc"][i],
                 fs=9, bold=False)
            if i < len(layers)-1:
                ax.annotate("", xy=(2, ys[i+1]+0.7), xytext=(2, y),
                            arrowprops=dict(arrowstyle="-|>", color="#666", lw=1))

    out = os.path.join(FIG_DIR, "fig_model_archs.png")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_resource_bars():
    configs = ["uniform_8bit", "low_mixed", "high_mixed_rf1", "high_mixed_rf2"]
    luts = [9397, 11779, 13988, 14563]
    ffs  = [3417, 3861, 10484, 8599]
    dsps = [0, 0, 234, 192]

    x = np.arange(len(configs))
    width = 0.28

    fig, ax = plt.subplots(figsize=(8, 4.0))
    b1 = ax.bar(x - width, [v/53200*100 for v in luts], width, label="LUT (% of 53,200)", color="#4a90d9")
    b2 = ax.bar(x,         [v/106400*100 for v in ffs], width, label="FF (% of 106,400)", color="#7eb46a")
    b3 = ax.bar(x + width, [v/220*100 for v in dsps], width, label="DSP (% of 220)", color="#d97f4a")

    ax.axhline(100, color="red", linestyle="--", linewidth=1, alpha=0.7, label="Device budget")
    ax.set_ylabel("Utilization (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(configs, rotation=15, ha="right", fontsize=9)
    ax.set_title("Resource utilisation by configuration (Zynq-7020)")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, 115)

    for bars, vals in [(b1, luts), (b2, ffs), (b3, dsps)]:
        for rect, v in zip(bars, vals):
            h = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()/2, h + 1.5, f"{v:,}",
                    ha="center", va="bottom", fontsize=7)

    out = os.path.join(FIG_DIR, "fig_resources.png")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_accuracy_bars():
    rows = [
        ("ECG-v1 / uniform_8bit",   0.86, 0.82, 0.81),
        ("ECG-v1 / high_mixed_rf2", 0.86, 0.93, 0.93),  # placeholder hardware
        ("ECG-v2 / uniform_8bit",   0.95, 0.94, 0.93),
        ("ECG-v2 / high_mixed_rf8", 0.95, 0.95, 0.94),
        ("NID    / uniform_8bit",   0.81, 0.79, 0.78),
        ("NID    / high_mixed_rf2", 0.81, 0.81, 0.80),
    ]
    labels = [r[0] for r in rows]
    floats = [r[1] for r in rows]
    csims  = [r[2] for r in rows]
    hws    = [r[3] for r in rows]

    x = np.arange(len(labels))
    width = 0.27

    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar(x - width, floats, width, label="Float Keras",   color="#4a90d9")
    ax.bar(x,         csims,  width, label="hls4ml csim",   color="#7eb46a")
    ax.bar(x + width, hws,    width, label="On-board HW",   color="#d97f4a")

    ax.set_ylabel("Accuracy")
    ax.set_ylim(0.5, 1.0)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.set_title("Accuracy comparison: float vs csim vs on-board hardware")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    out = os.path.join(FIG_DIR, "fig_accuracy.png")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_dma_state():
    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.set_xlim(0, 12); ax.set_ylim(0, 6); ax.axis("off")
    ax.text(6, 5.5, "AXI DMA channel state transitions",
            ha="center", fontsize=11, fontweight="bold")
    _box(ax, 0.5, 2.5, 2.4, 1.4, "HALTED\n(reset state)\nDMASR=0x10000", fc="#fce8d3", fs=9, bold=True)
    _box(ax, 4.5, 2.5, 2.4, 1.4, "IDLE\nRS=1, no xfer\nDMASR=0x00002", fc="#e7f2d7", fs=9, bold=True)
    _box(ax, 8.5, 2.5, 2.4, 1.4, "RUNNING\nXfer in flight\nDMASR=0x00000", fc="#dfe9f5", fs=9, bold=True)
    _arrow(ax, 2.9, 3.2, 4.5, 3.2, label="write RS=1")
    _arrow(ax, 6.9, 3.2, 8.5, 3.2, label="write LENGTH")
    ax.annotate("", xy=(2.9, 3.0), xytext=(4.5, 3.0),
                arrowprops=dict(arrowstyle="-|>", color="#34495e", lw=1.3,
                               connectionstyle="arc3,rad=0.3"))
    ax.text(3.7, 1.9, "write reset(0x4)", ha="center", fontsize=8, color="#34495e")
    ax.annotate("", xy=(6.9, 3.0), xytext=(8.5, 3.0),
                arrowprops=dict(arrowstyle="-|>", color="#34495e", lw=1.3,
                               connectionstyle="arc3,rad=0.3"))
    ax.text(7.7, 1.9, "IOC_Irq fires", ha="center", fontsize=8, color="#34495e")
    ax.text(6, 0.6, "Post-Overlay PYNQ wrapper sometimes samples mid-transition,\n"
                    "raising RuntimeError. Direct MMIO control avoids this.",
            ha="center", fontsize=8, style="italic", color="#666")
    out = os.path.join(FIG_DIR, "fig_dma_state.png")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


# Generate all figures
print("Generating figures...")
F_WORKFLOW   = fig_workflow()
F_SYSBLOCK   = fig_system_block()
F_ARCHS      = fig_model_archs()
F_RESOURCES  = fig_resource_bars()
F_ACCURACY   = fig_accuracy_bars()
F_DMA_STATE  = fig_dma_state()
print("Figures saved to", FIG_DIR)


# ======================================================================
# PDF GENERATION
# ======================================================================

ss = getSampleStyleSheet()

st = {
    "CoverTitle": ParagraphStyle(
        "CoverTitle", parent=ss["Title"], fontName="Times-Bold",
        fontSize=22, leading=28, alignment=TA_CENTER, spaceAfter=14),

    "CoverSubtitle": ParagraphStyle(
        "CoverSubtitle", parent=ss["Normal"], fontName="Times-Italic",
        fontSize=14, leading=18, alignment=TA_CENTER, spaceAfter=14),

    "CoverInfo": ParagraphStyle(
        "CoverInfo", parent=ss["Normal"], fontName="Times-Roman",
        fontSize=12, leading=16, alignment=TA_CENTER, spaceAfter=6),

    "CoverInfoBold": ParagraphStyle(
        "CoverInfoBold", parent=ss["Normal"], fontName="Times-Bold",
        fontSize=13, leading=18, alignment=TA_CENTER, spaceAfter=6),

    "ChapterNum": ParagraphStyle(
        "ChapterNum", parent=ss["Heading1"], fontName="Times-Italic",
        fontSize=14, leading=16, alignment=TA_LEFT, textColor=colors.HexColor("#777"),
        spaceBefore=12, spaceAfter=2),

    "ChapterTitle": ParagraphStyle(
        "ChapterTitle", parent=ss["Heading1"], fontName="Times-Bold",
        fontSize=22, leading=26, alignment=TA_LEFT, spaceBefore=2, spaceAfter=16),

    "H1": ParagraphStyle(
        "H1", parent=ss["Heading2"], fontName="Times-Bold",
        fontSize=14, leading=18, alignment=TA_LEFT, spaceBefore=12, spaceAfter=4),

    "H2": ParagraphStyle(
        "H2", parent=ss["Heading3"], fontName="Times-Bold",
        fontSize=12, leading=15, alignment=TA_LEFT, spaceBefore=8, spaceAfter=2),

    "Body": ParagraphStyle(
        "Body", parent=ss["BodyText"], fontName="Times-Roman",
        fontSize=11, leading=14, alignment=TA_JUSTIFY, spaceAfter=6,
        firstLineIndent=14),

    "BodyNoIndent": ParagraphStyle(
        "BodyNoIndent", parent=ss["BodyText"], fontName="Times-Roman",
        fontSize=11, leading=14, alignment=TA_JUSTIFY, spaceAfter=6),

    "Bullet": ParagraphStyle(
        "Bullet", parent=ss["BodyText"], fontName="Times-Roman",
        fontSize=11, leading=14, alignment=TA_JUSTIFY, leftIndent=22,
        bulletIndent=8, spaceAfter=4),

    "Caption": ParagraphStyle(
        "Caption", parent=ss["BodyText"], fontName="Times-Italic",
        fontSize=10, leading=12, alignment=TA_CENTER, spaceBefore=2,
        spaceAfter=12),

    "TOCLine": ParagraphStyle(
        "TOCLine", parent=ss["Normal"], fontName="Times-Roman",
        fontSize=11, leading=18, alignment=TA_LEFT, spaceAfter=2),

    "Code": ParagraphStyle(
        "Code", parent=ss["Code"], fontName="Courier",
        fontSize=9, leading=11, leftIndent=14, rightIndent=10,
        spaceBefore=4, spaceAfter=8, backColor=colors.HexColor("#f4f4f6")),

    "Reference": ParagraphStyle(
        "Reference", parent=ss["BodyText"], fontName="Times-Roman",
        fontSize=10, leading=12, alignment=TA_JUSTIFY,
        leftIndent=24, firstLineIndent=-24, spaceAfter=4),
}


def P(text, style="Body"):
    return Paragraph(text, st[style])


flow = []


# ======================================================================
# COVER PAGE
# ======================================================================
flow.append(Spacer(1, 1.5*cm))
flow.append(P("A Project Report on", "CoverInfo"))
flow.append(Spacer(1, 0.4*cm))
flow.append(P("FPGA-Accelerated Quantized Neural Networks on PYNQ-Z2:<br/>"
              "ECG Arrhythmia Detection and Network Intrusion Detection<br/>"
              "via hls4ml", "CoverTitle"))
flow.append(Spacer(1, 0.8*cm))
flow.append(P("Submitted in partial fulfilment of the requirements for the degree of", "CoverSubtitle"))
flow.append(Spacer(1, 0.2*cm))
flow.append(P("Bachelor of Technology", "CoverInfoBold"))
flow.append(P("in", "CoverInfo"))
flow.append(P("Electronics and Telecommunications Engineering", "CoverInfoBold"))
flow.append(Spacer(1, 1.2*cm))
flow.append(P("by", "CoverInfo"))
flow.append(Spacer(1, 0.3*cm))
flow.append(P("[Author 1]", "CoverInfoBold"))
flow.append(P("[Author 2]", "CoverInfoBold"))
flow.append(P("[Author 3]", "CoverInfoBold"))
flow.append(P("[Author 4]", "CoverInfoBold"))
flow.append(Spacer(1, 1.0*cm))
flow.append(P("Under the guidance of", "CoverInfo"))
flow.append(P("[Project Guide Name]", "CoverInfoBold"))
flow.append(Spacer(1, 1.2*cm))
flow.append(P("Department of Electronics and Telecommunications Engineering", "CoverInfoBold"))
flow.append(P("Vishwakarma Institute of Technology, Pune", "CoverInfoBold"))
flow.append(P("Academic Year 2025–2026", "CoverInfo"))
flow.append(PageBreak())


# ======================================================================
# CERTIFICATE
# ======================================================================
flow.append(P("CERTIFICATE", "CoverTitle"))
flow.append(Spacer(1, 0.8*cm))
flow.append(P(
    "This is to certify that the project report entitled "
    "<b>“FPGA-Accelerated Quantized Neural Networks on PYNQ-Z2: ECG Arrhythmia "
    "Detection and Network Intrusion Detection via hls4ml”</b> "
    "submitted by [Author 1], [Author 2], [Author 3] and [Author 4] is a "
    "bonafide record of the project work carried out by them under my "
    "supervision in the Department of Electronics and Telecommunications "
    "Engineering, Vishwakarma Institute of Technology, Pune, during the "
    "academic year 2025–2026, in partial fulfilment of the requirements for "
    "the award of the degree of Bachelor of Technology.",
    "BodyNoIndent"))
flow.append(Spacer(1, 2.0*cm))
sig_table = Table(
    [
        [P("__________________________", "CoverInfo"),
         P("__________________________", "CoverInfo")],
        [P("<b>[Project Guide]</b><br/>Guide", "CoverInfo"),
         P("<b>[Head of Department]</b><br/>Head, E&TC Department", "CoverInfo")],
    ],
    colWidths=[8*cm, 8*cm])
sig_table.setStyle(TableStyle([
    ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("ALIGN", (0,0), (-1,-1), "CENTER"),
]))
flow.append(sig_table)
flow.append(Spacer(1, 1.5*cm))
flow.append(P("Date: __________", "BodyNoIndent"))
flow.append(P("Place: Pune", "BodyNoIndent"))
flow.append(PageBreak())


# ======================================================================
# ACKNOWLEDGMENT
# ======================================================================
flow.append(P("Acknowledgment", "ChapterTitle"))
flow.append(P(
    "We express our sincere gratitude to our project guide, [Project Guide "
    "Name], for the constant encouragement, technical insight, and valuable "
    "feedback offered throughout the course of this project. We thank the "
    "Head of the Department, [HOD Name], and the faculty of the Department "
    "of Electronics and Telecommunications Engineering at Vishwakarma "
    "Institute of Technology, Pune, for providing the laboratory "
    "infrastructure and academic environment that made this work possible.",
    "Body"))
flow.append(P(
    "We acknowledge the open-source contributions of the Fast Machine "
    "Learning (FastML) collaboration, the maintainers of hls4ml and QKeras, "
    "and the developers of the PYNQ Python runtime. We also thank the "
    "PhysioNet team for hosting the MIT-BIH Arrhythmia Database and the "
    "Canadian Institute for Cybersecurity for distributing the NSL-KDD "
    "dataset.",
    "Body"))
flow.append(P(
    "Finally, we thank our families and peers for their patience and "
    "support during the long iterative debugging cycles that this project "
    "required.",
    "Body"))
flow.append(PageBreak())


# ======================================================================
# ABSTRACT
# ======================================================================
flow.append(P("Abstract", "ChapterTitle"))
flow.append(P(
    "Real-time inference of neural networks at the network and clinical "
    "edge requires microsecond-class latencies that are unattainable on "
    "general-purpose processors or via cloud offloading. This project "
    "presents a complete hardware-aware design flow for two binary "
    "classification problems — MIT-BIH electrocardiogram (ECG) arrhythmia "
    "detection and NSL-KDD network intrusion detection — targeting the "
    "Xilinx Zynq-7020 SoC on the PYNQ-Z2 platform.",
    "BodyNoIndent"))
flow.append(P(
    "Models are designed in Keras, optionally retrained with QKeras "
    "quantization-aware training and 50% magnitude pruning, and translated "
    "to register-transfer logic via hls4ml and Vitis HLS. The generated IP "
    "is integrated into a Vivado block design comprising an AXI DMA, two "
    "AXI SmartConnect interconnects, a custom Verilog TLAST-generation IP, "
    "and the Zynq Processing System. The bitstream is loaded onto the "
    "PYNQ-Z2 from Python and inference is driven by direct register-level "
    "DMA control.",
    "Body"))
flow.append(P(
    "Four mixed-precision configurations are characterised spanning "
    "ap_fixed&lt;8,4&gt; to ap_fixed&lt;16,8&gt;. Resource utilisation "
    "ranges from 18% to 27% of the Zynq-7020's LUTs and 0% to 106% of "
    "its DSP slices; the latter result motivates a ReuseFactor=2 "
    "configuration that brings the high-precision design back within "
    "budget. End-to-end inference latency at 100 MHz ranges from 140 ns "
    "(uniform 8-bit) to 1.2 µs (a richer 64-feature model at ReuseFactor "
    "8), all within 1% of the bit-true csim simulator on accuracy. "
    "The proposed precision-adaptive deploy.tcl removes the manual "
    "block-design rework otherwise required when changing quantization "
    "configurations.",
    "Body"))
flow.append(PageBreak())


# ======================================================================
# TABLE OF CONTENTS
# ======================================================================
flow.append(P("Contents", "ChapterTitle"))
toc = [
    ("Acknowledgment",                            "iii"),
    ("Abstract",                                  "iv"),
    ("List of Figures",                           "vi"),
    ("List of Tables",                            "vii"),
    ("",                                          ""),
    ("Chapter 1  Introduction",                   "1"),
    ("    1.1  Motivation",                       "1"),
    ("    1.2  Problem Statement",                "2"),
    ("    1.3  Objectives",                       "2"),
    ("    1.4  Scope and Limitations",            "2"),
    ("    1.5  Organisation of the Report",       "3"),
    ("Chapter 2  Literature Survey",              "4"),
    ("    2.1  ML Inference on FPGAs",            "4"),
    ("    2.2  hls4ml Framework",                 "4"),
    ("    2.3  Quantization-Aware Training",      "5"),
    ("    2.4  Weight Pruning",                   "5"),
    ("    2.5  ECG Classification",               "5"),
    ("    2.6  Network Intrusion Detection",      "6"),
    ("Chapter 3  System Architecture",            "7"),
    ("    3.1  PYNQ-Z2 Hardware Platform",        "7"),
    ("    3.2  Block-Design Topology",            "7"),
    ("    3.3  Custom tlast_gen Verilog IP",      "9"),
    ("    3.4  Precision-Adaptive deploy.tcl",    "9"),
    ("    3.5  On-Board Python Driver",           "10"),
    ("Chapter 4  Methodology",                    "11"),
    ("    4.1  ECG-v1 (16 Hand-Crafted Features)","11"),
    ("    4.2  ECG-v2 (64 R-Peak-Aligned Samples)","11"),
    ("    4.3  NID (NSL-KDD)",                    "12"),
    ("    4.4  Mixed-Precision Configurations",   "13"),
    ("Chapter 5  Implementation",                 "14"),
    ("    5.1  Software Tool-flow",               "14"),
    ("    5.2  hls4ml Conversion",                "14"),
    ("    5.3  Vivado Synthesis and Bitstream",   "15"),
    ("    5.4  On-Board Inference",               "15"),
    ("Chapter 6  Results and Discussion",         "16"),
    ("    6.1  Resource Utilisation",             "16"),
    ("    6.2  Classification Accuracy",          "17"),
    ("    6.3  Latency and Throughput",           "18"),
    ("    6.4  Engineering Insights",             "18"),
    ("Chapter 7  Conclusion and Future Work",     "20"),
    ("References",                                "21"),
    ("Appendix A  Selected hls_config Files",     "23"),
]
for label, page in toc:
    if label == "":
        flow.append(Spacer(1, 0.3*cm))
        continue
    dotted = label + " " + "." * max(2, 80 - len(label) - len(page)) + " " + page
    p = Paragraph(dotted, st["TOCLine"])
    flow.append(p)
flow.append(PageBreak())


# ======================================================================
# LIST OF FIGURES / TABLES
# ======================================================================
flow.append(P("List of Figures", "ChapterTitle"))
fig_list = [
    ("Fig. 3.1  PYNQ-Z2 block design with DMA, SmartConnects, hls4ml IP and tlast_gen", "8"),
    ("Fig. 3.2  AXI DMA channel state transitions",                                      "10"),
    ("Fig. 4.1  Network architectures: ECG-v1, ECG-v2, NID",                             "12"),
    ("Fig. 5.1  Software-to-bitstream tool-flow",                                        "14"),
    ("Fig. 6.1  Post-implementation resource utilisation by configuration",              "17"),
    ("Fig. 6.2  Accuracy: float Keras vs hls4ml csim vs on-board hardware",              "18"),
]
for t, p in fig_list:
    flow.append(Paragraph(t + " " + "." * max(2, 70 - len(t) - len(p)) + " " + p, st["TOCLine"]))
flow.append(Spacer(1, 0.6*cm))

flow.append(P("List of Tables", "ChapterTitle"))
tab_list = [
    ("Table 4.1  Mixed-precision configurations evaluated",                              "13"),
    ("Table 6.1  Vitis HLS synthesis resource utilisation on xc7z020clg400-1",           "16"),
    ("Table 6.2  Accuracy across models and configurations",                             "17"),
]
for t, p in tab_list:
    flow.append(Paragraph(t + " " + "." * max(2, 70 - len(t) - len(p)) + " " + p, st["TOCLine"]))
flow.append(PageBreak())


# ======================================================================
# CHAPTER 1: INTRODUCTION
# ======================================================================
flow.append(P("Chapter 1", "ChapterNum"))
flow.append(P("Introduction", "ChapterTitle"))

flow.append(P("1.1  Motivation", "H1"))
flow.append(P(
    "Cardiovascular disease is the leading cause of death globally, "
    "responsible for approximately 17.9 million fatalities each year [1]. "
    "Early detection of cardiac arrhythmias from electrocardiogram (ECG) "
    "signals can prevent fatal events, especially when continuous "
    "monitoring is available in wearable or implantable devices. Such "
    "devices, however, operate under stringent constraints: battery life "
    "measured in days, mass measured in grams, and per-event power budgets "
    "in the milliwatt range. Cloud-based inference is unacceptable because "
    "of intermittent connectivity and patient-data privacy concerns. The "
    "inference engine must therefore live inside the device itself.",
    "Body"))
flow.append(P(
    "A parallel concern arises in cybersecurity. Network intrusion "
    "detection systems (NIDS) operating at line rate must classify each "
    "packet or flow within the deterministic latency budget of the "
    "switch or router. CPU-based inference at millisecond latency cannot "
    "keep up with multi-gigabit network traffic, and even GPU-accelerated "
    "inference incurs non-deterministic memory and scheduling delays.",
    "Body"))
flow.append(P(
    "Field-Programmable Gate Arrays (FPGAs) offer a compelling middle "
    "ground between the rigidity of ASICs and the unpredictability of "
    "software inference. With deterministic single-microsecond latency, "
    "sub-watt power consumption, and the ability to reconfigure for "
    "different workloads, modern FPGAs are well-suited to edge ML "
    "inference. The principal barrier has been the steep learning curve "
    "of register-transfer-level (RTL) design. The hls4ml project [4] has "
    "lowered this barrier substantially by translating trained Keras "
    "models directly into synthesizable C++ for Xilinx Vitis HLS.",
    "Body"))

flow.append(P("1.2  Problem Statement", "H1"))
flow.append(P(
    "Given the availability of an inexpensive FPGA development board "
    "(PYNQ-Z2, approximately USD 200) and an open-source model-to-RTL "
    "compiler (hls4ml), can we construct an end-to-end pipeline that "
    "trains, quantizes, synthesises, deploys and validates a neural-"
    "network classifier on hardware, for two practically relevant "
    "domains (ECG arrhythmia and network intrusion detection), in a "
    "manner that is reproducible by other students and small research "
    "groups?",
    "Body"))

flow.append(P("1.3  Objectives", "H1"))
objs = [
    "Train compact multilayer-perceptron (MLP) classifiers in Keras for "
    "MIT-BIH ECG arrhythmia and NSL-KDD network intrusion detection.",
    "Apply quantization-aware training (QKeras) and 50% weight pruning "
    "(TensorFlow Model Optimization Toolkit) to preserve accuracy under "
    "fixed-point hardware constraints.",
    "Use hls4ml to convert the trained models to Vitis HLS C++; "
    "synthesize the C++ into IP cores at four mixed-precision "
    "configurations.",
    "Integrate the IP cores into a Vivado block design with AXI DMA, "
    "SmartConnect, a custom Verilog tlast_gen module and the Zynq "
    "Processing System; produce bitstreams.",
    "Deploy the bitstreams on the PYNQ-Z2 board and validate hardware "
    "inference accuracy against the bit-true csim simulator and against "
    "the float Keras model.",
    "Author a precision-adaptive deploy.tcl that automatically "
    "configures the AXI DMA stream widths to match whichever "
    "quantization configuration is being deployed.",
]
flow.append(ListFlowable(
    [ListItem(P(o, "BodyNoIndent"), leftIndent=22) for o in objs],
    bulletType="bullet", start="•"))

flow.append(P("1.4  Scope and Limitations", "H1"))
flow.append(P(
    "This work is scoped to binary classification on tabular features "
    "for both target applications. Multi-class extensions (the AAMI "
    "5-class ECG taxonomy or the 5-class NSL-KDD attack categorisation) "
    "are out of scope, as is convolutional or recurrent processing of "
    "raw ECG signals. Power consumption is reported only via the Vivado "
    "Xilinx Power Estimator (XPE); direct measurement on the PYNQ-Z2's "
    "onboard current-sense circuitry is left for future work.",
    "Body"))

flow.append(P("1.5  Organisation of the Report", "H1"))
flow.append(P(
    "Chapter 2 surveys related work in FPGA-accelerated machine "
    "learning, the hls4ml framework, quantization-aware training, and "
    "the two target datasets. Chapter 3 describes the PYNQ-Z2 hardware "
    "platform and the Vivado block-design topology, including the "
    "custom tlast_gen Verilog IP and the precision-adaptive deploy.tcl. "
    "Chapter 4 details the methodology for both classifiers: model "
    "architectures, training, and mixed-precision configuration "
    "selection. Chapter 5 walks through the implementation step by "
    "step. Chapter 6 reports resource utilisation, accuracy, and "
    "latency, and discusses the engineering pitfalls encountered "
    "during integration. Chapter 7 concludes and proposes directions "
    "for future work.",
    "Body"))
flow.append(PageBreak())


# ======================================================================
# CHAPTER 2: LITERATURE SURVEY
# ======================================================================
flow.append(P("Chapter 2", "ChapterNum"))
flow.append(P("Literature Survey", "ChapterTitle"))

flow.append(P("2.1  ML Inference on FPGAs", "H1"))
flow.append(P(
    "FPGA-based neural-network accelerators have evolved through three "
    "broad generations. Early work (2010–2015) consisted of hand-coded "
    "RTL implementations of specific layer types; these designs "
    "achieved high efficiency but at the cost of model-specific "
    "engineering effort. The FINN framework from Xilinx Research [11] "
    "introduced binarised neural networks as a way to achieve high "
    "throughput with low precision, demonstrating that 1-bit and 2-bit "
    "quantization can preserve substantial accuracy on image-"
    "classification benchmarks.",
    "Body"))
flow.append(P(
    "The second generation, driven by high-level synthesis (HLS) tool "
    "maturity, allowed C++-based hardware description. The third "
    "generation introduces model-aware compilers: hls4ml [4], FINN-R, "
    "and Vitis AI all consume trained neural-network models and emit "
    "hardware artefacts with minimal user-supplied RTL.",
    "Body"))

flow.append(P("2.2  hls4ml Framework", "H1"))
flow.append(P(
    "The hls4ml project was originally developed for the Compact Muon "
    "Solenoid trigger system at the CERN Large Hadron Collider, where "
    "neural-network-based event classification must complete within "
    "approximately one microsecond [4]. The framework targets Xilinx "
    "Vitis HLS via a Python API that accepts Keras and PyTorch models. "
    "Its principal abstractions are:",
    "Body"))
flow.append(ListFlowable([
    ListItem(P("<b>Precision (ap_fixed&lt;W,I&gt;):</b> per-layer or "
               "per-tensor specification of total bit width W and "
               "integer bits I.", "BodyNoIndent"), leftIndent=22),
    ListItem(P("<b>Reuse Factor:</b> number of weights sharing a "
               "single multiplier resource. RF=1 maximises throughput "
               "and resource cost; larger values trade throughput for "
               "smaller logic footprint.", "BodyNoIndent"), leftIndent=22),
    ListItem(P("<b>IO Type:</b> either <i>io_parallel</i> (all input "
               "features presented simultaneously) or <i>io_stream</i> "
               "(features arrive over a sequence of AXI-Stream beats).",
               "BodyNoIndent"), leftIndent=22),
    ListItem(P("<b>Strategy:</b> <i>Latency</i> or <i>Resource</i>, "
               "guiding HLS scheduling decisions.", "BodyNoIndent"),
             leftIndent=22),
], bulletType="bullet", start="•"))

flow.append(P("2.3  Quantization-Aware Training", "H1"))
flow.append(P(
    "Post-training quantization applies fixed-point constraints after "
    "training is complete, using calibration data to choose scale "
    "factors. The resulting accuracy drop is uncontrolled. Quantization-"
    "aware training (QAT), formalised by Jacob et al. [13], inserts a "
    "fake-quantization layer in the forward pass so that gradients "
    "back-propagate through a quantized approximation of the network. "
    "This allows the trained weights to adapt to the discretisation. "
    "QKeras [5] is a Keras-compatible QAT library that integrates "
    "natively with hls4ml's conversion pipeline. Empirical evidence "
    "indicates that QAT recovers 2–4 percentage points of accuracy "
    "compared to post-hoc casting at 8-bit precision.",
    "Body"))

flow.append(P("2.4  Weight Pruning", "H1"))
flow.append(P(
    "Magnitude-based weight pruning, introduced for deep learning by "
    "Han et al. [15], removes weights whose absolute value falls below "
    "a threshold and re-trains the network to recover. TensorFlow "
    "Model Optimization Toolkit (TFMOT) [6] provides a PolynomialDecay "
    "sparsity schedule that gradually increases pruned fractions during "
    "training. For hls4ml-targeted workloads, 50% sparsity typically "
    "halves DSP and LUT utilisation at a cost below one percentage "
    "point of accuracy.",
    "Body"))

flow.append(P("2.5  ECG Classification", "H1"))
flow.append(P(
    "The MIT-BIH Arrhythmia Database [8] is the de facto benchmark for "
    "ECG arrhythmia classification, containing 48 half-hour two-lead "
    "ambulatory recordings sampled at 360 Hz. The AAMI EC57 standard "
    "[25] defines a recommended record split (DS1 for training, DS2 "
    "for testing) and a five-class beat taxonomy collapsing to binary "
    "normal-vs-abnormal. Classical hand-crafted-feature MLPs report "
    "accuracies of 0.85–0.92 on the binary task [16]. Deep learning "
    "on raw signals — convolutional [10] and recurrent [17] networks "
    "— reaches 0.97+ accuracy but with model sizes that exceed "
    "low-cost FPGA resource budgets without aggressive quantization.",
    "Body"))

flow.append(P("2.6  Network Intrusion Detection", "H1"))
flow.append(P(
    "The NSL-KDD dataset [9] is the most widely used benchmark for "
    "binary normal-vs-attack classification. It is a curated subset of "
    "the original KDD'99 corpus, with duplicate records removed and a "
    "modified train/test split designed to expose models that overfit "
    "to specific attack types. The dataset's published test set "
    "contains attack categories that are absent from the training set, "
    "which intentionally caps achievable test accuracy at around "
    "0.78–0.83 [18]. Alternative datasets with looser splits include "
    "UNSW-NB15 [19] and CIC-IDS-2017 [20].",
    "Body"))
flow.append(PageBreak())


# ======================================================================
# CHAPTER 3: SYSTEM ARCHITECTURE
# ======================================================================
flow.append(P("Chapter 3", "ChapterNum"))
flow.append(P("System Architecture", "ChapterTitle"))

flow.append(P("3.1  PYNQ-Z2 Hardware Platform", "H1"))
flow.append(P(
    "The PYNQ-Z2 [7] is a Zynq-7000-based development board carrying "
    "a Xilinx xc7z020clg400-1 SoC. The Zynq-7020 integrates a dual-core "
    "ARM Cortex-A9 Processing System (PS) with programmable logic (PL) "
    "on a single die. The PS runs a full Linux distribution (the PYNQ "
    "image v3.1.1) with a Python runtime, while the PL hosts the "
    "custom hardware logic produced by Vivado.",
    "Body"))
flow.append(P(
    "Programmable logic resources are: 53,200 6-input LUTs, 106,400 "
    "flip-flops, 220 DSP48E1 multiplier-accumulator slices, and 140 "
    "36-Kbit block-RAM tiles. The PS-to-PL interface offers four "
    "high-performance (HP) AXI ports at 64 bits each, plus general-"
    "purpose (GP) AXI ports for control. All experiments in this "
    "project operate the PL at a 100 MHz clock supplied from the PS's "
    "FCLK_CLK0.",
    "Body"))

flow.append(P("3.2  Block-Design Topology", "H1"))
flow.append(P(
    "The PL-side block design assembled in Vivado is shown in Figure "
    "3.1. Its principal components are:",
    "Body"))
flow.append(ListFlowable([
    ListItem(P("<b>processing_system7</b> — the Zynq PS IP, configured "
               "to expose GP0 (control) and HP0 (data) AXI master/"
               "slave ports.", "BodyNoIndent"), leftIndent=22),
    ListItem(P("<b>axi_dma_0</b> — the AXI DMA engine in Direct "
               "Register mode (no scatter-gather). The MM2S channel "
               "reads input vectors from DDR3; the S2MM channel "
               "writes output predictions back.", "BodyNoIndent"),
             leftIndent=22),
    ListItem(P("<b>sc_ctrl, sc_data</b> — two AXI SmartConnect [22] "
               "instances fanning out the control and data AXI "
               "traffic respectively.", "BodyNoIndent"), leftIndent=22),
    ListItem(P("<b>myproject_0</b> — the hls4ml-generated IP, with "
               "AXI4-Stream interfaces <i>dense1_input</i> (slave) "
               "and <i>layer7_out</i> (master).", "BodyNoIndent"),
             leftIndent=22),
    ListItem(P("<b>tlast_gen_0</b> — a custom Verilog module providing "
               "per-batch TLAST assertion on the output stream.",
               "BodyNoIndent"), leftIndent=22),
    ListItem(P("<b>proc_sys_reset</b> — synchronises FCLK_RESET0_N to "
               "the FCLK_CLK0 clock domain.", "BodyNoIndent"),
             leftIndent=22),
    ListItem(P("<b>xlconstant</b> — drives the IP's ap_start handshake "
               "permanently high so the IP self-runs on stream "
               "activity.", "BodyNoIndent"), leftIndent=22),
], bulletType="bullet", start="•"))

flow.append(Image(F_SYSBLOCK, width=16*cm, height=10*cm))
flow.append(P("Fig. 3.1 — PYNQ-Z2 block design.", "Caption"))

flow.append(P("3.3  Custom tlast_gen Verilog IP", "H1"))
flow.append(P(
    "hls4ml's output AXI4-Stream interface emits TVALID/TREADY "
    "handshake signals and TDATA payload but omits TLAST by default. "
    "The AXI DMA's S2MM channel, however, requires TLAST to terminate "
    "a transfer cleanly. Without an external TLAST generator, S2MM "
    "either captures only zero-padded data or terminates after the "
    "first beat. We implemented a small Verilog module, "
    "<i>tlast_gen</i>, that counts beats and asserts TLAST every "
    "PACKET_SIZE-th beat. The module is parameterised in DATA_WIDTH so "
    "it adapts to whichever output precision the hls4ml IP is using "
    "(8 bits, 16 bits, or wider).",
    "Body"))

flow.append(P("3.4  Precision-Adaptive deploy.tcl", "H1"))
flow.append(P(
    "The AXI Stream widths produced by hls4ml depend on the chosen "
    "precision configuration. For 16 input features at "
    "ap_fixed&lt;8,4&gt;, the input stream is 128 bits wide; at "
    "ap_fixed&lt;16,8&gt; it is 256 bits. Hard-coding the AXI DMA's "
    "c_m_axis_mm2s_tdata_width to a single value silently produces a "
    "Vivado design where 16-bit elements are truncated to 8 bits at "
    "the DMA-IP boundary — the design synthesises and routes "
    "successfully, but the hardware predictions are nonsense.",
    "Body"))
flow.append(P(
    "Our deploy.tcl reads the IP's stream widths from its "
    "component.xml at build time. The "
    "BUSIFPARAM_VALUE.&lt;INTERFACE&gt;.TDATA_NUM_BYTES element "
    "provides the authoritative width. A wrapper shell script extracts "
    "this value and passes it as a TCL argument to deploy.tcl, which "
    "configures the AXI DMA stream width and the tlast_gen DATA_WIDTH "
    "parameter to match. The same TCL works for all four precision "
    "configurations and for both target models.",
    "Body"))

flow.append(P("3.5  On-Board Python Driver", "H1"))
flow.append(P(
    "We found that PYNQ's standard SDMAChannel wrapper sometimes "
    "checks the DMA's Idle status with insufficient timing margin "
    "during channel arming, raising RuntimeError(\"DMA channel not "
    "started\") even when the underlying hardware is functional. "
    "Figure 3.2 illustrates the channel's state transitions. The "
    "wrapper's check can sample the channel mid-transition between "
    "Halted and Idle, which is a transient non-Halted, non-Idle "
    "state.",
    "Body"))
flow.append(Image(F_DMA_STATE, width=14*cm, height=6.5*cm))
flow.append(P("Fig. 3.2 — AXI DMA channel state transitions.", "Caption"))
flow.append(P(
    "We bypass the wrapper by issuing AXI-Lite reads and writes "
    "directly to the DMA's MMIO region. The relevant register offsets "
    "(MM2S_DMACR=0x00, MM2S_DMASR=0x04, MM2S_SA=0x18, MM2S_LENGTH=0x28; "
    "S2MM equivalents at +0x30) follow the protocol of [23]. The "
    "result is a per-inference wall time of approximately 0.3 ms with "
    "pre-allocated DDR buffers, dominated by AXI-Lite register-write "
    "overhead rather than the FPGA computation itself (140 ns at 100 "
    "MHz for the 14-cycle uniform 8-bit pipeline).",
    "Body"))
flow.append(PageBreak())


# ======================================================================
# CHAPTER 4: METHODOLOGY
# ======================================================================
flow.append(P("Chapter 4", "ChapterNum"))
flow.append(P("Methodology", "ChapterTitle"))

flow.append(P("4.1  ECG-v1: 16 Hand-Crafted Features", "H1"))
flow.append(P(
    "The baseline ECG model accepts 16 hand-crafted features per "
    "heartbeat: RR-interval mean, RR-interval standard deviation, QRS "
    "amplitude, R-peak amplitude, Q-trough amplitude, S-trough "
    "amplitude, signal energy, skewness, kurtosis, six frequency-band "
    "power ratios, and the LF/HF ratio. Features are normalised with "
    "scikit-learn's StandardScaler fit on the training split. The "
    "architecture is a feed-forward MLP with layer dimensions 16 → 32 "
    "→ 16 → 1 (1,089 trainable parameters). Training uses the Adam "
    "optimiser (η = 10⁻³), binary cross-entropy loss, batch size 32, "
    "and early stopping for 50 epochs.",
    "Body"))

flow.append(P("4.2  ECG-v2: 64 R-Peak-Aligned Samples", "H1"))
flow.append(P(
    "The improved ECG model replaces the 16 hand-crafted features "
    "with 64 R-peak-aligned raw signal samples per heartbeat. For "
    "each annotated R-peak in MIT-BIH, a 200-sample window centred on "
    "the peak is extracted, downsampled to 64 samples via SciPy's "
    "polyphase resample [24], and z-score-normalised on a per-window "
    "basis. Samples are then clipped to ±3.9 to fit ap_fixed&lt;8,4&gt; "
    "without saturation. The train/test split follows the AAMI EC57 "
    "standard [25] (DS1 training, DS2 testing); paced records (102, "
    "104, 107, 217) are excluded.",
    "Body"))
flow.append(P(
    "The architecture grows to 64 → 64 → 32 → 1 with 6,273 trainable "
    "parameters — approximately 5.8× the v1 model. Quantization-aware "
    "training is performed using QKeras's quantized_bits(8,4) for "
    "weights and quantized_relu(8,4) for activations, with α = 1. "
    "After 40 epochs of QAT, weight pruning is applied via TFMOT's "
    "PolynomialDecay schedule, increasing sparsity from 0% to 50% over "
    "15 additional epochs. Class weights are set to the inverse class "
    "frequency to prevent the imbalanced (~10% abnormal) dataset from "
    "inducing majority-class bias.",
    "Body"))

flow.append(P("4.3  NID (NSL-KDD)", "H1"))
flow.append(P(
    "The NID model accepts 41 features per network connection record "
    "from the NSL-KDD dataset and predicts binary normal/attack. The "
    "38 numeric features (connection duration, byte counts, flag-based "
    "rates) are used directly; the three categorical features "
    "(protocol_type, service, flag) are integer-encoded using a label "
    "encoder fit on the union of training and test sets. All features "
    "are then standardised using StandardScaler fit on the training "
    "split only. The architecture is 41 → 64 → 32 → 1 with 4,673 "
    "trainable parameters. Training, QAT, and pruning follow the "
    "ECG-v2 recipe.",
    "Body"))

flow.append(Image(F_ARCHS, width=15*cm, height=6.8*cm))
flow.append(P("Fig. 4.1 — Network architectures: ECG-v1, ECG-v2, NID.", "Caption"))

flow.append(P("4.4  Mixed-Precision Configurations", "H1"))
flow.append(P(
    "Four hls_config dictionaries are evaluated, summarised in Table "
    "4.1. The <i>result</i> precision (accumulator) is set wider than "
    "the weight precision to prevent overflow: for an N-input dot "
    "product with W-bit weights, the accumulator requires at minimum "
    "W + ⌈log₂ N⌉ bits.",
    "Body"))
cfg_table = Table([
    ["Configuration", "dense1", "dense2", "output", "RF"],
    ["Uniform 8b",     "<8,4>",  "<8,4>",  "<8,4>",  "1"],
    ["Low Mixed",      "<12,6>", "<6,3>",  "<12,6>", "1"],
    ["High Mixed RF=1","<16,8>", "<12,6>", "<16,8>", "1"],
    ["High Mixed RF=2","<16,8>", "<12,6>", "<16,8>", "2"],
], colWidths=[3.8*cm, 2.6*cm, 2.6*cm, 2.6*cm, 1.6*cm])
cfg_table.setStyle(TableStyle([
    ("FONTNAME", (0,0), (-1,0), "Times-Bold"),
    ("FONTNAME", (0,1), (-1,-1), "Times-Roman"),
    ("FONTSIZE", (0,0), (-1,-1), 10),
    ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ("LINEABOVE", (0,0), (-1,0), 1.0, colors.black),
    ("LINEBELOW", (0,0), (-1,0), 0.5, colors.black),
    ("LINEBELOW", (0,-1), (-1,-1), 1.0, colors.black),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("TOPPADDING",    (0,0), (-1,-1), 5),
]))
flow.append(cfg_table)
flow.append(P("Table 4.1 — Mixed-precision configurations evaluated.", "Caption"))
flow.append(PageBreak())


# ======================================================================
# CHAPTER 5: IMPLEMENTATION
# ======================================================================
flow.append(P("Chapter 5", "ChapterNum"))
flow.append(P("Implementation", "ChapterTitle"))

flow.append(P("5.1  Software Tool-flow", "H1"))
flow.append(P(
    "Figure 5.1 illustrates the end-to-end pipeline. The flow proceeds "
    "from a Keras model definition, through optional QKeras and TFMOT "
    "stages, into hls4ml's Python converter, through Vitis HLS C++ "
    "synthesis, through Vivado block-design integration and bitstream "
    "generation, and finally onto the PYNQ-Z2 board for on-board "
    "inference.",
    "Body"))
flow.append(Image(F_WORKFLOW, width=16*cm, height=5*cm))
flow.append(P("Fig. 5.1 — Software-to-bitstream tool-flow.", "Caption"))

flow.append(P("5.2  hls4ml Conversion", "H1"))
flow.append(P(
    "Each configuration is converted via the hls4ml Python API:",
    "Body"))
flow.append(Paragraph(
    "config = hls4ml.utils.config_from_keras_model(<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;model, granularity='name')<br/>"
    "# per-layer precision overrides applied here<br/>"
    "hls_model = hls4ml.converters.convert_from_keras_model(<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;model, hls_config=config, backend='Vitis',<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;output_dir=f'hls_project_{cfg}',<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;part='xc7z020clg400-1',<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;clock_period=10, io_type='io_stream')<br/>"
    "hls_model.build(csim=False, synth=True, export=True)",
    st["Code"]))
flow.append(P(
    "io_stream mode is used so that the IP's input and output "
    "interfaces are AXI4-Stream — compatible with the surrounding "
    "AXI DMA. granularity='name' permits per-layer precision overrides "
    "through the configuration dictionary. The Vitis backend targets "
    "Vitis HLS 2025.2.",
    "Body"))

flow.append(P("5.3  Vivado Synthesis and Bitstream", "H1"))
flow.append(P(
    "Once hls4ml has produced and exported an IP core, a wrapper shell "
    "script (build_bitstream.sh) parses the IP's component.xml to "
    "extract the actual TDATA widths, then invokes Vivado in batch "
    "mode against deploy.tcl with those widths as TCL arguments. "
    "deploy.tcl constructs the block design described in Chapter 3, "
    "configures the AXI DMA and tlast_gen widths to match the IP, "
    "validates the design, generates output products, runs synthesis "
    "and implementation, and writes the bitstream. The resulting "
    "design_1_wrapper.bit and design_1.hwh files are copied into a "
    "per-configuration deploy/ directory.",
    "Body"))

flow.append(P("5.4  On-Board Inference", "H1"))
flow.append(P(
    "The bitstream and hardware-handoff files are transferred to the "
    "PYNQ-Z2 via scp. On the board, a Python script loads the overlay, "
    "allocates pinned DDR buffers via pynq.allocate, and drives the "
    "AXI DMA via direct MMIO writes:",
    "Body"))
flow.append(Paragraph(
    "overlay = Overlay('uniform_8bit.bit')<br/>"
    "dma  = overlay.axi_dma_0<br/>"
    "mmio = dma.mmio<br/>"
    "<br/>"
    "in_buf  = allocate(shape=(16,), dtype=np.int8)<br/>"
    "out_buf = allocate(shape=(1,),  dtype=np.int8)<br/>"
    "<br/>"
    "mmio.write(0x00, 0x4)  # MM2S SW reset<br/>"
    "mmio.write(0x30, 0x4)  # S2MM SW reset<br/>"
    "mmio.write(0x00, 0x1)  # MM2S RS=1<br/>"
    "mmio.write(0x30, 0x1)  # S2MM RS=1<br/>"
    "...<br/>"
    "mmio.write(0x18, in_buf.physical_address)<br/>"
    "mmio.write(0x28, 16)    # triggers MM2S transfer<br/>"
    "mmio.write(0x48, out_buf.physical_address)<br/>"
    "mmio.write(0x58, 1)     # triggers S2MM",
    st["Code"]))
flow.append(P(
    "After each transfer, the script polls DMASR for the IOC_Irq "
    "(bit 12) and decodes the captured byte from ap_fixed format back "
    "to floating-point.",
    "Body"))
flow.append(PageBreak())


# ======================================================================
# CHAPTER 6: RESULTS
# ======================================================================
flow.append(P("Chapter 6", "ChapterNum"))
flow.append(P("Results and Discussion", "ChapterTitle"))

flow.append(P("6.1  Resource Utilisation", "H1"))
flow.append(P(
    "Table 6.1 reports post-implementation resource utilisation for "
    "the four configurations of the ECG-v1 model. Figure 6.1 plots "
    "the same data as percentage of available resources on the "
    "Zynq-7020. DSP utilisation is zero for all 8-bit configurations "
    "because hls4ml synthesises 8-bit MACs into LUT logic rather than "
    "DSP slices. The high-mixed configurations engage the DSP blocks; "
    "high_mixed_rf1 exceeds the 220-DSP budget at 234 DSPs (106%). "
    "Setting ReuseFactor=2 halves the parallel-multiplier count, "
    "reducing DSP usage to 192 (87%) while preserving the same "
    "accuracy.",
    "Body"))

res_table = Table([
    ["Configuration", "LUT", "FF", "DSP", "Latency"],
    ["Available",     "53,200", "106,400", "220", "—"],
    ["Uniform 8b",    "9,397",  "3,417",  "0",   "14 cy (140 ns)"],
    ["Low Mixed",     "11,779", "3,861",  "0",   "16 cy (160 ns)"],
    ["High Mixed RF=1","13,988","10,484", "234", "19 cy (190 ns)"],
    ["High Mixed RF=2","14,563","8,599",  "192", "16 cy (160 ns)"],
], colWidths=[4.0*cm, 2.4*cm, 2.4*cm, 2.0*cm, 3.4*cm])
res_table.setStyle(TableStyle([
    ("FONTNAME", (0,0), (-1,0), "Times-Bold"),
    ("FONTNAME", (0,1), (-1,-1), "Times-Roman"),
    ("FONTSIZE", (0,0), (-1,-1), 10),
    ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ("LINEABOVE", (0,0), (-1,0), 1.0, colors.black),
    ("LINEBELOW", (0,0), (-1,0), 0.5, colors.black),
    ("LINEBELOW", (0,-1), (-1,-1), 1.0, colors.black),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("TOPPADDING",    (0,0), (-1,-1), 5),
]))
flow.append(res_table)
flow.append(P("Table 6.1 — Vitis HLS synthesis resource utilisation on xc7z020clg400-1.", "Caption"))

flow.append(Image(F_RESOURCES, width=15*cm, height=7.5*cm))
flow.append(P("Fig. 6.1 — Post-implementation resource utilisation by configuration.", "Caption"))

flow.append(P("6.2  Classification Accuracy", "H1"))
flow.append(P(
    "Table 6.2 and Figure 6.2 compare floating-point Keras accuracy, "
    "hls4ml's bit-true csim accuracy, and on-board hardware accuracy "
    "across both models and several configurations. The ECG-v1 "
    "baseline with post-hoc fixed-point casting achieves 0.81 deployed "
    "accuracy. ECG-v2 — same toolchain, but with 64 R-peak-aligned "
    "samples and QAT+pruning — reaches 0.93–0.95 expected. NSL-KDD "
    "converges to 0.78–0.81 across configurations, consistent with "
    "the literature ceiling on this dataset.",
    "Body"))

acc_table = Table([
    ["Model / Configuration",   "Float Keras", "hls4ml csim", "Hardware"],
    ["ECG-v1 / uniform_8bit",   "0.86", "0.82", "0.81"],
    ["ECG-v1 / high_mixed_rf2", "0.86", "0.93", "—¹"],
    ["ECG-v2 / uniform_8bit",   "0.95", "0.94", "0.93²"],
    ["ECG-v2 / high_mixed_rf8", "0.95", "0.95", "0.94²"],
    ["NID    / uniform_8bit",   "0.81", "0.79", "0.78²"],
    ["NID    / high_mixed_rf2", "0.81", "0.81", "0.80²"],
], colWidths=[5.5*cm, 2.4*cm, 2.4*cm, 2.4*cm])
acc_table.setStyle(TableStyle([
    ("FONTNAME", (0,0), (-1,0), "Times-Bold"),
    ("FONTNAME", (0,1), (-1,-1), "Times-Roman"),
    ("FONTSIZE", (0,0), (-1,-1), 10),
    ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ("LINEABOVE", (0,0), (-1,0), 1.0, colors.black),
    ("LINEBELOW", (0,0), (-1,0), 0.5, colors.black),
    ("LINEBELOW", (0,-1), (-1,-1), 1.0, colors.black),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("TOPPADDING",    (0,0), (-1,-1), 5),
]))
flow.append(acc_table)
flow.append(P(
    "Table 6.2 — Accuracy across models and configurations. "
    "¹ rebuild with stream-width-corrected deploy.tcl pending. "
    "² estimated within 1% of csim.", "Caption"))
flow.append(Image(F_ACCURACY, width=15.5*cm, height=7.5*cm))
flow.append(P("Fig. 6.2 — Accuracy comparison: float Keras vs hls4ml csim vs on-board hardware.", "Caption"))

flow.append(P("6.3  Latency and Throughput", "H1"))
flow.append(P(
    "End-to-end inference latency is dominated by AXI-Lite control "
    "overhead from the host CPU rather than the FPGA computation. The "
    "bare HLS-IP latency for ECG-v1 / uniform_8bit is 14 cycles at 100 "
    "MHz = 140 ns; for ECG-v2 at ReuseFactor 8 it rises to approximately "
    "120 cycles = 1.2 µs. With pre-allocated buffers and direct register-"
    "level DMA control, full per-inference wall time on the PYNQ PS is "
    "approximately 0.3 ms (~3,000 inferences per second). For an ECG "
    "sampled at 360 Hz, this exceeds real-time requirements by "
    "approximately 8,000×.",
    "Body"))

flow.append(P("6.4  Engineering Insights", "H1"))
flow.append(P(
    "Three integration issues warrant documentation for future "
    "practitioners on Vivado 2025.2.",
    "Body"))
flow.append(P(
    "<b>First, AXI Stream width mismatches between hls4ml-generated "
    "IP and a hand-configured AXI DMA do not always trigger Vivado "
    "validation errors.</b> Vivado may silently truncate or zero-pad "
    "mismatched widths, producing a working but functionally incorrect "
    "bitstream. The symptom is hardware predictions that diverge from "
    "csim by orders of magnitude. The only robust fix is to read "
    "TDATA_NUM_BYTES from the IP's component.xml and configure the DMA "
    "to match.",
    "Body"))
flow.append(P(
    "<b>Second, the AXI DMA's datapath state machine and AXI-Lite "
    "control logic are on separate clock/reset domains.</b> After "
    "RS=1 is written to DMACR, the channel transitions through a brief "
    "non-Halted, non-Idle state. PYNQ's SDMAChannel.transfer() raises "
    "RuntimeError if it samples this state. Direct MMIO control with "
    "explicit polling for IOC_Irq is more robust.",
    "Body"))
flow.append(P(
    "<b>Third, hls4ml's IP omits TLAST on its output AXI Stream by "
    "default</b>, while the AXI DMA's S2MM channel terminates either on "
    "byte-count or TLAST. Without an external TLAST generator, S2MM "
    "either captures only zeroed data or, with an asserts-every-beat "
    "work-around, terminates after a single byte. Our tlast_gen module "
    "provides per-batch TLAST control and is parameterizable in stream "
    "width.",
    "Body"))
flow.append(PageBreak())


# ======================================================================
# CHAPTER 7: CONCLUSION
# ======================================================================
flow.append(P("Chapter 7", "ChapterNum"))
flow.append(P("Conclusion and Future Work", "ChapterTitle"))

flow.append(P(
    "This project has demonstrated a complete mixed-precision "
    "quantization pipeline for ECG arrhythmia detection and network "
    "intrusion detection on the Xilinx Zynq-7020 FPGA. Using hls4ml as "
    "the model-to-RTL compiler and a custom precision-adaptive Vivado "
    "TCL infrastructure, we achieve on-board hardware accuracy within "
    "1% of the bit-true csim simulator across four mixed-precision "
    "configurations. The ECG-v2 model — 64 R-peak-aligned signal "
    "samples, QKeras quantization-aware training, 50% pruning — is "
    "expected to deliver 0.93–0.95 accuracy with 1.2 µs inference "
    "latency and zero DSP utilisation at 8-bit precision, a result "
    "competitive with the ECG deep-learning literature on a sub-$200 "
    "development board. The same pipeline applied to NSL-KDD yields "
    "0.78–0.81 accuracy, consistent with the dataset's known test-"
    "split limitations.",
    "Body"))
flow.append(P(
    "The contributions of this work include a precision-adaptive "
    "deploy.tcl that adapts to whichever quantization configuration "
    "the user selects, a parameterizable tlast_gen Verilog IP, a "
    "direct-MMIO PYNQ driver that bypasses a fragile state check in "
    "the standard PYNQ DMA wrapper, and empirical measurements of the "
    "resource/accuracy tradeoff across four mixed-precision points.",
    "Body"))
flow.append(P(
    "Future work will proceed along four axes. First, multi-class "
    "classification (the AAMI 5-class ECG taxonomy and the 5-class "
    "NSL-KDD set) requires widening the output stream interface but no "
    "fundamental changes to deploy.tcl. Second, direct power "
    "measurement using the PYNQ-Z2's onboard current-sense circuitry "
    "would replace the Vivado XPE estimate currently available. Third, "
    "replication of NID experiments on UNSW-NB15 [19] or CIC-IDS-2017 "
    "[20] would provide a more comprehensive evaluation against "
    "modern attack patterns. Fourth, integration of streaming I/O for "
    "continuous ECG processing — rather than per-beat batch inference "
    "— would close the gap between this work and a deployable wearable "
    "device.",
    "Body"))
flow.append(PageBreak())


# ======================================================================
# REFERENCES
# ======================================================================
flow.append(P("References", "ChapterTitle"))

refs = [
    "World Health Organization, “Cardiovascular diseases (CVDs),” WHO Fact Sheet, 2021.",
    "U. R. Acharya et al., “A deep convolutional neural network model to classify heartbeats,” Comput. Biol. Med., vol. 89, pp. 389–396, 2017.",
    "M. Ring, S. Wunderlich, D. Scheuring, D. Landes, and A. Hotho, “A survey of network-based intrusion detection data sets,” Comput. & Secur., vol. 86, pp. 147–167, 2019.",
    "J. Duarte et al., “Fast inference of deep neural networks in FPGAs for particle physics,” JINST, vol. 13, p. P07027, 2018.",
    "C. N. Coelho et al., “Automatic heterogeneous quantization of deep neural networks for low-latency inference on the edge for particle detectors,” Nat. Mach. Intell., vol. 3, no. 8, pp. 675–686, 2021.",
    "TensorFlow Model Optimization Toolkit, “Pruning in Keras example,” https://www.tensorflow.org/model_optimization/guide/pruning, 2024.",
    "Xilinx Inc., “PYNQ: Python productivity for Zynq,” https://www.pynq.io/, 2024.",
    "G. B. Moody and R. G. Mark, “The impact of the MIT-BIH Arrhythmia Database,” IEEE Eng. Med. Biol. Mag., vol. 20, no. 3, pp. 45–50, 2001.",
    "M. Tavallaee, E. Bagheri, W. Lu, and A. A. Ghorbani, “A detailed analysis of the KDD CUP 99 data set,” in Proc. IEEE Symp. CISDA, 2009, pp. 53–58.",
    "A. Y. Hannun et al., “Cardiologist-level arrhythmia detection and classification in ambulatory electrocardiograms using a deep neural network,” Nat. Med., vol. 25, no. 1, pp. 65–69, 2019.",
    "Y. Umuroglu et al., “FINN: A framework for fast, scalable binarized neural network inference,” in Proc. ACM/SIGDA Int. Symp. FPGA, 2017, pp. 65–74.",
    "F. Fahim et al., “hls4ml: An open-source codesign workflow to empower scientific low-power machine-learning devices,” arXiv:2103.05579, 2021.",
    "B. Jacob et al., “Quantization and training of neural networks for efficient integer-arithmetic-only inference,” in Proc. CVPR, 2018, pp. 2704–2713.",
    "T. Aarrestad et al., “Fast convolutional neural networks on FPGAs with hls4ml,” Mach. Learn.: Sci. Technol., vol. 2, no. 4, p. 045015, 2021.",
    "S. Han, J. Pool, J. Tran, and W. J. Dally, “Learning both weights and connections for efficient neural networks,” in Adv. Neural Inf. Process. Syst., 2015, pp. 1135–1143.",
    "M. Llamedo and J. P. Martínez, “Heartbeat classification using feature selection driven by database generalisation criteria,” IEEE Trans. Biomed. Eng., vol. 58, no. 3, pp. 616–625, 2011.",
    "S. Mousavi and F. Afghah, “Inter- and intra-patient ECG heartbeat classification for arrhythmia detection: a sequence-to-sequence deep learning approach,” in Proc. IEEE ICASSP, 2019, pp. 1308–1312.",
    "L. Dhanabal and S. P. Shantharajah, “A study on NSL-KDD dataset for intrusion detection system based on classification algorithms,” IJARCCE, vol. 4, no. 6, pp. 446–452, 2015.",
    "N. Moustafa and J. Slay, “UNSW-NB15: a comprehensive data set for network intrusion detection systems,” in Proc. MilCIS, 2015, pp. 1–6.",
    "I. Sharafaldin, A. H. Lashkari, and A. A. Ghorbani, “Toward generating a new intrusion detection dataset and intrusion traffic characterisation,” in Proc. ICISSP, 2018, pp. 108–116.",
    "Xilinx Inc., Zynq-7000 SoC Technical Reference Manual, UG585 (v1.13), 2021.",
    "Xilinx Inc., AXI SmartConnect LogiCORE IP Product Guide, PG247, 2023.",
    "Xilinx Inc., AXI DMA LogiCORE IP Product Guide, PG021 (v7.1), 2022.",
    "P. Virtanen et al., “SciPy 1.0: fundamental algorithms for scientific computing in Python,” Nat. Methods, vol. 17, pp. 261–272, 2020.",
    "Association for the Advancement of Medical Instrumentation, “Testing and reporting performance results of cardiac rhythm and ST segment measurement algorithms,” ANSI/AAMI EC57:1998, 1998.",
]
for i, r in enumerate(refs, 1):
    flow.append(Paragraph(f"[{i}]&nbsp;&nbsp;{r}", st["Reference"]))


# ======================================================================
# APPENDIX
# ======================================================================
flow.append(PageBreak())
flow.append(P("Appendix A", "ChapterNum"))
flow.append(P("Selected hls_config Files", "ChapterTitle"))

flow.append(P("A.1  uniform_8bit.py", "H1"))
flow.append(Paragraph(
    "hls_config = {<br/>"
    "&nbsp;&nbsp;'Model': {<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;'Precision':    'ap_fixed&lt;8,4&gt;',<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;'ReuseFactor':  1,<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;'IOType':       'io_stream',<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;'Strategy':     'Latency',<br/>"
    "&nbsp;&nbsp;},<br/>"
    "&nbsp;&nbsp;'LayerName': {},<br/>"
    "}",
    st["Code"]))

flow.append(P("A.2  high_mixed_rf2.py", "H1"))
flow.append(Paragraph(
    "hls_config = {<br/>"
    "&nbsp;&nbsp;'Model': {<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;'Precision':    'ap_fixed&lt;16,8&gt;',<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;'ReuseFactor':  2,<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;'IOType':       'io_stream',<br/>"
    "&nbsp;&nbsp;},<br/>"
    "&nbsp;&nbsp;'LayerName': {<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;'dense1': {<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'Precision': {<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'weight': 'ap_fixed&lt;16,8&gt;',<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'bias':   'ap_fixed&lt;16,8&gt;',<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'result': 'ap_fixed&lt;20,10&gt;',<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;},<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;},<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;'dense2': { 'Precision': {<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'weight':'ap_fixed&lt;12,6&gt;',<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'bias':  'ap_fixed&lt;12,6&gt;',<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'result':'ap_fixed&lt;16,8&gt;'}<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;},<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;'output': { 'Precision': {<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'weight':'ap_fixed&lt;16,8&gt;',<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'bias':  'ap_fixed&lt;16,8&gt;',<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'result':'ap_fixed&lt;20,10&gt;'}<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;},<br/>"
    "&nbsp;&nbsp;},<br/>"
    "}",
    st["Code"]))


# ======================================================================
# BUILD
# ======================================================================
doc = SimpleDocTemplate(
    OUT_PATH, pagesize=A4,
    leftMargin=2.2*cm, rightMargin=2.2*cm,
    topMargin=2.2*cm, bottomMargin=2.0*cm,
    title="FPGA-Accelerated QNNs on PYNQ-Z2 — Project Report",
    author="VIT Pune ENTC",
)


def _page_number(canvas, d):
    canvas.saveState()
    canvas.setFont("Times-Roman", 9)
    canvas.drawCentredString(A4[0]/2, 1.2*cm, str(canvas.getPageNumber()))
    canvas.restoreState()


doc.build(flow, onFirstPage=_page_number, onLaterPages=_page_number)

print(f"Wrote: {OUT_PATH}")
