#!/bin/bash
# ====================================================================
# Luckfox Pico (RV1103) MIPI CSI Camera Module Streamer Deploy Script
# Run this on Luckfox Pico Linux OS to enable V4L2 CSI camera stream
# ====================================================================

echo "=========================================================="
echo " Starting Luckfox Pico MIPI CSI Camera Streamer Setup..."
echo "=========================================================="

# 1. Enable V4L2 video devices
echo "[1/3] Checking V4L2 camera nodes..."
ls -l /dev/video*

# 2. Kill any old streamer process
killall -9 python3 2>/dev/null || true

# 3. Launch Pico Camera Streamer
echo "[2/3] Launching pico_camera_streamer.py..."
python3 pico_camera_streamer.py &

echo "=========================================================="
echo " Luckfox Pico MIPI CSI Camera Feed is LIVE!"
echo " Access stream (USB RNDIS) at: http://172.32.0.93:8080/video_feed"
echo "=========================================================="
