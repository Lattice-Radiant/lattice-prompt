@echo off
rem The lattice-radiant-mcp MCP server (cortex-bridge: Radiant projects, builds, timing,
rem IP generation, cable listing and programming) over stdio, from the bundle's Python.
rem The Radiant installation is found as the server documents it (RADIANT_EXE, its
rem configuration file, then the newest install under the default roots).
call "%~dp0_env.cmd"
rem The timing-closure merge needs packages the bundle does not ship; keep it off even
rem when the user's environment sets it.
set "TIMING_CLOSURE_MERGE_ENABLED="
"%LP_ROOT%\python\python.exe" -m radiant_mcp %*
