# Load RUCKUS environment and library
source -quiet $::env(RUCKUS_DIR)/vivado_proc.tcl

loadSource -lib lcls_timing_core -dir "$::DIR_PATH/rtl"

# Standard 317 MHz reference OSC
if { [info exists ::env(TIMING_246MHz)] != 1 || $::env(TIMING_246MHz) == 0 } {
   set path "$::DIR_PATH/coregen"

# Standard 245.76 MHz reference OSC
} else {
   set path "$::DIR_PATH/coregen/smurf"
}

if { $::env(VIVADO_VERSION) >= 2021.1 && [info exists ::env(TIMING_246MHz)] != 1} {

   if { [info exists ::env(LCLS_TIMING_XCI)] != 0 && $::env(LCLS_TIMING_XCI) == 1 } {
       loadIpCore -path "${path}/TimingGty_extref.xci"
       loadIpCore -path "${path}/TimingGty_fixedlat.xci"
       puts "Loading XCI files for LCLS Timing"
   } else {
       loadSource -lib lcls_timing_core   -path "${path}/TimingGty_extref.dcp"
       loadSource -lib lcls_timing_core   -path "${path}/TimingGty_fixedlat.dcp"       
   }      


} elseif { $::env(VIVADO_VERSION) >= 2020.2 && [info exists ::env(TIMING_246MHz)] == 1 } {

    if { [info exists ::env(LCLS_TIMING_XCI)] != 0 && $::env(LCLS_TIMING_XCI) == 1 } {
	loadIpCore -path "${path}/TimingGty_extref.xci"
	loadIpCore -path "${path}/TimingGty_fixedlat.xci"       
    } else {
	loadSource -lib lcls_timing_core   -path "${path}/TimingGty_extref.dcp"
	loadSource -lib lcls_timing_core   -path "${path}/TimingGty_fixedlat.dcp"       
    }      

} else {
   puts "\n\nWARNING: $::DIR_PATH requires Vivado 2021.1 (or later)\n\n"
}
