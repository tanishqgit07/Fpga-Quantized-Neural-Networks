# ECG v2 — uniform 8-bit precision, ReuseFactor=8
#
# v2's network is ~6x larger (6273 params vs 1089 in v1). RF=1 would
# blow past the LUT budget on Z-7020. RF=8 brings parallel-MAC count
# down to ~770, which fits comfortably with ~50% LUT util.

hls_config = {
    'Model': {
        'Precision':    'ap_fixed<8,4>',
        'ReuseFactor':  8,
        'IOType':       'io_stream',
        'Strategy':     'Latency',
    },
    'LayerName': {},
}
