@echo off
title Swachh Nayan Live Sensor Studio
echo ==========================================================
echo        SWACHH NAYAN: LIVE SENSOR STUDIO & ACTUATION HUB
echo ==========================================================
echo.
echo Starting software and connecting to ESP32-S3 (COM5)...
python "%~dp0swachh_nayan_laptop_app.py"
pause
