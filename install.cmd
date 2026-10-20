@echo off
rem Registers the bundled MCP servers with Claude Code and Claude Desktop.
rem   install.cmd              register
rem   install.cmd --uninstall  remove the entries
call "%~dp0bin\_env.cmd"
"%LP_ROOT%\python\python.exe" "%LP_ROOT%\install.py" %*
