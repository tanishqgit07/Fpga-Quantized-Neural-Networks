# NID config — low precision (6-12 bit), ReuseFactor=1.
# Smaller LUT/DSP usage at the cost of accuracy. Useful as the
# "minimum-resource" point in the precision/accuracy tradeoff.

hls_config = {
    'Model': {
        'Precision':   'ap_fixed<12,6>',
        'ReuseFactor': 1,
        'IOType':      'io_stream',
        'Strategy':    'Latency',
    },
    'LayerName': {
        'dense1': {
            'Precision': {
                'weight': 'ap_fixed<6,2>',
                'bias':   'ap_fixed<6,2>',
                'result': 'ap_fixed<12,6>',
            },
        },
        'dense2': {
            'Precision': {
                'weight': 'ap_fixed<6,2>',
                'bias':   'ap_fixed<6,2>',
                'result': 'ap_fixed<12,6>',
            },
        },
        'output': {
            'Precision': {
                'weight': 'ap_fixed<8,4>',
                'bias':   'ap_fixed<8,4>',
                'result': 'ap_fixed<12,6>',
            },
        },
    },
}
