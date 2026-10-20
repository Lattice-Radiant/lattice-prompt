@echo off
rem The cortex-kb MCP server over stdio, serving the bundled knowledge base.
rem The session database and the pinned-source checkouts live under
rem CORTEX_KB_CACHE (default %LOCALAPPDATA%\lattice-prompt\kb-cache).
rem --skip-unresolved keeps the server starting offline: designs whose linked
rem sources are not in the cache are marked unavailable instead of failing.
call "%~dp0_env.cmd"
if not exist "%CORTEX_KB_CACHE%" mkdir "%CORTEX_KB_CACHE%"
"%LP_ROOT%\python\python.exe" -c "from kbtools.cli import main; main()" serve --repo "%LP_ROOT%\components\cortex-kb" --skip-unresolved %*
