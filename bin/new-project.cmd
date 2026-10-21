@echo off
rem Create an arch2code project of the integrated flow from the bundle's template:
rem   new-project <directory> [--name <project>] [--submodule]
rem Then: a2c-make agents-setup in the project; copy .mcp.json.example to .mcp.json.
call "%~dp0_env.cmd"
"%LP_ROOT%\python\python.exe" "%LP_ROOT%\templates\new_project.py" %*
