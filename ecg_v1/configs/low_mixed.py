hls_config = {
    'Model': {
        'Precision':   'ap_fixed<8,4>',
        'ReuseFactor': 1,
        'IOType':'io_stream',
        'Strategy':    'Latency'
    },
    'LayerName': {
        'dense1': {
            'Precision': {
                'weight': 'ap_fixed<12,6>',
                'bias':   'ap_fixed<12,6>',
                'result': 'ap_fixed<14,7>'
            }
        },
        'dense2': {
            'Precision': {
                'weight': 'ap_fixed<6,3>',
                'bias':   'ap_fixed<6,3>',
                'result': 'ap_fixed<8,4>'
            }
        },
        'output': {
            'Precision': {
                'weight': 'ap_fixed<12,6>',
                'bias':   'ap_fixed<12,6>',
                'result': 'ap_fixed<14,7>'
            }
        }
    }
}