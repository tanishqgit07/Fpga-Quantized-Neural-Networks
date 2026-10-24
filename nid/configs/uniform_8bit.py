# NID config — uniform 8-bit precision, ReuseFactor 1

hls_config = {
    'Model': {
        'Precision':    'ap_fixed<8,4>',
        'ReuseFactor':  1,
        'IOType':       'io_stream',
        'Strategy':     'Latency',
    },
    'LayerName': {},
}
