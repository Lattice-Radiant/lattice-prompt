@echo off
rem A command prompt with the bundle's Python, git and tools first on PATH.
call "%~dp0_env.cmd"
echo lattice-prompt: python, git and make from %LP_ROOT%; A2C_ROOT=%A2C_ROOT%
cmd /k
