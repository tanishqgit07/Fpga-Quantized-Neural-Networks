"""
main_path_a.py — VivadoAccelerator backend (Vivado 2020.1) end-to-end build.

This is the Path A variant. It uses hls4ml's VivadoAccelerator backend
which auto-generates the block design (PS + DMA + reset + IP) and emits
.bit + .hwh in one shot. No manual deploy.tcl required.

Toolchain requirement:
    Vivado 2020.1 + Vivado HLS 2020.1 must be on PATH.
    Run `. .\\activate.ps1` from the project root first.

Usage:
    python main_path_a.py configs.uniform_8bit
"""

import os
import sys
import importlib
import json
import shutil

os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")

import numpy as np
from tensorflow import keras
from sklearn.metrics import accuracy_score
import hls4ml
from qkeras.utils import load_qmodel

MODEL_PATH = "model_qkeras.h5"
BOARD      = "pynq-z2"
# Stamp this into the Vivado project name so .xpr files are recognizable
# (e.g. ecg_v1_uniform_8bit.xpr instead of project_1.xpr)
PROJECT_PREFIX = "ecg_v1"


def merge_config(model, user_config):
    config = hls4ml.utils.config_from_keras_model(model, granularity='name')
    for k, v in user_config.get('Model', {}).items():
        config['Model'][k] = v
    for layer, layer_cfg in user_config.get('LayerName', {}).items():
        if layer in config['LayerName']:
            for k, v in layer_cfg.items():
                config['LayerName'][layer][k] = v
        else:
            config['LayerName'][layer] = layer_cfg
    return config


def main():
    if len(sys.argv) < 2:
        print("Usage: python main_path_a.py <config_module>")
        print("Example: python main_path_a.py configs.uniform_8bit")
        sys.exit(1)

    config_module_name = sys.argv[1]
    config_module = importlib.import_module(config_module_name)
    user_config = config_module.hls_config

    config_name = config_module_name.split('.')[-1]
    output_dir  = f"hls_project_{config_name}_a"

    print(f"Loading model: {MODEL_PATH}")
    # load_qmodel registers QKeras custom layers (QDense, QActivation, ...)
    model = load_qmodel(MODEL_PATH)
    model.summary()

    X_test = np.load('X_test.npy')
    y_test = np.load('y_test.npy')

    y_keras = (model.predict(X_test, verbose=0) > 0.5).astype(int).flatten()
    keras_acc = accuracy_score(y_test, y_keras)
    print(f"Keras accuracy: {keras_acc:.4f}")

    config = merge_config(model, user_config)
    # io_type lives inside Model for VivadoAccelerator
    config['Model']['IOType'] = user_config.get('Model', {}).get('IOType', 'io_stream')

    print("\nFinal HLS config:")
    try:
        print(json.dumps(config, indent=2, default=str))
    except (TypeError, ValueError):
        from pprint import pprint
        pprint(config)

    print(f"\nConverting (backend=VivadoAccelerator, board={BOARD})...")
    hls_model = hls4ml.converters.convert_from_keras_model(
        model,
        hls_config=config,
        backend='VivadoAccelerator',
        board=BOARD,
        output_dir=output_dir,
        clock_period=10,
    )

    # Skip hls_model.compile()/predict() on Windows — hls4ml uses a .sh
    # script to build the C++ shared lib for Python-side prediction, which
    # cmd.exe can't run.
    print("\nSkipping hls_model.compile()/predict() (Windows: needs bash for build_lib.sh)")

    # Patch design.tcl to use a recognizable project name instead of
    # "project_1" everywhere. The substitution renames the Vivado project,
    # the .xpr file, and all the project_1.runs/.srcs/.cache directories.
    vivado_proj_name = f"{PROJECT_PREFIX}_{config_name}"
    design_tcl_path = os.path.join(output_dir, "design.tcl")
    if os.path.exists(design_tcl_path):
        with open(design_tcl_path, "r") as f:
            design_tcl = f.read()
        # Only rename literal "project_1" tokens — preserved in path strings,
        # create_project arg, project_1.runs/.srcs references, etc.
        design_tcl = design_tcl.replace("project_1", vivado_proj_name)
        with open(design_tcl_path, "w") as f:
            f.write(design_tcl)
        print(f"Patched design.tcl: Vivado project = {vivado_proj_name}")

    print("\nBuilding bitstream (HLS synth + Vivado synth + impl + write_bitstream)...")
    print("This typically takes 10-30 min per config.")
    hls_model.build(csim=False, synth=True, export=True, bitfile=True)

    # Package the deploy artifacts
    deploy_dir = os.path.abspath(f"deploy/{config_name}")
    os.makedirs(deploy_dir, exist_ok=True)
    prj = os.path.join(output_dir, "myproject_vivado_accelerator")
    bit = os.path.join(prj, f"{vivado_proj_name}.runs", "impl_1", "design_1_wrapper.bit")
    hwh = os.path.join(prj, f"{vivado_proj_name}.srcs", "sources_1", "bd",
                       "design_1", "hw_handoff", "design_1.hwh")
    drv = os.path.join(output_dir, "axi_stream_driver.py")
    for src, dst_name in [(bit, f"{config_name}.bit"),
                          (hwh, f"{config_name}.hwh"),
                          (drv, "axi_stream_driver.py")]:
        if os.path.exists(src):
            shutil.copy(src, os.path.join(deploy_dir, dst_name))
            print(f"  + {dst_name}")
        else:
            print(f"  ! MISSING: {src}")

    print(f"\nDone. Bitstream + .hwh in: {deploy_dir}")


if __name__ == "__main__":
    main()
