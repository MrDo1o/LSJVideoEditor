@echo off
title SSK - Sovereign NLE Director Agent
setlocal
cd /d "%~dp0\windows"
python ssk_agent.py %*
pause
