# Load RUCKUS environment and library
source -quiet $::env(RUCKUS_DIR)/vivado_proc.tcl

# Load ruckus files
loadRuckusTcl "$::DIR_PATH/LCLS-I"
loadRuckusTcl "$::DIR_PATH/LCLS-II"
