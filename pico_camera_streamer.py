"""
Swachh Nayan — Luckfox Pico (RV1103) Dedicated MIPI CSI Camera Streamer
Run this script DIRECTLY on the Luckfox Pico Board to stream its MIPI CSI camera module.

Device Nodes Tested: /dev/video11, /dev/video0, /dev/video1
"""

import cv2
import http.server
import socketserver
import time
import os
import sys

PORT = 8080

# Candidate V4L2 device nodes on Luckfox Pico Linux
V4L2_DEVICES = ["/dev/video11", "/dev/video0", "/dev/video1", 0, 11]

def get_pico_camera():
    """Tries Luckfox Pico V4L2 nodes to find active MIPI CSI Camera."""
    for dev in V4L2_DEVICES:
        print(f"[PICO CAM] Testing camera device node: {dev}...")
        cap = cv2.VideoCapture(dev)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                print(f"[PICO CAM SUCCESS] Active MIPI CSI Camera found at {dev}!")
                return cap
            cap.release()
    print("[PICO CAM Error] Could not open MIPI CSI camera at /dev/video11 or /dev/video0.")
    return None

cap = get_pico_camera()

class PicoCamHTTPHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path == "/" or self.path == "/video_feed":
            self.send_response(200)
            self.send_header("Content-type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            try:
                while True:
                    if cap and cap.isOpened():
                        ret, frame = cap.read()
                        if not ret:
                            time.sleep(0.05)
                            continue
                    else:
                        # Fallback frame if camera disconnected
                        import numpy as np
                        frame = np.zeros((480, 640, 3), dtype=np.uint8)
                        cv2.putText(frame, "LUCKFOX PICO CAM CONNECTING...", (50, 240),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                    ret, jpeg = cv2.imencode('.jpg', frame)
                    if ret:
                        self.wfile.write(b'--frame\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', str(len(jpeg)))
                        self.end_headers()
                        self.wfile.write(jpeg.tobytes())
                        self.wfile.write(b'\r\n')
                    time.sleep(0.04)  # ~25 FPS
            except Exception:
                pass
        else:
            self.send_error(404)

def main():
    server = socketserver.TCPServer(("", PORT), PicoCamHTTPHandler)
    print("==========================================================")
    print(f" LUCKFOX PICO MIPI CSI CAMERA STREAMER ONLINE ON PORT {PORT}")
    print(f" Stream URL: http://<PICO_IP>:{PORT}/video_feed")
    print("==========================================================")
    server.serve_forever()

if __name__ == "__main__":
    main()
