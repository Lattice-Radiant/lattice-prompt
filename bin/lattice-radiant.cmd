@echo off
rem The lattice-radiant MCP server (cortex-bridge: Radiant projects and flows, constraints lint,
rem programming, Reveal through the revealai plugin) over stdio, from the bundle's Python.
rem The timing-closure tools (perceive_timing, propose_levers, ...) come from the separately
rem installed cortex-framework and cortex-agent-impl packages, which this bundle does not carry;
rem with them installed into the bundle's Python, set TIMING_CLOSURE_MERGE_ENABLED=1 before
rem calling and the server merges them (components\cortex-bridge\src is on the module path for
rem the merge package; the defaults below select the internal, full-tier tool set).
call "%~dp0_env.cmd"
set "PYTHONPATH=%LP_ROOT%\components\cortex-bridge\src;%PYTHONPATH%"
if not defined CORTEX_TIMING_CLOSURE_MCP_SURFACE set "CORTEX_TIMING_CLOSURE_MCP_SURFACE=internal"
if not defined CORTEX_TIMING_CLOSURE_MCP_RELEASE_TIER set "CORTEX_TIMING_CLOSURE_MCP_RELEASE_TIER=full"
if not defined CORTEX_TIMING_CLOSURE_MCP_ENABLED_TOOLS set "CORTEX_TIMING_CLOSURE_MCP_ENABLED_TOOLS=perceive_timing,list_levers,check_plan,search_radiant_docs,propose_levers,get_capability_probe_kit,list_toolchain_capabilities,get_primitive_instantiation_template,list_primitive_topologies,lint_rtl,lint_constraints,verify_non_regression,bind_lever"
"%LP_ROOT%\python\python.exe" -m radiant_mcp %*
