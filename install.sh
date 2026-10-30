#!/bin/sh
# Registers the bundled MCP servers (lattice-arch2code-mcp, lattice-knowledge-db,
# lattice-propel-mcp, lattice-radiant-mcp) with Claude Code and Claude Desktop, and
# removes the old entries of the same servers (arch2code, cortex-kb, lattice-cortex,
# lattice-prompt, radiant and any other key running them).
#   ./install.sh              register
#   ./install.sh --uninstall  remove the entries (new and old names)
#   ./install.sh --read-only  register lattice-knowledge-db without its authoring tools
LP_ROOT=$(cd "$(dirname "$0")" && pwd)
. "$LP_ROOT/bin/_env.sh"
exec "$LP_ROOT/python/bin/python3" "$LP_ROOT/install.py" "$@"
