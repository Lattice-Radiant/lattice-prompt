@echo off
rem The arch2code MCP server over stdio, serving the bundled cortex-a2c.
call "%~dp0_env.cmd"
"%LP_ROOT%\python\python.exe" -m arch2code_mcp %*
