#!/usr/bin/env python3
"""
Prepares INT8 calibration dataset from real SC3336 camera snapshots for RKNN conversion.
"""

import os
import glob
from PIL import Image

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    calib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration_images")
    os.makedirs(calib_dir, exist_ok=True)

    bmp_files = glob.glob(os.path.join(root, "*.bmp"))
    jpg_paths = []

    print(f"Found {len(bmp_files)} camera snapshots in {root}")
    for idx, bmp_path in enumerate(bmp_files):
        try:
            with Image.open(bmp_path) as img:
                rgb = img.convert("RGB")
                out_path = os.path.join(calib_dir, f"calib_{idx}.jpg")
                rgb.save(out_path, "JPEG", quality=95)
                # RKNN toolkit expects paths (convert to WSL path format if running in WSL)
                jpg_paths.append(out_path)
                print(f"  Processed: {os.path.basename(bmp_path)} -> {out_path}")
        except Exception as e:
            print(f"  Error reading {bmp_path}: {e}")

    calib_txt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration_dataset.txt")
    with open(calib_txt_path, "w") as f:
        for p in jpg_paths:
            # Convert Windows path to WSL /mnt/c format for WSL toolkit
            wsl_path = p.replace("\\", "/").replace("c:", "/mnt/c").replace("C:", "/mnt/c")
            f.write(wsl_path + "\n")

    print(f"\n[SUCCESS] Calibration dataset generated at: {calib_txt_path}")

if __name__ == '__main__':
    main()
