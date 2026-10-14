@echo off
title SSK - Autonomous 5-Minute Highlight Reel
cd /d "%~dp0"
echo ==============================================================================
echo  SSK Sovereign NLE Director -- Autonomous Highlight Reel Assembly
echo ==============================================================================
python windows\ssk_agent.py --prompt "Assemble a 5 minute high-energy highlight reel and export" --filelist my_clips.txt --output "%USERPROFILE%\Videos\Bae_Highlight_Reel_5Min.mp4"
echo.
pause
