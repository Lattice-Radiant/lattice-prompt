@echo off
rem Design skills of the bundled knowledge base (cortex-kb skills ...):
rem   kb-skills list [--all]                       reviewed skills (all with --all)
rem   kb-skills export-dir DIR --project .         the project's skills as a rules directory
rem                                                for a2c-make agents-setup (new-project wires it)
rem   kb-skills install --all | --select d/s,...   fallback: copy into %USERPROFILE%\.claude\skills
rem   kb-skills uninstall                          remove what install wrote
rem Every reviewed skill is also an MCP prompt of the lattice-knowledge-db server.
call "%~dp0_env.cmd"
"%LP_ROOT%\python\python.exe" -c "from kbtools.cli import main; main()" --repo "%LP_ROOT%\components\cortex-kb" skills %*
