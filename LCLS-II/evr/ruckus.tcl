# Load RUCKUS library
source $::env(RUCKUS_PROC_TCL)

# Load Source Code
loadSource -lib lcls_timing_core -dir  "$::DIR_PATH/rtl/"

# Load Simulation
loadSource -lib lcls_timing_core -sim_only -dir "$::DIR_PATH/tb/"
