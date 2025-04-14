# Load RUCKUS environment and library
source $::env(RUCKUS_PROC_TCL)

loadSource -lib lcls_timing_core -dir "$::DIR_PATH/rtl"

###########################################################################
# Standard 317 MHz reference OSC
###########################################################################
if { [info exists ::env(TIMING_246MHz)] != 1 || $::env(TIMING_246MHz) == 0 } {
   set path "$::DIR_PATH/coregen"

   # Check the Vivado Version
   if { $::env(VIVADO_VERSION) >= 2021.1} {

      # Check if loading the XCI file
      if { [info exists ::env(LCLS_TIMING_GTY_XCI)] != 0 && $::env(LCLS_TIMING_GTY_XCI) == 1 } {
         loadIpCore -path "${path}/TimingGty_extref.xci"
         loadIpCore -path "${path}/TimingGty_fixedlat.xci"
         loadIpCore -path "${path}/TimingGty_fixedlat_Lcls1Only.xci"
         puts "Loading XCI files for LCLS Timing"

      # Else loading the .DCP file
      } else {
         loadSource -lib lcls_timing_core -path "${path}/TimingGty_extref.dcp"
         loadSource -lib lcls_timing_core -path "${path}/TimingGty_fixedlat.dcp"
         loadSource -lib lcls_timing_core -path "${path}/TimingGty_fixedlat_Lcls1Only.dcp"
      }

   } else {
      puts "\n\nWARNING: $::DIR_PATH requires Vivado 2021.1 (or later)\n\n"
   }

###########################################################################
# Standard 245.76 MHz reference OSC
###########################################################################
} else {
   set path "$::DIR_PATH/coregen/smurf"

   # Check the Vivado Version
   if { $::env(VIVADO_VERSION) >= 2018.2} {

      # Check if loading the XCI file
      if { [info exists ::env(LCLS_TIMING_GTY_XCI)] != 0 && $::env(LCLS_TIMING_GTY_XCI) == 1 } {
         loadIpCore -path "${path}/TimingGty_extref.xci"
         loadIpCore -path "${path}/TimingGty_fixedlat.xci"
         puts "Loading XCI files for LCLS Timing"

      # Else loading the .DCP file
      } else {
         loadSource -lib lcls_timing_core -path "${path}/TimingGty_extref.dcp"
         loadSource -lib lcls_timing_core -path "${path}/TimingGty_fixedlat.dcp"
      }

   } else {
      puts "\n\nWARNING: $::DIR_PATH requires Vivado 2018.2 (or later)\n\n"
   }

}
