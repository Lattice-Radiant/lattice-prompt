@echo off
rem The lattice-arch2code-mcp MCP server (arch2code) over stdio, serving the bundled cortex-a2c.
call "%~dp0_env.cmd"
"%LP_ROOT%\python\python.exe" -m arch2code_mcp %*
