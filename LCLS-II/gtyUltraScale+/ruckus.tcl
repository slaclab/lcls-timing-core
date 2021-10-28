# Load RUCKUS environment and library
source -quiet $::env(RUCKUS_DIR)/vivado_proc.tcl

if { $::env(VIVADO_VERSION) >= 2021.1 } {

   loadSource -lib lcls_timing_core -dir "$::DIR_PATH/rtl"

   # Standard 317 MHz reference OSC
   if { [info exists ::env(TIMING_246MHz)] != 1 || $::env(TIMING_246MHz) == 0 } {
      set path "$::DIR_PATH/coregen"

   # Standard 245.76 MHz reference OSC
   } else {
      set path "$::DIR_PATH/coregen/smurf"
   }

   loadSource -lib lcls_timing_core   -path "${path}/TimingGty_extref.dcp"
   # loadIpCore -path "${path}/TimingGty_extref.xci"

   loadSource -lib lcls_timing_core   -path "${path}/TimingGty_fixedlat.dcp"
   # loadIpCore -path "${path}/TimingGty_fixedlat.xci"

} else {
   puts "\n\nWARNING: $::DIR_PATH requires Vivado 2021.1 (or later)\n\n"
}
