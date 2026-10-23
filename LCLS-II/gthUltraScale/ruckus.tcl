# Load RUCKUS environment and library
source $::env(RUCKUS_PROC_TCL)

if { $::env(VIVADO_VERSION) >= 2016.4 } {

   loadSource -lib lcls_timing_core -dir "$::DIR_PATH/rtl"

   if { $::env(VIVADO_VERSION) >= 2025.1 } {
      set coreDir "$::DIR_PATH/coregen/2025.1"
   } else {
      set coreDir "$::DIR_PATH/coregen/2016.4"
   }

   if { [info exists ::env(LCLS_TIMING_GTH_XCI)] != 0 && $::env(LCLS_TIMING_GTH_XCI) == 1 } {
       loadIpCore -path "${coreDir}/TimingGth_extref.xci"
       loadIpCore -path "${coreDir}/TimingGth_fixedlat.xci"
   } else {
       loadSource -lib lcls_timing_core   -path "${coreDir}/TimingGth_extref.dcp"
       loadSource -lib lcls_timing_core   -path "${coreDir}/TimingGth_fixedlat.dcp"
       if { $::env(VIVADO_VERSION) >= 2025.1 } {
          loadConstraints -path "${coreDir}/TimingGth_fixedlat.xdc"
          set_property PROCESSING_ORDER {EARLY}              [get_files {TimingGth_fixedlat.xdc}]
          set_property SCOPED_TO_REF    {TimingGth_fixedlat} [get_files {TimingGth_fixedlat.xdc}]
          set_property SCOPED_TO_CELLS  {inst}               [get_files {TimingGth_fixedlat.xdc}]
       }
   }

} else {
   puts "\n\nWARNING: $::DIR_PATH requires Vivado 2016.4 (or later)\n\n"
}
