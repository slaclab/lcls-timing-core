#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

# Define default target
target: import

# MODULES is the directory holding the surf/ and ruckus/ clones
ifndef MODULES
export MODULES = $(abspath $(CURDIR))
endif

export RUCKUS_DIR = $(MODULES)/ruckus
export TOP_DIR    = $(abspath $(CURDIR))
export PROJ_DIR   = $(TOP_DIR)/tests/ghdl
export OUT_DIR    = $(TOP_DIR)/build

# surf and ruckus are plain clones, not submodules of this repo
export OVERRIDE_SUBMODULE_LOCKS = 1

ifndef GHDL_CMD
export GHDL_CMD = ghdl
endif

export GHDL_BASE_FLAGS = \
	--workdir=$(OUT_DIR) \
	--std=08 \
	--ieee=synopsys \
	-frelaxed-rules \
	-fexplicit

export GHDL_OPTIONAL_WARNINGS = elaboration hide specs shared
export GHDL_SUPPORTED_WARNING_NAMES := $(shell $(GHDL_CMD) --help-warnings 2>/dev/null | awk '/^[[:space:]]*-W/ {name=$$1; sub(/^-W/, "", name); sub(/\*$$/, "", name); if (name != "all") print name}')
export GHDL_WARNING_FLAGS := $(strip $(foreach warn,$(GHDL_OPTIONAL_WARNINGS),$(if $(filter $(warn),$(GHDL_SUPPORTED_WARNING_NAMES)),-Wno-$(warn))))
export GHDLFLAGS = $(GHDL_BASE_FLAGS) $(GHDL_WARNING_FLAGS)

# Stop early, with the clone command, when a dependency is missing
ifeq ($(wildcard $(MODULES)/ruckus/system_ghdl.mk),)
$(error ruckus not found at $(MODULES)/ruckus: git clone --depth 1 -b main https://github.com/slaclab/ruckus $(MODULES)/ruckus)
endif
ifeq ($(wildcard $(MODULES)/surf/ruckus.tcl),)
$(error surf not found at $(MODULES)/surf: git clone --depth 1 -b main https://github.com/slaclab/surf $(MODULES)/surf)
endif

# Load the common makefile library
include $(MODULES)/ruckus/system_ghdl.mk
