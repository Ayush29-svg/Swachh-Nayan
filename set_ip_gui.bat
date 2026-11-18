@echo off
title Luckfox Pico RNDIS IP Configurator
color 0A
echo ====================================================================
echo  Swachh Nayan — Luckfox Pico USB Network Adapter Configurator
echo ====================================================================
echo.
echo  Current Issue:
echo  Configure your laptop's USB network card (Ethernet 2) for RNDIS.
echo  Luckfox Pico default USB IP is 172.32.0.93.
echo.
echo  Opening Network Connections window for you...
echo.
control netconnections
echo.
echo  INSTRUCTIONS:
echo  1. Right-click 'Ethernet 2' (Remote NDIS based Internet Sharing Device)
echo  2. Click 'Properties' -> Double-click 'Internet Protocol Version 4 (TCP/IPv4)'
echo  3. Set IP address:    172.32.0.100
echo  4. Set Subnet mask:   255.255.255.0
echo  5. Click OK -> Click Close
echo.
echo ====================================================================
pause
