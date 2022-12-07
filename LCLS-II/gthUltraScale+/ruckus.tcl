# Load RUCKUS environment and library
source -quiet $::env(RUCKUS_DIR)/vivado_proc.tcl

if { $::env(VIVADO_VERSION) >= 2021.2 } {

   loadSource -lib lcls_timing_core -dir "$::DIR_PATH/rtl"

   loadSource -lib lcls_timing_core   -path "$::DIR_PATH/coregen/TimingGth_extref.dcp"
   # loadIpCore -path "$::DIR_PATH/coregen/TimingGth_extref.xci"

   loadSource -lib lcls_timing_core   -path "$::DIR_PATH/coregen/TimingGth_fixedlat.dcp"
   # loadIpCore -path "$::DIR_PATH/coregen/TimingGth_fixedlat.xci"

} else {
   puts "\n\nWARNING: $::DIR_PATH requires Vivado 2021.2 (or later)\n\n"
}
