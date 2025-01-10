# Load RUCKUS environment and library
source -quiet $::env(RUCKUS_DIR)/vivado_proc.tcl

# Check for Vivado version 2019.1 (or later)
if { [VersionCheck 2019.1 ] < 0 } {
   exit -1
}

# Check for submodule tagging
if { [info exists ::env(OVERRIDE_SUBMODULE_LOCKS)] != 1 || $::env(OVERRIDE_SUBMODULE_LOCKS) == 0 } {
   if { [SubmoduleCheck {ruckus} {2.1.2}  ] < 0 } {exit -1}
   if { [SubmoduleCheck {surf}   {2.53.0} ] < 0 } {exit -1}
} else {
   puts "\n\n*********************************************************"
   puts "OVERRIDE_SUBMODULE_LOCKS != 0"
   puts "Ignoring the submodule locks in lcls-timing-core/ruckus.tcl"
   puts "*********************************************************\n\n"
}

# Load ruckus files
loadRuckusTcl "$::DIR_PATH/LCLS-I"  "quiet"
loadRuckusTcl "$::DIR_PATH/LCLS-II" "quiet"

