# deploy.tcl
#
# Build a PYNQ-Z2 bitstream that wraps the hls4ml-generated IP
# (myproject) with AXI DMA, a TLAST generator, and a Zynq PS.
#
# Replaces the previous broken deploy.tcl. Designed to mirror what
# hls4ml's VivadoAccelerator backend would produce, but on Vivado 2025.2
# with SmartConnect (the AXI Interconnect successor) and a correctly
# wired reset chain.
#
# Standalone — main.py does NOT invoke this. Run after HLS finishes:
#   ./build_bitstream.sh <config_name>
# which in turn calls:
#   vivado -mode batch -source deploy.tcl -tclargs <config> <hls_ip> <tlast_ip> <output_dir>
#
# tclargs:
#   0: config_name      — e.g. "uniform_8bit"
#   1: hls_ip_dir       — directory containing the hls4ml-exported IP (component.xml)
#   2: tlast_ip_dir     — directory containing the packaged tlast_gen IP
#   3: output_dir       — absolute path; project is created at <output_dir>/vivado_proj
#   4: in_bytes         — TDATA bytes of the IP's input stream (dense1_input)
#   5: out_bytes        — TDATA bytes of the IP's output stream (layer7_out)
#
# in_bytes / out_bytes come from build_bitstream.sh which extracts them from
# the IP's component.xml. Hardcoding 128/8 as before only works for one
# specific precision config; the rest get butchered streams.

if {$argc < 6} {
    puts "ERROR: deploy.tcl requires 6 args: <config> <hls_ip_dir> <tlast_ip_dir> <output_dir> <in_bytes> <out_bytes>"
    exit 1
}

set config_name  [lindex $argv 0]
set hls_ip_dir   [lindex $argv 1]
set tlast_ip_dir [lindex $argv 2]
set output_dir   [lindex $argv 3]
set in_bytes     [lindex $argv 4]
set out_bytes    [lindex $argv 5]
set in_bits      [expr {$in_bytes * 8}]
set out_bits     [expr {$out_bytes * 8}]

# AXI DMA's MM data widths are constrained to {128, 256, 512, 1024} on Z-7020.
# Pick the smallest legal value >= the corresponding stream width.
proc pick_mm_width {min_bits} {
    foreach w {128 256 512 1024} {
        if {$w >= $min_bits} { return $w }
    }
    return 1024
}
set mm2s_mm_width [pick_mm_width $in_bits]
set s2mm_mm_width [pick_mm_width $out_bits]
puts "deploy.tcl: stream widths input=${in_bits} bits, output=${out_bits} bits"
puts "deploy.tcl: MM widths     mm2s=${mm2s_mm_width} bits, s2mm=${s2mm_mm_width} bits"

set proj_name "vivado_proj"
set proj_dir  [file join $output_dir $proj_name]

puts "deploy.tcl: building bitstream for $config_name"
puts "  hls_ip_dir   = $hls_ip_dir"
puts "  tlast_ip_dir = $tlast_ip_dir"
puts "  proj_dir     = $proj_dir"

# ----------------------------------------------------------------------
# Helpers — pick the latest installed version of an IP by name, so the
# script survives Vivado upgrades without us hard-coding :7.1, :5.5 etc.
# ----------------------------------------------------------------------
proc latest_ip_vlnv {ip_name} {
    set candidates [get_ipdefs -all -filter "NAME == $ip_name"]
    if {[llength $candidates] == 0} {
        error "No IP found with NAME == $ip_name"
    }
    return [lindex [lsort -dictionary $candidates] end]
}

# ----------------------------------------------------------------------
# 1. Project setup
# ----------------------------------------------------------------------
file delete -force $proj_dir
create_project $proj_name $proj_dir -part xc7z020clg400-1 -force

# Try to apply PYNQ-Z2 board part; fall back to part-only if board file missing
if {[catch {set_property BOARD_PART tul.com.tw:pynq-z2:part0:1.0 [current_project]} err]} {
    puts "WARNING: PYNQ-Z2 board file not found ($err). Continuing with part-only."
}

# Add IP repos
set_property ip_repo_paths [list $hls_ip_dir $tlast_ip_dir] [current_project]
update_ip_catalog -rebuild

# ----------------------------------------------------------------------
# 2. Block design
# ----------------------------------------------------------------------
create_bd_design "design_1"
current_bd_design design_1

