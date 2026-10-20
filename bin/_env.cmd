@echo off
rem Shared environment of the lattice-prompt launchers. The bundle root is the
rem parent of this directory; nothing here depends on where the bundle lives.
set "LP_ROOT=%~dp0.."
for %%I in ("%LP_ROOT%") do set "LP_ROOT=%%~fI"
set "PATH=%LP_ROOT%\python;%LP_ROOT%\python\Scripts;%LP_ROOT%\git\cmd;%LP_ROOT%\git\usr\bin;%LP_ROOT%\tools;%PATH%"
set "A2C_ROOT=%LP_ROOT%\components\cortex-a2c"
set "PYTHON=%LP_ROOT%\python\python.exe"
if not defined CORTEX_KB_CACHE set "CORTEX_KB_CACHE=%LOCALAPPDATA%\lattice-prompt\kb-cache"
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
