"""
Swachh Nayan — Luckfox Pico Auto-Detector & Automatic Uploader
Continuously monitors USB / Network for Luckfox Pico board and automatically uploads files upon connection.
"""

import time
import subprocess
import os
import sys

PROJECT_DIR = r"c:\Users\gupta\Downloads\Swachh_Nayan"
TARGET_IPS = ["172.32.0.93", "192.168.10.11", "172.32.0.2", "192.168.1.11", "192.168.0.11"]

def test_ssh(ip):
    try:
        res = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=1", "-o", "StrictHostKeyChecking=no", f"root@{ip}", "echo PICO_READY"],
            capture_output=True,
            text=True,
            timeout=2
        )
        return "PICO_READY" in res.stdout
    except Exception:
        return False

def upload_files(ip):
    print(f"\n[AUTO UPLOAD] Board detected at {ip}! Uploading project files...")
    cmd = ["scp", "-r", os.path.join(PROJECT_DIR, "*"), f"root@{ip}:/root/"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            print(f"[AUTO UPLOAD SUCCESS] All files successfully uploaded to Luckfox Pico at {ip}!")
            print("[AUTO LAUNCH] Starting standalone Pico engine on board...")
            subprocess.run(["ssh", f"root@{ip}", "chmod +x /root/deploy_standalone_pico.sh && /root/deploy_standalone_pico.sh"])
            return True
        else:
            print(f"[AUTO UPLOAD ERROR]: {res.stderr}")
    except Exception as e:
        print(f"[AUTO UPLOAD EXCEPTION]: {e}")
    return False

def main():
    print("====================================================================")
    print(" SWACHH NAYAN — Luckfox Pico Auto-Detector & Upload Daemon         ")
    print(" Watching USB RNDIS & Network for Luckfox Pico connection...         ")
    print("====================================================================")

    while True:
        for ip in TARGET_IPS:
            if test_ssh(ip):
                if upload_files(ip):
                    print(f"\n*** UPLOAD & BOARD LAUNCH COMPLETE! YOU CAN VISIT http://{ip}:8080 ***")
                    return
        time.sleep(2)

if __name__ == "__main__":
    main()
