@echo off
rem GNU make with the bundle's Python, git and tools first on PATH, for the
rem cortex-a2c make flow (make -C <project> db|gen|newmodule, make -C rundir run).
call "%~dp0_env.cmd"
make %*
