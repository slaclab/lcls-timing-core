# CI-only top manifest for ruckus GHDL mode (PROJ_DIR, see the top-level Makefile).
# No production ruckus.tcl references this file, so Vivado builds never see it.
source $::env(RUCKUS_PROC_TCL)

# Dependency first: library surf
loadRuckusTcl "$::env(MODULES)/surf"

# Production manifest, unmodified: library lcls_timing_core (LCLS-I and LCLS-II core + evr)
loadRuckusTcl "$::env(TOP_DIR)"

# CI-only stub so "library UNISIM" in CtrControl.vhd resolves under GHDL
loadSource -lib unisim -path "$::DIR_PATH/unisim/vcomponents.vhd"
