# <project>: makefile fragment included by every Makefile of the project.
#
# Where arch2code is, in this order:
#   1. A2C_ROOT in the environment: the lattice-prompt launchers (bin/a2c-make, bin/a2c-mcp)
#      set it to the bundle's components/cortex-a2c, a developer may set it to a checkout;
#   2. a git submodule at arch2code/ (git submodule add https://github.com/Lattice-Radiant/cortex-a2c.git arch2code)
#      when the project must pin the generator version it was designed with.
ifeq ($(origin A2C_ROOT), undefined)
  ifneq ($(wildcard $(REPO_ROOT)/arch2code/include/make/a2c-common.mk),)
    A2C_ROOT := $(REPO_ROOT)/arch2code
  else
    $(error A2C_ROOT is not set: run through the bundle's bin/a2c-make, export A2C_ROOT, or add arch2code as a submodule)
  endif
endif

# The project the arch2code targets act on. The trivial helloWorld values let `make db` run before
# the design exists; the design-from-intent skill replaces them at stage 5 (emission).
PROJECTNAME = @PROJECT@
TB_TOP_MODULE = @PROJECT@_tb
HDL_TOP_MODULE = @PROJECT@

# Project-local skills under rules/ and the AGENTS.append.md beside them are appended to
# AGENTS.md by `make agents-setup` (knowledge-base rules, server precedence, project notes).
EXTRA_A2C_RULES_DIRS := $(REPO_ROOT)/rules $(REPO_ROOT)/.kb/rules

# The knowledge base's reviewed skills for the designs this project names (design/intent.yaml):
# `make kb-skills` exports them into .kb/rules through the bundle's kb-skills launcher (or
# `cortex-kb skills` from a checkout when KB_SKILLS is set), and agents-setup deploys them into
# every tool's skills folder. They are also MCP prompts of the cortex-kb server.
KB_SKILLS ?= $(if $(LP_ROOT),$(LP_ROOT)/bin/kb-skills,cortex-kb skills)
-include $(A2C_ROOT)/pro/include/make/a2cPro.mk
include $(A2C_ROOT)/include/make/a2c-common.mk
