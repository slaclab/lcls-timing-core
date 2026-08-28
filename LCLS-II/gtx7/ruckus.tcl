# Load RUCKUS environment and library
source $::env(RUCKUS_PROC_TCL)

# Check for submodule tagging for https://github.com/slaclab/surf/pull/1475
if { [info exists ::env(OVERRIDE_SUBMODULE_LOCKS)] != 1 || $::env(OVERRIDE_SUBMODULE_LOCKS) == 0 } {
   if { [SubmoduleCheck {surf}   {2.74.0] < 0 } {exit -1}
} else {
   puts "\n\n*********************************************************"
   puts "OVERRIDE_SUBMODULE_LOCKS != 0"
   puts "Ignoring the submodule locks in lcls-timing-core/ruckus.tcl"
   puts "*********************************************************\n\n"
}

loadSource -lib lcls_timing_core -dir "$::DIR_PATH/rtl"
