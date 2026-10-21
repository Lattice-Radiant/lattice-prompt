@echo off
rem Design skills of the bundled knowledge base (cortex-kb skills ...):
rem   kb-skills list [--all]                       reviewed skills (all with --all)
rem   kb-skills install --all | --select d/s,...   copy into %USERPROFILE%\.claude\skills
rem   kb-skills uninstall                          remove what install wrote
call "%~dp0_env.cmd"
"%LP_ROOT%\python\python.exe" -c "from kbtools.cli import main; main()" --repo "%LP_ROOT%\components\cortex-kb" skills %*
