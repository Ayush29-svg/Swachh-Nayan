#!/usr/bin/env python3
"""
Swachh-Nayan: Local / Server Training Script for Storm-Drain Waste Detection
Architecture: YOLOv5n (airockchip fork for RV1103 / RKNN NPU compatibility)
Target Hardware: Luckfox Pico (RV1103, 64MB RAM, 0.5 TOPS NPU)
"""

import os
import sys
import subprocess
import argparse

def run_cmd(cmd):
    print(f"\n>> RUNNING: {cmd}\n")
    ret = subprocess.run(cmd, shell=True)
    if ret.returncode != 0:
        print(f"[ERROR] Command failed with exit code {ret.returncode}")
        sys.exit(ret.returncode)

def setup_repo():
    if not os.path.exists("yolov5_rockchip"):
        print("--> Cloning airockchip/yolov5 (contains NPU subgraph optimization)...")
        run_cmd("git clone https://github.com/airockchip/yolov5.git yolov5_rockchip")
    else:
        print("--> yolov5_rockchip repo already present.")

def main():
    parser = argparse.ArgumentParser(description="Train YOLOv5n on Drain Waste for Luckfox RV1103")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--img-size", type=int, default=640, help="Image resolution (640 recommended)")
    parser.add_argument("--data", type=str, default="../drain_waste.yaml", help="Path to dataset yaml")
    args = parser.parse_args()

    setup_repo()

    os.chdir("yolov5_rockchip")

    # Install requirements
    print("--> Ensuring PyTorch and dependencies are installed...")
    run_cmd(f"{sys.executable} -m pip install -r requirements.txt")

    # Download pre-trained nano weights if not present
    if not os.path.exists("yolov5n.pt"):
        print("--> Downloading baseline YOLOv5n COCO weights for transfer learning...")
        run_cmd("wget https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5n.pt")

    # Patch PyTorch 2.6+ weights_only=False in scripts
    patch_code = """import torch
# Global PyTorch 2.6+ weights_only compatibility patch
_orig_torch_load = torch.load
torch.load = lambda *args, **kwargs: _orig_torch_load(*args, **{**kwargs, 'weights_only': False})
"""
    for py_file in ['train.py', 'export.py', 'val.py', 'detect.py', 'models/yolo.py']:
        if os.path.exists(py_file):
            with open(py_file, 'r') as f:
                c = f.read()
            if '_orig_torch_load' not in c:
                with open(py_file, 'w') as f:
                    f.write(patch_code + '\n' + c)

    # Start Training
    print(f"\n=======================================================")
    print(f"  Starting YOLOv5n Training on Storm Drain Waste       ")
    print(f"  Epochs: {args.epochs} | Batch: {args.batch_size} | Size: {args.img_size} ")
    print(f"=======================================================\n")
    
    train_cmd = (
        f"{sys.executable} train.py "
        f"--img {args.img_size} "
        f"--batch {args.batch_size} "
        f"--epochs {args.epochs} "
        f"--data {args.data} "
        f"--weights yolov5n.pt "
        f"--cfg models/yolov5n.yaml "
        f"--project runs_drain_waste "
        f"--name exp_rv1103"
    )
    run_cmd(train_cmd)

    # Export specifically for RV1103 RKNN
    best_weights = "runs_drain_waste/exp_rv1103/weights/best.pt"
    if os.path.exists(best_weights):
        print("\n--> Exporting trained model to ONNX with Rockchip RV1103 subgraph optimizations...")
        export_cmd = f"{sys.executable} export.py --weights {best_weights} --include onnx --rknpu"
        run_cmd(export_cmd)
        print(f"\n[SUCCESS] Exported ONNX model: {best_weights.replace('.pt', '.onnx')}")
        print("You can now convert this ONNX model to INT8 RKNN using convert_to_rknn.py!")
    else:
        print("[WARNING] Could not find best.pt weights after training.")

if __name__ == '__main__':
    main()
