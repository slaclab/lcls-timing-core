# Load RUCKUS environment and library
source -quiet $::env(RUCKUS_DIR)/vivado_proc.tcl

# Check for Vivado version 2016.4 (or later)
if { [VersionCheck 2016.4 ] < 0 } {
   exit -1
}

if { [SubmoduleCheck {ruckus} {1.5.12} ] < 0 } {exit -1}
if { [SubmoduleCheck {surf}   {1.7.1}  ] < 0 } {exit -1}

# Load ruckus files
loadRuckusTcl "$::DIR_PATH/LCLS-I"  "quiet"
loadRuckusTcl "$::DIR_PATH/LCLS-II" "quiet"

# Check for submodule tagging
puts "*********************************************************"
if { [info exists ::env(TIMING_EXT_PKG)] != 1 || $::env(TIMING_EXT_PKG) == 0 } {
   puts "TIMING_EXT_PKG = 0"
   puts "Using default TimingExtnPkg.vhd in lcls-timing-core"
   loadSource -path "$::DIR_PATH/LCLS-II/core/rtl/default/TimingExtnPkg.vhd"
} else {
   puts "TIMING_EXT_PKG = 1"
   puts "Using application's defined TimingExtnPkg.vhd"
}
puts "*********************************************************"
