@echo off
setlocal
title Mikasa Graphite
cd /d "%~dp0"
cmd /k "uv run mikasa --tui %*"
