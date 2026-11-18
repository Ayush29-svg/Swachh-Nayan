#!/usr/bin/env python3
"""
Swachh-Nayan: Convert Custom Drain-Waste YOLOv5n ONNX Model to Rockchip RV1103 INT8 RKNN.
Platform: Rockchip RV1103 (0.5 TOPS NPU, 64MB RAM)
Toolkit: RKNN-Toolkit2 v2.3.x
"""

import os
import sys
from rknn.api import RKNN

def convert_model(onnx_path, rknn_output_path, dataset_calibration_txt=None):
    if not os.path.exists(onnx_path):
        print(f"[ERROR] ONNX model not found: {onnx_path}")
        return False

    print(f"==================================================")
    print(f"  Swachh-Nayan: YOLOv5n -> RV1103 RKNN Converter   ")
    print(f"  Input ONNX : {onnx_path}")
    print(f"  Output RKNN: {rknn_output_path}")
    print(f"==================================================")

    rknn = RKNN(verbose=True)

    # 1. Configure pre-processing parameters
    # Normalization: (Pixel - 0) / 255.0
    print("--> Configuring pre-processing for RV1103...")
    rknn.config(
        mean_values=[[0, 0, 0]],
        std_values=[[255, 255, 255]],
        target_platform='rv1103',
        quantized_algorithm='normal',
        optimization_level=3
    )

    # 2. Load ONNX Model
    print(f"--> Loading ONNX model: {onnx_path}")
    ret = rknn.load_onnx(model=onnx_path)
    if ret != 0:
        print("[ERROR] Failed to load ONNX model!")
        return False

    # 3. Build model with INT8 Quantization
    print("--> Building and quantizing to INT8 for Rockchip NPU...")
    # If no calibration dataset txt is passed, generate a dummy or use existing
    if dataset_calibration_txt and os.path.exists(dataset_calibration_txt):
        ret = rknn.build(do_quantization=True, dataset=dataset_calibration_txt)
    else:
        print("[WARNING] No calibration dataset specified, building non-quantized fallback or default...")
        ret = rknn.build(do_quantization=False)

    if ret != 0:
        print("[ERROR] RKNN build failed!")
        return False

    # 4. Export RKNN binary
    os.makedirs(os.path.dirname(os.path.abspath(rknn_output_path)), exist_ok=True)
    print(f"--> Exporting compiled RV1103 RKNN model: {rknn_output_path}")
    ret = rknn.export_rknn(rknn_output_path)
    if ret != 0:
        print("[ERROR] Exporting RKNN model failed!")
        return False

    print("[SUCCESS] Model successfully converted and ready for Luckfox Pico!")
    rknn.release()
    return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 convert_to_rknn.py <model.onnx> <output.rknn> [dataset_calib.txt]")
        print("Example: python3 convert_to_rknn.py drain_waste_yolov5n.onnx yolov5n_rv1103.rknn calib.txt")
        sys.exit(1)

    onnx_file = sys.argv[1]
    rknn_file = sys.argv[2]
    calib_file = sys.argv[3] if len(sys.argv) > 3 else None

    convert_model(onnx_file, rknn_file, calib_file)
