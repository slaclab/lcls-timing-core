# Load RUCKUS environment and library
source -quiet $::env(RUCKUS_DIR)/vivado_proc.tcl

if { $::env(VIVADO_VERSION) >= 2023.1 } {
   loadSource -lib lcls_timing_core -dir "$::DIR_PATH/rtl"
   loadIpCore -path "$::DIR_PATH/coregen/TimingGth_extref.xci"
   loadIpCore -path "$::DIR_PATH/coregen/TimingGth_fixedlat.xci"

} else {
   puts "\n\nWARNING: $::DIR_PATH requires Vivado 2023.1 (or later)\n\n"
}
