# Load RUCKUS environment and library
source -quiet $::env(RUCKUS_DIR)/vivado_proc.tcl

loadSource -lib lcls_timing_core -dir "$::DIR_PATH/rtl"
