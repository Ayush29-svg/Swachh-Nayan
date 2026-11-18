@echo off
title Swachh Nayan Edge AI Live Studio
echo ================================================================
echo   SWACHH NAYAN: EDGE AI SENSOR MONITOR & TRASH DIVERSION STUDIO
echo ================================================================
echo.
echo Connecting to ESP32-S3 (COM5)...
echo Loading YOLOv5 model (best.onnx)...
echo Starting server on http://localhost:8088
echo.
python "%~dp0swachh_nayan_live_server.py"
pause
