@echo off
title SWACHH-NAYAN | Summit Presentation Dashboard Launcher
echo ==============================================================
echo   SWACHH-NAYAN: Edge-Vision Storm-Drain Trash Diverter
echo   Connecting to Rockchip RV1103 via RNDIS / ADB...
echo ==============================================================
C:\platform-tools\adb.exe connect 172.32.0.93:5555
C:\platform-tools\adb.exe -s 172.32.0.93:5555 forward tcp:8080 tcp:8080
C:\platform-tools\adb.exe -s 172.32.0.93:5555 forward tcp:8088 tcp:8088
echo Ports 8080 and 8088 successfully forwarded!
echo Opening browser at http://localhost:8080 ...
start http://localhost:8080
echo Dashboard active. Keep this window minimized during the demonstration.
pause
