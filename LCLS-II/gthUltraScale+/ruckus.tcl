# Load RUCKUS environment and library
source -quiet $::env(RUCKUS_DIR)/vivado_proc.tcl

loadSource -dir "$::DIR_PATH/rtl"

loadSource   -path "$::DIR_PATH/coregen/TimingGth_extref.dcp"
# loadIpCore -path "$::DIR_PATH/coregen/TimingGth_extref.xci"

loadSource   -path "$::DIR_PATH/coregen/TimingGth_fixedlat.dcp"
# loadIpCore -path "$::DIR_PATH/coregen/TimingGth_fixedlat.xci"
