@echo off
:: Swachh Nayan — RNDIS Luckfox Pico USB Network Fix
:: Configures static IP 172.32.0.100 on Ethernet 2 (RNDIS Adapter)

echo ========================================================
echo  Configuring RNDIS USB Adapter IP for Luckfox Pico...
echo ========================================================

netsh interface ip set address name="Ethernet 2" static 172.32.0.100 255.255.255.0

echo.
echo ========================================================
echo  Testing connection to Luckfox Pico (172.32.0.93)...
echo ========================================================
ping -n 3 172.32.0.93

pause
