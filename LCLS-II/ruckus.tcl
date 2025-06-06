# Load RUCKUS library
source $::env(RUCKUS_PROC_TCL)

# Load Source Code
loadRuckusTcl "$::DIR_PATH/core"
loadRuckusTcl "$::DIR_PATH/evr"

# Get the family type
set family [getFpgaFamily]

if { ${family} eq {artix7} } {
   loadRuckusTcl "$::DIR_PATH/gtp7"
}

if { ${family} == "kintex7" } {
   loadRuckusTcl "$::DIR_PATH/gtx7"
}

if { ${family} == "kintexu" } {
   loadRuckusTcl "$::DIR_PATH/gthUltraScale"
}

if { ${family} eq {kintexuplus} ||
     ${family} eq {virtexuplus} ||
     ${family} eq {virtexuplusHBM} ||
     ${family} eq {zynquplus} ||
     ${family} eq {zynquplusRFSOC} ||
     ${family} eq {qzynquplusRFSOC} } {
   loadRuckusTcl "$::DIR_PATH/gtyUltraScale+"
   loadRuckusTcl "$::DIR_PATH/gthUltraScale+"
}
