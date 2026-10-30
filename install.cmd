@echo off
rem Registers the bundled MCP servers (lattice-arch2code-mcp, lattice-knowledge-db,
rem lattice-propel-mcp, lattice-radiant-mcp) with Claude Code and Claude Desktop, and
rem removes the old entries of the same servers (arch2code, cortex-kb, lattice-cortex,
rem lattice-prompt, radiant and any other key running them).
rem   install.cmd              register
rem   install.cmd --uninstall  remove the entries (new and old names)
rem   install.cmd --read-only  register lattice-knowledge-db without its authoring tools
call "%~dp0bin\_env.cmd"
"%LP_ROOT%\python\python.exe" "%LP_ROOT%\install.py" %*
