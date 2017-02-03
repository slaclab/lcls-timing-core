# Load RUCKUS environment and library
source -quiet $::env(RUCKUS_DIR)/vivado_proc.tcl

# Load .XCI files
# loadIpCore -dir  "$::DIR_PATH/coregen/TimingGth.xci"
# loadIpCore -dir  "$::DIR_PATH/coregen/TimingGth_clksel.xci"
# loadIpCore -dir  "$::DIR_PATH/coregen/TimingGth_extref.xci"
# loadIpCore -dir  "$::DIR_PATH/coregen/TimingGth_fixedlat.xci"
# loadIpCore -dir  "$::DIR_PATH/coregen/TimingGth_polarity.xci"

# Load .DCP files
# loadSource -path "$::DIR_PATH/coregen/TimingGth.dcp"
# loadSource -path "$::DIR_PATH/coregen/TimingGth_clksel.dcp"
loadSource -path "$::DIR_PATH/coregen/TimingGth_extref.dcp"
loadSource -path "$::DIR_PATH/coregen/TimingGth_fixedlat.dcp"
# loadSource -path "$::DIR_PATH/coregen/TimingGth_polarity.dcp"
