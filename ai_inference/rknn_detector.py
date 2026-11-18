"""
Swachh Nayan — RKNN NPU Hardware Accelerated Object Detection Engine
Target: Waveshare Luckfox Pico (RV1103 ARM Cortex-A7 + 0.5 TOPS NPU)
"""

import cv2
import numpy as np
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class RKNNNPUWasteDetector:
    def __init__(self, model_path=config.RKNN_MODEL_PATH):
        self.model_path = model_path
        self.rknn_lite = None
        self.npu_available = False

        self._init_rknn()

    def _init_rknn(self):
        """Initialize RKNN Lite runtime on Luckfox Pico RV1103."""
        try:
            from rknnlite.api import RKNNLite
            self.rknn_lite = RKNNLite()
            
            if not os.path.exists(self.model_path):
                print(f"[RKNN NPU] Model file {self.model_path} not found. Falling back to OpenCV Engine.")
                return

            print(f"[RKNN NPU] Loading RKNN model from {self.model_path}...")
            ret = self.rknn_lite.load_rknn(self.model_path)
            if ret != 0:
                print(f"[RKNN NPU Error] Load RKNN failed with code {ret}")
                return

            ret = self.rknn_lite.init_runtime(async_mode=False)
            if ret != 0:
                print(f"[RKNN NPU Error] Init runtime failed with code {ret}")
                return

            self.npu_available = True
            print("[RKNN NPU] Luckfox Pico 0.5 TOPS NPU runtime initialized successfully!")

        except ImportError:
            print("[RKNN NPU] rknnlite library not found. Running in OpenCV Fallback mode.")
        except Exception as e:
            print(f"[RKNN NPU Initialization Exception]: {e}")

    def detect_waste(self, frame):
        """
        Runs frame through RV1103 NPU if available, else returns OpenCV fallback.
        """
        if not self.npu_available:
            from ai_inference.opencv_detector import OpenCVWasteDetector
            cv_fallback = OpenCVWasteDetector()
            return cv_fallback.detect_waste(frame)

        # NPU Pre-processing
        h, w, _ = frame.shape
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (300, 300))
        img_input = np.expand_dims(img_resized, axis=0)

        # Execute NPU Inference
        outputs = self.rknn_lite.inference(inputs=[img_input])

        # Post-process NPU output tensors (MobileNetV2-SSD style: boxes, classes, scores)
        boxes = outputs[0][0]
        classes = outputs[1][0]
        scores = outputs[2][0]

        annotated_frame = frame.copy()
        detections = []

        tz_x1 = int(config.TRIGGER_ZONE["xmin"] * w)
        tz_x2 = int(config.TRIGGER_ZONE["xmax"] * w)
        tz_y1 = int(config.TRIGGER_ZONE["ymin"] * h)
        tz_y2 = int(config.TRIGGER_ZONE["ymax"] * h)

        # Draw Trigger Zone Box
        cv2.rectangle(annotated_frame, (tz_x1, tz_y1), (tz_x2, tz_y2), (255, 255, 0), 2)

        for i in range(len(scores)):
            score = scores[i]
            if score >= config.CONFIDENCE_THRESHOLD:
                cls_id = int(classes[i])
                cls_name = config.CLASSES[cls_id] if cls_id < len(config.CLASSES) else "waste"
                
                box = boxes[i]
                ymin, xmin, ymax, xmax = int(box[0]*h), int(box[1]*w), int(box[2]*h), int(box[3]*w)
                bw, bh = xmax - xmin, ymax - ymin
                cx, cy = xmin + bw//2, ymin + bh//2

                in_tz = (tz_x1 <= cx <= tz_x2) and (tz_y1 <= cy <= tz_y2)

                det = {
                    "class": cls_name,
                    "bbox": (xmin, ymin, bw, bh),
                    "centroid": (cx, cy),
                    "confidence": float(score),
                    "in_trigger_zone": in_tz
                }
                detections.append(det)

                color = (0, 0, 255) if in_tz else (0, 255, 0)
                cv2.rectangle(annotated_frame, (xmin, ymin), (xmax, ymax), color, 2)
                label = f"NPU: {cls_name} {score*100:.0f}%"
                cv2.putText(annotated_frame, label, (xmin, ymin - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return annotated_frame, detections

    def release(self):
        if self.rknn_lite and self.npu_available:
            self.rknn_lite.release()
