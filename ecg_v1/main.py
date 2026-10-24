import numpy as np
import sys
import importlib
import json
from tensorflow import keras
from sklearn.metrics import accuracy_score
import hls4ml

MODEL_PATH = "model.h5"
FPGA_PART  = "xc7z020clg400-1"


def merge_config(model, user_config):
    """
    Merge user hls_config dict into hls4ml's auto-generated config.
    """
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
        print("Usage: python3 main.py <config_module>")
        print("Example: python3 main.py configs.uniform_8bit")
        print("\nAvailable configs:")
        print("  configs.uniform_8bit")
        print("  configs.low_mixed")
        print("  configs.high_mixed_rf1")
        print("  configs.high_mixed_rf2")
        sys.exit(1)

    config_module_name = sys.argv[1]
    print(f"Loading config: {config_module_name}")

    try:
        config_module = importlib.import_module(config_module_name)
        user_config   = config_module.hls_config
    except ModuleNotFoundError:
        print(f"ERROR: Could not find config module '{config_module_name}'")
        sys.exit(1)

    config_name = config_module_name.split('.')[-1]
    output_dir  = f"hls_project_{config_name}"

    print("\nLoading model...")
    model = keras.models.load_model(MODEL_PATH)
    model.summary()

    X_test = np.load('X_test.npy')
    y_test = np.load('y_test.npy')

    y_keras = (model.predict(X_test) > 0.5).astype(int).flatten()
    keras_acc = accuracy_score(y_test, y_keras)
    print(f"Keras Accuracy: {keras_acc:.4f}")

    print("\nGenerating HLS configuration...")
    config = merge_config(model, user_config)

    print("\nFinal HLS config:")
    try:
        print(json.dumps(config, indent=2, default=str))
    except (TypeError, ValueError):
        from pprint import pprint
        pprint(config)

    print(f"\nConverting to HLS project: {output_dir}")
    hls_model = hls4ml.converters.convert_from_keras_model(
        model,
        hls_config=config,
        backend='Vitis',
        output_dir=output_dir,
        part=FPGA_PART,
        clock_period=10,
        io_type='io_stream'
    )

    print("\nCompiling HLS model...")
    hls_model.compile()

    y_hls = (hls_model.predict(X_test) > 0.5).astype(int).flatten()
    hls_acc = accuracy_score(y_test, y_hls)
    print(f"hls4ml Accuracy: {hls_acc:.4f}")
    print(f"Accuracy drop:   {keras_acc - hls_acc:.4f}")

    print(f"\nRunning HLS synth + IP export...")
    print(f"Monitor: tail -f {output_dir}/vitis_hls.log")
    hls_model.build(csim=False, synth=True, export=True)

    print("\nSynthesis Report:")
    hls4ml.report.read_vivado_report(output_dir)

    print(f"\n----------------------------------------")
    print(f"HLS done. IP packaged at:")
    print(f"  {output_dir}/myproject_prj/solution1/impl/ip")
    print(f"\nNext step — build bitstream:")
    print(f"  ./build_bitstream.sh {config_name}")
    print(f"----------------------------------------")


if __name__ == "__main__":
    main()
