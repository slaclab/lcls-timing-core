# Load RUCKUS library
source -quiet $::env(RUCKUS_DIR)/vivado_proc.tcl

# Load Source Code
loadSource -lib lcls_timing_core -dir "$::DIR_PATH/evr/"