# Zynq PS
create_bd_cell -type ip -vlnv [latest_ip_vlnv processing_system7] ps7

# Apply board preset if available; configures DDR + FIXED_IO and minimal MIO
if {[catch {
    apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \
        -config {apply_board_preset "1" Master "Disable" Slave "Disable"} \
        [get_bd_cells ps7]
} err]} {
    puts "WARNING: apply_bd_automation for ps7 failed ($err). Trying default preset."
    apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \
        -config {Master "Disable" Slave "Disable"} \
        [get_bd_cells ps7]
}

# Enable HP0 (was the previous root-cause hang), keep GP0 enabled, set FCLK_CLK0=100MHz
set_property -dict [list \
    CONFIG.PCW_USE_S_AXI_HP0          {1} \
    CONFIG.PCW_S_AXI_HP0_DATA_WIDTH   {64} \
    CONFIG.PCW_USE_M_AXI_GP0          {1} \
    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100} \
    CONFIG.PCW_EN_CLK0_PORT           {1} \
    CONFIG.PCW_EN_RST0_PORT           {1} \
] [get_bd_cells ps7]

# AXI DMA — widths now match the IP's actual stream widths
create_bd_cell -type ip -vlnv [latest_ip_vlnv axi_dma] axi_dma_0
set_property -dict [list \
    CONFIG.c_include_sg               {0} \
    CONFIG.c_include_mm2s             {1} \
    CONFIG.c_m_axi_mm2s_data_width    $mm2s_mm_width \
    CONFIG.c_m_axis_mm2s_tdata_width  $in_bits \
    CONFIG.c_mm2s_burst_size          {16} \
    CONFIG.c_include_s2mm             {1} \
    CONFIG.c_m_axi_s2mm_data_width    $s2mm_mm_width \
    CONFIG.c_s_axis_s2mm_tdata_width  $out_bits \
    CONFIG.c_s2mm_burst_size          {16} \
    CONFIG.c_sg_length_width          {26} \
] [get_bd_cells axi_dma_0]

# hls4ml IP — myproject
create_bd_cell -type ip -vlnv [latest_ip_vlnv myproject] myproject_0

# tlast_gen — adds TLAST on every PACKET_SIZE-th beat
# DATA_WIDTH must match the IP's output stream (out_bits).
create_bd_cell -type ip -vlnv [latest_ip_vlnv tlast_gen] tlast_gen_0
set_property -dict [list \
    CONFIG.PACKET_SIZE {1} \
    CONFIG.DATA_WIDTH  $out_bits \
] [get_bd_cells tlast_gen_0]

# proc_sys_reset
create_bd_cell -type ip -vlnv [latest_ip_vlnv proc_sys_reset] rst_0

# SmartConnect for control: PS GP0 → DMA Lite
create_bd_cell -type ip -vlnv [latest_ip_vlnv smartconnect] sc_ctrl
set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {1}] [get_bd_cells sc_ctrl]

# SmartConnect for data: DMA MM2S + DMA S2MM → PS HP0
create_bd_cell -type ip -vlnv [latest_ip_vlnv smartconnect] sc_data
set_property -dict [list CONFIG.NUM_SI {2} CONFIG.NUM_MI {1}] [get_bd_cells sc_data]

# xlconstant for ap_start tied high — IP runs continuously while stream data
# flows. The previous BD did this too; we keep it because main.py is no longer
# allowed to patch the firmware (see README). The current bug is in the reset
# wiring below, not ap_start.
create_bd_cell -type ip -vlnv [latest_ip_vlnv xlconstant] ap_start_const
set_property -dict [list CONFIG.CONST_VAL {1} CONFIG.CONST_WIDTH {1}] \
    [get_bd_cells ap_start_const]

# ----------------------------------------------------------------------
# 3. Connections
# ----------------------------------------------------------------------
# Clock fanout
connect_bd_net [get_bd_pins ps7/FCLK_CLK0] \
    [get_bd_pins ps7/M_AXI_GP0_ACLK] \
    [get_bd_pins ps7/S_AXI_HP0_ACLK] \
    [get_bd_pins axi_dma_0/s_axi_lite_aclk] \
    [get_bd_pins axi_dma_0/m_axi_mm2s_aclk] \
    [get_bd_pins axi_dma_0/m_axi_s2mm_aclk] \
    [get_bd_pins myproject_0/ap_clk] \
    [get_bd_pins tlast_gen_0/aclk] \
    [get_bd_pins rst_0/slowest_sync_clk] \
    [get_bd_pins sc_ctrl/aclk] \
    [get_bd_pins sc_data/aclk]

