@echo off
rem The lattice-radiant MCP server (cortex-bridge: Radiant projects and flows, timing closure,
rem constraints lint, programming, Reveal through the revealai plugin) over stdio, from the
rem bundle's Python. components\cortex-bridge\src is on the module path for the timing-closure
rem package the server merges when TIMING_CLOSURE_MERGE_ENABLED is set (the defaults below
rem enable the internal, full-tier tool set; set the variables before calling to change them).
call "%~dp0_env.cmd"
set "PYTHONPATH=%LP_ROOT%\components\cortex-bridge\src;%PYTHONPATH%"
if not defined TIMING_CLOSURE_MERGE_ENABLED set "TIMING_CLOSURE_MERGE_ENABLED=1"
if not defined CORTEX_TIMING_CLOSURE_MCP_SURFACE set "CORTEX_TIMING_CLOSURE_MCP_SURFACE=internal"
if not defined CORTEX_TIMING_CLOSURE_MCP_RELEASE_TIER set "CORTEX_TIMING_CLOSURE_MCP_RELEASE_TIER=full"
if not defined CORTEX_TIMING_CLOSURE_MCP_ENABLED_TOOLS set "CORTEX_TIMING_CLOSURE_MCP_ENABLED_TOOLS=perceive_timing,list_levers,check_plan,search_radiant_docs,propose_levers,get_capability_probe_kit,list_toolchain_capabilities,get_primitive_instantiation_template,list_primitive_topologies,lint_rtl,lint_constraints,verify_non_regression,bind_lever"
"%LP_ROOT%\python\python.exe" -m radiant_mcp %*
