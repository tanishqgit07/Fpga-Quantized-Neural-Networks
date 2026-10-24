// tlast_gen
//
// AXI4-Stream passthrough that asserts TLAST on the final beat of every
// PACKET_SIZE-beat packet. Replaces the axis_subset_converter band-aid
// (which asserted TLAST on every beat — DMA terminates after 1 byte).
//
// PACKET_SIZE is the number of input beats per output packet. For a
// per-inference single-byte output, set PACKET_SIZE=1 (TLAST every beat,
// equivalent to old behavior). For a batched receive of N inferences,
// set PACKET_SIZE=N so DMA receives a single N-byte packet.

`default_nettype none

module tlast_gen #(
    parameter integer DATA_WIDTH  = 8,
    parameter integer PACKET_SIZE = 1
) (
    input  wire                    aclk,
    input  wire                    aresetn,

    input  wire [DATA_WIDTH-1:0]   s_axis_tdata,
    input  wire                    s_axis_tvalid,
    output wire                    s_axis_tready,

    output wire [DATA_WIDTH-1:0]   m_axis_tdata,
    output wire                    m_axis_tvalid,
    input  wire                    m_axis_tready,
    output wire                    m_axis_tlast
);

    localparam integer CW = (PACKET_SIZE <= 1) ? 1 : $clog2(PACKET_SIZE);

    reg [CW-1:0] beat_count;

    wire beat_fire = s_axis_tvalid & s_axis_tready;
    wire is_last_beat = (PACKET_SIZE <= 1) ? 1'b1
                                           : (beat_count == PACKET_SIZE - 1);

    always @(posedge aclk) begin
        if (!aresetn) begin
            beat_count <= {CW{1'b0}};
        end else if (beat_fire) begin
            if (is_last_beat)
                beat_count <= {CW{1'b0}};
            else
                beat_count <= beat_count + 1'b1;
        end
    end

    assign m_axis_tdata  = s_axis_tdata;
    assign m_axis_tvalid = s_axis_tvalid;
    assign s_axis_tready = m_axis_tready;
    assign m_axis_tlast  = is_last_beat;

endmodule

`default_nettype wire
