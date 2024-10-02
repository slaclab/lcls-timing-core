# Load RUCKUS environment and library
source -quiet $::env(RUCKUS_DIR)/vivado_proc.tcl

if { $::env(VIVADO_VERSION) >= 2022.2} {
   loadSource -lib lcls_timing_core -dir "$::DIR_PATH/rtl"

   if { [info exists ::env(LCLS_TIMING_XCI)] != 0 && $::env(LCLS_TIMING_XCI) == 1 } {
       loadIpCore -path "$::DIR_PATH/coregen/TimingGth_extref.xci"
       loadIpCore -path "$::DIR_PATH/coregen/TimingGth_fixedlat.xci"
   } else {
       loadSource -lib lcls_timing_core   -path "$::DIR_PATH/coregen/TimingGth_extref.dcp"
       loadSource -lib lcls_timing_core   -path "$::DIR_PATH/coregen/TimingGth_fixedlat.dcp"
   }
} else {
   puts "\n\nWARNING: $::DIR_PATH requires Vivado 2022.2 (or later)\n\n"
}
