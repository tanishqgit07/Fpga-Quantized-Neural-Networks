# ECG v2 — high precision (10-16 bit) with ReuseFactor=8.
# Highest accuracy point in the precision/accuracy tradeoff.

hls_config = {
    'Model': {
        'Precision':    'ap_fixed<16,8>',
        'ReuseFactor':  8,
        'IOType':       'io_stream',
        'Strategy':     'Latency',
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
