REPO_ROOT = $(shell git rev-parse --show-toplevel 2>/dev/null || (cd .. && pwd))
include $(REPO_ROOT)/include/make/shared.mk

# External dependencies in compilation
EXTRA_CPP_SRC      =
EXTRA_CPP_INCLUDES =
EXTRA_LD_FLAGS     +=

# Generated files named '*Includes*.cpp' compile at -O3.
EXTRA_O3_CPP_SRC   = $(filter %Includes.cpp %IncludesFW.cpp, $(SC_GEN_FILES))

include $(A2C_ROOT)/include/make/a2c-systemc.mk

run: $(BIN_DIR)/$(BIN)
ifndef VL_DUT
	$(BIN_DIR)/$(BIN) $(TB_TOP_MODULE)
else
	$(BIN_DIR)/$(BIN) $(TB_TOP_MODULE) --vlInst $(HDL_TOP_MODULE)
endif