# Reset chain — THIS IS THE FIX FOR THE CURRENT BLOCKER.
# Previous BD left axi_dma_0/axi_resetn dangling, holding the datapath in
# reset and producing DMASR=0x0 forever.
connect_bd_net [get_bd_pins ps7/FCLK_RESET0_N] [get_bd_pins rst_0/ext_reset_in]
connect_bd_net [get_bd_pins rst_0/peripheral_aresetn] \
    [get_bd_pins axi_dma_0/axi_resetn] \
    [get_bd_pins axi_dma_0/s_axi_lite_aresetn] \
    [get_bd_pins myproject_0/ap_rst_n] \
    [get_bd_pins tlast_gen_0/aresetn] \
    [get_bd_pins sc_ctrl/aresetn] \
    [get_bd_pins sc_data/aresetn]

# AXI Lite control: PS GP0 → SmartConnect → DMA
connect_bd_intf_net [get_bd_intf_pins ps7/M_AXI_GP0]    [get_bd_intf_pins sc_ctrl/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins sc_ctrl/M00_AXI]  [get_bd_intf_pins axi_dma_0/S_AXI_LITE]

# AXI Memory data: DMA MM2S/S2MM → SmartConnect → PS HP0
connect_bd_intf_net [get_bd_intf_pins axi_dma_0/M_AXI_MM2S] [get_bd_intf_pins sc_data/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins axi_dma_0/M_AXI_S2MM] [get_bd_intf_pins sc_data/S01_AXI]
connect_bd_intf_net [get_bd_intf_pins sc_data/M00_AXI]      [get_bd_intf_pins ps7/S_AXI_HP0]

# AXI Stream: DMA MM2S → myproject input
connect_bd_intf_net \
    [get_bd_intf_pins axi_dma_0/M_AXIS_MM2S] \
    [get_bd_intf_pins myproject_0/dense1_input]

# AXI Stream: myproject output → tlast_gen → DMA S2MM
connect_bd_intf_net \
    [get_bd_intf_pins myproject_0/layer7_out] \
    [get_bd_intf_pins tlast_gen_0/s_axis]
connect_bd_intf_net \
    [get_bd_intf_pins tlast_gen_0/m_axis] \
    [get_bd_intf_pins axi_dma_0/S_AXIS_S2MM]

# ap_start tied high
connect_bd_net \
    [get_bd_pins ap_start_const/dout] \
    [get_bd_pins myproject_0/ap_start]

# Address assignment + validation
assign_bd_address
validate_bd_design

save_bd_design

# ----------------------------------------------------------------------
# 4. HDL wrapper
# ----------------------------------------------------------------------
set bd_file [get_files design_1.bd]
generate_target all [get_files $bd_file]

make_wrapper -files [get_files $bd_file] -top -force
import_files -force -norecurse [file join $proj_dir ${proj_name}.gen sources_1 bd design_1 hdl design_1_wrapper.v]
set_property top design_1_wrapper [current_fileset]
update_compile_order -fileset sources_1

# ----------------------------------------------------------------------
# 5. Synth → Impl → Bitstream
# ----------------------------------------------------------------------
launch_runs synth_1 -jobs 4
wait_on_run  synth_1
if {[get_property PROGRESS [get_runs synth_1]] != "100%"} {
    puts "ERROR: synth_1 did not complete"
    exit 1
}

launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run  impl_1
if {[get_property PROGRESS [get_runs impl_1]] != "100%"} {
    puts "ERROR: impl_1 did not complete"
    exit 1
}

# ----------------------------------------------------------------------
# 6. Final messages
# ----------------------------------------------------------------------
puts "----------------------------------------"
puts "deploy.tcl: build complete for $config_name"
puts "  bit: [file join $proj_dir ${proj_name}.runs impl_1 design_1_wrapper.bit]"
puts "  hwh: [file join $proj_dir ${proj_name}.gen sources_1 bd design_1 hw_handoff design_1.hwh]"
puts "----------------------------------------"

close_project
