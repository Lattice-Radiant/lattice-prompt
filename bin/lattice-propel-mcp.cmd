@echo off
rem The lattice-propel-mcp MCP server (cortex-mcp: Propel SoC sessions, IP facts, firmware,
rem validators, SoC manifest replay) over stdio, from the bundle's Python.
call "%~dp0_env.cmd"
"%LP_ROOT%\python\python.exe" -m lattice_prompt.server %*
