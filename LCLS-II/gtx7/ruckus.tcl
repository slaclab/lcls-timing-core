# Load RUCKUS environment and library
source $::env(RUCKUS_PROC_TCL)

# Check for submodule tagging for https://github.com/slaclab/surf/pull/1475
if { [SubmoduleCheck {surf} {2.74.0}] < 0 } {exit -1}

loadSource -lib lcls_timing_core -dir "$::DIR_PATH/rtl"
