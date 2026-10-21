# <project>: an arch2code project of the integrated FPGA design flow.
#
#   make agents-setup   deploy the arch2code skills (and Pro's run-tandem when present) into
#                       .claude/skills etc. and write AGENTS.md / CLAUDE.md
#                       (arch2code's template + this project's AGENTS.append.md)
#   make preflight      which arch2code this project builds with; the rest of stage 0 runs
#                       through the MCP servers (kb_status, toolchain_detect, ...)
#   make db / gen / ... the arch2code targets once the project YAML exists (stage 5)
#
# Run it as `bin/a2c-make` of the lattice-prompt bundle (sets PATH, PYTHON and A2C_ROOT),
# or as plain `make` with a development checkout: see include/make/shared.mk.
REPO_ROOT = $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)
include $(REPO_ROOT)/include/make/shared.mk

.PHONY: preflight
preflight:
	@echo "arch2code: $(A2C_ROOT) ($$(git -C $(A2C_ROOT) describe --always --dirty 2>/dev/null || echo not a git checkout))"
	@echo "Pro layer: $$( [ -d $(A2C_ROOT)/pro ] && echo present || echo absent )"
	@echo "stage 0 continues with: kb_status (cortex-kb), toolchain_detect / questa_detect / list_projects (arch2code), lattice://health (lattice-cortex), detect_radiant_installations / check_environment (lattice-radiant-mcp)"

.PHONY: clean
clean::
	rm -rf $(A2C_SQLDB_DOTFILE) $(A2C_SQLDB_FILE) $(GEN_BUILD_DIR)
