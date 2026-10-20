#!/bin/sh
# Registers the bundled MCP servers with Claude Code and Claude Desktop.
#   ./install.sh              register
#   ./install.sh --uninstall  remove the entries
#   ./install.sh --authoring  register cortex-kb with its authoring tools (Claude can add designs)
LP_ROOT=$(cd "$(dirname "$0")" && pwd)
. "$LP_ROOT/bin/_env.sh"
exec "$LP_ROOT/python/bin/python3" "$LP_ROOT/install.py" "$@"
