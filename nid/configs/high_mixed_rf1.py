# NID config — high precision, ReuseFactor=1 (max parallelism).
# Likely over the Z-7020's 220 DSP budget without pruning. Keep for the
# accuracy/resource tradeoff comparison, deploy only if QKeras + 50%
# pruning brings DSP usage under budget.

hls_config = {
    'Model': {
        'Precision':   'ap_fixed<16,8>',
        'ReuseFactor': 1,
        'IOType':      'io_stream',
        'Strategy':    'Latency',
    },
    'LayerName': {
        'dense1': {
            'Precision': {
                'weight': 'ap_fixed<16,8>',
                'bias':   'ap_fixed<16,8>',
                'result': 'ap_fixed<20,10>',
            },
        },
        'dense2': {
            'Precision': {
                'weight': 'ap_fixed<12,6>',
                'bias':   'ap_fixed<12,6>',
                'result': 'ap_fixed<16,8>',
            },
        },
        'output': {
            'Precision': {
                'weight': 'ap_fixed<16,8>',
                'bias':   'ap_fixed<16,8>',
                'result': 'ap_fixed<20,10>',
            },
        },
    },
}
