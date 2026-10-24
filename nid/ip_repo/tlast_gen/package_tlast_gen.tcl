# package_tlast_gen.tcl
#
# Run once on arush's laptop (or any time tlast_gen.v changes) to package
# tlast_gen as a Vivado IP. Output is consumed by deploy.tcl via ip_repo path.
#
# Usage:
#   cd ~/DD_proj_new_env/ip_repo/tlast_gen
#   vivado -mode batch -source package_tlast_gen.tcl

set ip_dir [file dirname [info script]]
set work_dir [file join $ip_dir _packaging]
file delete -force $work_dir
file mkdir $work_dir

create_project tlast_gen_pkg $work_dir -part xc7z020clg400-1 -force
add_files -norecurse [file join $ip_dir src tlast_gen.v]

ipx::package_project -root_dir $ip_dir \
    -vendor user.org \
    -library user \
    -taxonomy /UserIP \
    -import_files \
    -force

# Mark the s_axis / m_axis bundles as AXI4-Stream interfaces (Vivado infers
# this from naming, but make it explicit so it's stable across versions).
ipx::infer_bus_interfaces xilinx.com:interface:axis_rtl:1.0 [ipx::current_core]

# Associate clock with both stream interfaces and the reset
ipx::associate_bus_interfaces -busif s_axis -clock aclk [ipx::current_core]
ipx::associate_bus_interfaces -busif m_axis -clock aclk [ipx::current_core]

set_property core_revision 1 [ipx::current_core]
ipx::create_xgui_files [ipx::current_core]
ipx::update_checksums [ipx::current_core]
ipx::save_core [ipx::current_core]

close_project
puts "tlast_gen IP packaged at $ip_dir"
