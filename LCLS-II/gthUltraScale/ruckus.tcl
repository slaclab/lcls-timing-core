# Load RUCKUS environment and library
source $::env(RUCKUS_PROC_TCL)

if { $::env(VIVADO_VERSION) >= 2016.4 } {

   loadSource -lib lcls_timing_core -dir "$::DIR_PATH/rtl"

   if { [info exists ::env(LCLS_TIMING_GTH_XCI)] != 0 && $::env(LCLS_TIMING_GTH_XCI) == 1 } {
       loadIpCore -path "$::DIR_PATH/coregen/2016.4/TimingGth_extref.xci"
       loadIpCore -path "$::DIR_PATH/coregen/2016.4/TimingGth_fixedlat.xci"
   } else {
       loadSource -lib lcls_timing_core   -path "$::DIR_PATH/coregen/2016.4/TimingGth_extref.dcp"
       loadSource -lib lcls_timing_core   -path "$::DIR_PATH/coregen/2016.4/TimingGth_fixedlat.dcp"
   }

} else {
   puts "\n\nWARNING: $::DIR_PATH requires Vivado 2016.4 (or later)\n\n"
}
