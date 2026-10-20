#!/bin/sh
# Shared environment of the lattice-prompt launchers (Linux). Sourced, not
# executed. LP_ROOT is the bundle root: the caller may set it; otherwise it is
# the parent of the directory holding the calling script (bin/). Nothing here
# depends on where the bundle lives.
#
# Unlike the Windows bundle, git and GNU make are not bundled: every Linux
# distribution provides them (packages git, make) and the native simulation
# flow needs the distribution's C++ toolchain anyway.
LP_ROOT=${LP_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
export LP_ROOT
export PATH="$LP_ROOT/python/bin:$PATH"
export A2C_ROOT="$LP_ROOT/components/cortex-a2c"
export PYTHON="$LP_ROOT/python/bin/python3"
: "${CORTEX_KB_CACHE:=${XDG_CACHE_HOME:-$HOME/.cache}/lattice-prompt/kb-cache}"
export CORTEX_KB_CACHE
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
