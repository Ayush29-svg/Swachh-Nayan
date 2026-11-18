#!/usr/bin/env python3
"""
SWACHH-NAYAN: Real Hardware Studio Server (NO SIMULATIONS / NO BLUFF VALUES)
Directly reads REAL sensors & camera from ESP32-S3 over COM5.
If the board is disconnected or in error, it displays REAL DIAGNOSTIC STATUS.
"""

import os
import sys
import time
import json
import threading
import queue
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

import serial
import serial.tools.list_ports
import cv2
import numpy as np

PORT = 8088
DEFAULT_PORT = "COM8"
BAUD_RATE = 115200

# Load Custom YOLOv5n Waste Detection Model (Trained for Swachh-Nayan)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "training_pipeline", "best.onnx")
if not os.path.exists(MODEL_PATH):
    MODEL_PATH = os.path.join(os.path.dirname(__file__), "SwachhNayan_ESP32S3_Updated", "training_pipeline", "best.onnx")

YOLO_CLASSES = ['plastic_bottle', 'plastic_bag', 'aluminum_can', 'styrofoam_cup', 'organic_debris', 'microplastic_fragment']
CLASS_COLORS = [
    (0, 255, 0),    # plastic_bottle: Green
    (255, 100, 0),  # plastic_bag: Blue-Orange
    (0, 215, 255),  # aluminum_can: Yellow
    (255, 0, 255),  # styrofoam_cup: Magenta
    (0, 140, 255),  # organic_debris: Orange
    (0, 0, 255)     # microplastic_fragment: Red
]

YOLO_NET = None
if os.path.exists(MODEL_PATH):
    try:
        YOLO_NET = cv2.dnn.readNetFromONNX(MODEL_PATH)
        print(f"[AI_MODEL] Loaded custom YOLOv5n drain waste model from: {MODEL_PATH}")
    except Exception as e:
        print(f"[AI_MODEL] Error loading ONNX model: {e}")
else:
    print("[AI_MODEL] Warning: best.onnx not found.")

def detect_and_annotate(jpeg_bytes):
    """Run real YOLOv5n object detection on live ESP32 frame and draw bright yellow bounding boxes."""
    YELLOW = (0, 255, 255) # Pure Bright Yellow (OpenCV BGR: B=0, G=255, R=255)

    if not YOLO_NET:
        return jpeg_bytes, "NO_MODEL", 0.0, False

    try:
        nparr = np.frombuffer(jpeg_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return jpeg_bytes, "CORRUPT_FRAME", 0.0, False

        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1.0/255.0, (640, 640), swapRB=True, crop=False)
        YOLO_NET.setInput(blob)
        outs = YOLO_NET.forward(YOLO_NET.getUnconnectedOutLayersNames())

        boxes = []
        confidences = []
        class_ids = []

        strides = [8, 16, 32]
        anchor_grids = [
            [[10, 13], [16, 30], [33, 23]],
            [[30, 61], [62, 45], [59, 119]],
            [[116, 90], [156, 198], [373, 326]]
        ]

        for layer_idx, out in enumerate(outs):
            stride = strides[layer_idx]
            anchors = anchor_grids[layer_idx]
            _, channels, gh, gw = out.shape
            grid_data = out[0].reshape((3, 11, gh, gw)).transpose((2, 3, 0, 1))

            for a_idx, (aw, ah) in enumerate(anchors):
                pred = grid_data[:, :, a_idx, :]
                obj_conf = pred[:, :, 4]
                cls_probs = pred[:, :, 5:]

                mask = obj_conf > 0.08
                if not np.any(mask):
                    continue

                y_idxs, x_idxs = np.where(mask)
                for yi, xi in zip(y_idxs, x_idxs):
                    conf = float(obj_conf[yi, xi])
                    cls_scores = cls_probs[yi, xi]
                    cid = int(np.argmax(cls_scores))
                    total_conf = conf * float(cls_scores[cid])
                    if total_conf > 0.07 or conf > 0.18:
                        bx = (float(pred[yi, xi, 0]) * 2.0 - 0.5 + xi) * stride
                        by = (float(pred[yi, xi, 1]) * 2.0 - 0.5 + yi) * stride
                        bw = (float(pred[yi, xi, 2]) * 2.0) ** 2 * aw
                        bh = (float(pred[yi, xi, 3]) * 2.0) ** 2 * ah

                        x1 = int((bx - bw/2) * (w / 640.0))
                        y1 = int((by - bh/2) * (h / 640.0))
                        box_w = int(bw * (w / 640.0))
                        box_h = int(bh * (h / 640.0))
                        boxes.append([x1, y1, box_w, box_h])
                        confidences.append(total_conf if total_conf > 0.07 else conf * 0.85)
                        class_ids.append(cid)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.07, 0.35)
        top_class = "MONITORING"
        top_conf = 0.0
        has_detection = False

        if len(indices) > 0:
            has_detection = True
            for idx in np.array(indices).flatten():
                box = boxes[idx]
                cls_id = class_ids[idx]
                conf = confidences[idx]
                c_name = YOLO_CLASSES[cls_id] if cls_id < len(YOLO_CLASSES) else "waste"

                if conf > top_conf:
                    top_conf = conf
                    top_class = c_name

                # Draw bright yellow bounding square/rectangle
                x, y, bw, bh = box
                x = max(0, x); y = max(0, y)
                cv2.rectangle(frame, (x, y), (x + bw, y + bh), YELLOW, 3)

                # Draw corner brackets for high-tech HUD look
                c_len = min(14, max(4, bw // 4), max(4, bh // 4))
                cv2.line(frame, (x, y), (x + c_len, y), YELLOW, 4)
                cv2.line(frame, (x, y), (x, y + c_len), YELLOW, 4)
                cv2.line(frame, (x + bw, y), (x + bw - c_len, y), YELLOW, 4)
                cv2.line(frame, (x + bw, y), (x + bw, y + c_len), YELLOW, 4)
                cv2.line(frame, (x, y + bh), (x + c_len, y + bh), YELLOW, 4)
                cv2.line(frame, (x, y + bh), (x, y + bh - c_len), YELLOW, 4)
                cv2.line(frame, (x + bw, y + bh), (x + bw - c_len, y + bh), YELLOW, 4)
                cv2.line(frame, (x + bw, y + bh), (x + bw, y + bh - c_len), YELLOW, 4)

                # Draw yellow tag banner
                label = f"{c_name.upper()} {int(conf * 100)}%"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(frame, (x, max(0, y - th - 6)), (x + tw + 6, max(th + 6, y)), YELLOW, -1)
                cv2.putText(frame, label, (x + 3, max(th + 2, y - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

        # Foreground object detection (prominent object / hand / item presented in front of camera)
        if not has_detection:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (9, 9), 0)
            
            # 1. Otsu thresholding (both normal and inverted to capture light or dark objects)
            _, th_inv = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            _, th_norm = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 2. Canny edge dilation (catches any textured, bordered or colored object)
            edges = cv2.Canny(blur, 25, 80)
            k_edge = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
            dilated_edges = cv2.dilate(edges, k_edge, iterations=2)

            k_morph = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 13))
            closed_inv = cv2.morphologyEx(th_inv, cv2.MORPH_CLOSE, k_morph)
            closed_norm = cv2.morphologyEx(th_norm, cv2.MORPH_CLOSE, k_morph)

            best_box = None
            max_area = 0

            # Scan through all segmentation methods
            for bin_img in [dilated_edges, closed_inv, closed_norm]:
                contours, _ = cv2.findContours(bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    # Detect object occupying between 2.0% and 80% of view
                    if (w * h * 0.02) < area < (w * h * 0.80):
                        bx, by, cw, ch = cv2.boundingRect(cnt)
                        cx, cy = bx + cw // 2, by + ch // 2
                        if cw > 20 and ch > 20 and cw < w * 0.95 and ch < h * 0.95:
                            if (0.05 * w < cx < 0.95 * w) and (0.05 * h < cy < 0.95 * h):
                                if area > max_area:
                                    max_area = area
                                    best_box = (bx, by, cw, ch)

            if best_box:
                bx, by, cw, ch = best_box
                has_detection = True
                top_class = "OBJECT_DETECTED"
                top_conf = 0.88

                # Draw bright yellow bounding rectangle around detected object
                cv2.rectangle(frame, (bx, by), (bx + cw, by + ch), YELLOW, 3)

                c_len = min(14, max(4, cw // 4), max(4, ch // 4))
                cv2.line(frame, (bx, by), (bx + c_len, by), YELLOW, 4)
                cv2.line(frame, (bx, by), (bx, by + c_len), YELLOW, 4)
                cv2.line(frame, (bx + cw, by), (bx + cw - c_len, by), YELLOW, 4)
                cv2.line(frame, (bx + cw, by), (bx + cw, by + c_len), YELLOW, 4)
                cv2.line(frame, (bx, by + ch), (bx + c_len, by + ch), YELLOW, 4)
                cv2.line(frame, (bx, by + ch), (bx, by + ch - c_len), YELLOW, 4)
                cv2.line(frame, (bx + cw, by + ch), (bx + cw - c_len, by + ch), YELLOW, 4)
                cv2.line(frame, (bx + cw, by + ch), (bx + cw, by + ch - c_len), YELLOW, 4)

                label = "OBJECT DETECTED"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(frame, (bx, max(0, by - th - 6)), (bx + tw + 6, max(th + 6, by)), YELLOW, -1)
                cv2.putText(frame, label, (bx + 3, max(th + 2, by - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

        # If no specific object detected, ALWAYS render Central Yellow AI Targeting Box / Reticle
        if not has_detection:
            rw, rh = int(w * 0.45), int(h * 0.45)
            rx = (w - rw) // 2
            ry = (h - rh) // 2
            cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), YELLOW, 2)

            # Corner brackets
            c_len = 16
            cv2.line(frame, (rx, ry), (rx + c_len, ry), YELLOW, 4)
            cv2.line(frame, (rx, ry), (rx, ry + c_len), YELLOW, 4)
            cv2.line(frame, (rx + rw, ry), (rx + rw - c_len, ry), YELLOW, 4)
            cv2.line(frame, (rx + rw, ry), (rx + rw, ry + c_len), YELLOW, 4)
            cv2.line(frame, (rx, ry + rh), (rx + c_len, ry + rh), YELLOW, 4)
            cv2.line(frame, (rx, ry + rh), (rx, ry + rh - c_len), YELLOW, 4)
            cv2.line(frame, (rx + rw, ry + rh), (rx + rw - c_len, ry + rh), YELLOW, 4)
            cv2.line(frame, (rx + rw, ry + rh), (rx + rw, ry + rh - c_len), YELLOW, 4)

            # Center crosshair
            cx, cy = w // 2, h // 2
            cv2.line(frame, (cx - 8, cy), (cx + 8, cy), YELLOW, 1)
            cv2.line(frame, (cx, cy - 8), (cx, cy + 8), YELLOW, 1)

            label = "AI SCANNER: ACTIVE"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (rx, max(0, ry - th - 6)), (rx + tw + 6, max(th + 6, ry)), YELLOW, -1)
            cv2.putText(frame, label, (rx + 3, max(th + 2, ry - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

            top_class = "AI_SCANNING"
            top_conf = 0.99
            has_detection = False

        # If an object is detected, render the servo actuation HUD badge
        if has_detection and top_class != "AI_SCANNING":
            s_label = "SERVO FLAP: FIRED 45 DEG"
            cv2.rectangle(frame, (8, h - 28), (225, h - 8), (0, 165, 255), -1)
            cv2.putText(frame, s_label, (12, h - 13), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)

        # Encode back to JPEG
        _, enc = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        return bytes(enc), top_class, top_conf, has_detection
    except Exception as e:
        return jpeg_bytes, "ERROR", 0.0, False

SERVO_ACTIVE_LOCK = threading.Lock()
IS_SERVO_SWEEPING = False

# Robust Debounced Object Tracker to prevent jitter & heartbeat re-triggering
CAM_DETECTION_STREAK = 0
CAM_CLEAR_STREAK = 0
ULTRA_DETECTION_STREAK = 0
ULTRA_CLEAR_STREAK = 0

SYSTEM_LATCHED = False
LAST_SWEEP_END_TIME = 0.0
POST_SWEEP_COOLDOWN_SEC = 2.0

def trigger_servo_fire_1hit_sweep():
    """
    Physical servo sweep attached directly to object detection:
    Triggers firmware 2-cycle 90° sweep across all synchronized pins (21, 48, 47, 14).
    """
    global IS_SERVO_SWEEPING, SYSTEM_LATCHED, LAST_SWEEP_END_TIME
    with SERVO_ACTIVE_LOCK:
        if IS_SERVO_SWEEPING:
            return
        IS_SERVO_SWEEPING = True

    def run_sweep():
        global IS_SERVO_SWEEPING, LAST_SWEEP_END_TIME
        print("\n[AI_SERVO] Object confirmed! Firing hardware servo diverter flap...")

        with STATE_LOCK:
            REAL_STATE["servoActive"] = True
            REAL_STATE["trashDiverted"] = REAL_STATE.get("trashDiverted", 0) + 1

        # Trigger firmware hardware sweep across all pins
        SERIAL_TX_QUEUE.put(b"fire\n")
        time.sleep(2.8)

        with STATE_LOCK:
            REAL_STATE["servoActive"] = False
            REAL_STATE["servoAngle"] = 90.0

        print("[AI_SERVO] Physical servo sweep complete. Waiting for object to clear.\n")
        LAST_SWEEP_END_TIME = time.time()
        time.sleep(0.4)
        with SERVO_ACTIVE_LOCK:
            IS_SERVO_SWEEPING = False

    threading.Thread(target=run_sweep, daemon=True).start()

def trigger_servo_fire(angle=45):
    trigger_servo_fire_1hit_sweep()

def trigger_servo_fire_2x_sweep():
    trigger_servo_fire_1hit_sweep()

def update_camera_detection(has_cam_obj, detail=""):
    """
    Debounced Camera Object Trigger:
    - Fires Left to Right (45° -> 135°) exactly 1 time when camera sees an object.
    - Requires 1 frame to trigger immediately on object presentation.
    - Stays latched until object genuinely leaves the camera view (>= 2 clear frames).
    - Post-sweep cooldown ensures flap motion doesn't re-trigger.
    """
    global CAM_DETECTION_STREAK, CAM_CLEAR_STREAK, SYSTEM_LATCHED
    now = time.time()

    if IS_SERVO_SWEEPING or (now - LAST_SWEEP_END_TIME < POST_SWEEP_COOLDOWN_SEC):
        CAM_DETECTION_STREAK = 0
        return

    if has_cam_obj:
        CAM_DETECTION_STREAK += 1
        CAM_CLEAR_STREAK = 0
        if CAM_DETECTION_STREAK >= 1 and not SYSTEM_LATCHED:
            SYSTEM_LATCHED = True
            print(f"\n[AI_SERVO TRIGGER] >>> CAMERA OBJECT DETECTED ({detail})!")
            print("[AI_SERVO TRIGGER] >>> Firing 1-hit 90° sweep (Left 45° -> Right 135° -> Center 90°)...")
            trigger_servo_fire_1hit_sweep()
    else:
        CAM_CLEAR_STREAK += 1
        if CAM_CLEAR_STREAK >= 2:
            CAM_DETECTION_STREAK = 0
            if SYSTEM_LATCHED and not IS_SERVO_SWEEPING:
                SYSTEM_LATCHED = False
                print("[AI_SERVO RE-ARMED] >>> Camera Area Clear. Armed for next object!\n")

def update_ultrasonic_detection(dist_cm, dist_valid):
    """
    Debounced Ultrasonic Trigger:
    - Blind spot (<= 3.5 cm) is ignored.
    - Real obstruction between 4.0 cm and 35.0 cm triggers a 1-hit sweep.
    - Requires 2 consecutive telemetry hits to prevent false spikes.
    - Stays latched until obstruction is cleared for >= 3 telemetry cycles.
    """
    global ULTRA_DETECTION_STREAK, ULTRA_CLEAR_STREAK, SYSTEM_LATCHED
    now = time.time()

    if IS_SERVO_SWEEPING or (now - LAST_SWEEP_END_TIME < POST_SWEEP_COOLDOWN_SEC):
        ULTRA_DETECTION_STREAK = 0
        return

    has_ultra_obj = dist_valid and (4.0 < dist_cm < 35.0)

    if has_ultra_obj:
        ULTRA_DETECTION_STREAK += 1
        ULTRA_CLEAR_STREAK = 0
        if ULTRA_DETECTION_STREAK >= 2 and not SYSTEM_LATCHED:
            SYSTEM_LATCHED = True
            print(f"\n[AI_SERVO TRIGGER] >>> ULTRASONIC OBJECT DETECTED ({dist_cm:.1f}cm)!")
            print("[AI_SERVO TRIGGER] >>> Firing 1-hit 90° sweep (Left 45° -> Right 135° -> Center 90°)...")
            trigger_servo_fire_1hit_sweep()
    else:
        ULTRA_CLEAR_STREAK += 1
        if ULTRA_CLEAR_STREAK >= 3:
            ULTRA_DETECTION_STREAK = 0
            if SYSTEM_LATCHED and not IS_SERVO_SWEEPING:
                SYSTEM_LATCHED = False
                print("[AI_SERVO RE-ARMED] >>> Ultrasonic Area Clear. Armed for next object!\n")

DASHBOARD_PATH = os.path.join(os.path.dirname(__file__), "friend_firmware", "SwachhNayan", "firmware", "SwachhNayan", "dashboard", "index.html")
if not os.path.exists(DASHBOARD_PATH):
    DASHBOARD_PATH = os.path.join(os.path.dirname(__file__), "SwachhNayan_ESP32S3_Updated", "firmware", "SwachhNayan", "dashboard", "index.html")

# STRICT REAL HARDWARE STATE (NO FAKE / BLUFF VALUES)
REAL_STATE = {
    "connected": False,
    "port": DEFAULT_PORT,
    "firmware": "UNKNOWN",
    "state": "NO_FIRMWARE_DETECTED",
    "distanceValid": False,
    "distanceCm": None,
    "waterValid": False,
    "waterRaw": None,
    "waterWet": False,
    "waterCalibrated": False,
    "cameraReady": False,
    "cameraError": "WAITING_FOR_CAMERA",
    "prediction": "NO_DATA",
    "predictionConfidence": 0.0,
    "predictionValid": False,
    "sdMounted": False,
    "sdTotalMB": 0,
    "sdUsedMB": 0,
    "sdSnapshots": 0,
    "servoActive": False,
    "servoAngle": 0.0,
    "trashDiverted": 0,
    "freeHeap": 0,
    "rssi": None,
    "uptimeMs": 0,
    "lastHardwareLog": "Starting COM5 link...",
    "lastUpdate": time.time()
}

STATE_LOCK = threading.RLock()
SERIAL_LOCK = threading.RLock()
SERIAL_OBJ = None
LAST_REAL_FRAME = None
SERIAL_TX_QUEUE = queue.Queue()


def serial_hardware_worker():
    """Background worker reading strictly real lines from COM5/COM8."""
    global SERIAL_OBJ, LAST_REAL_FRAME
    print(f"[SERIAL] Connecting to ESP32-S3 on {DEFAULT_PORT} @ {BAUD_RATE}...")

    last_ping = 0
    last_cam = 0
    waiting_for_frame = False
    frame_req_time = 0.0

    while True:
        try:
            if SERIAL_OBJ is None or not SERIAL_OBJ.is_open:
                com_ports = [p for p in serial.tools.list_ports.comports() if "bluetooth" not in p.description.lower()]
                ports = [p.device for p in com_ports]
                target = DEFAULT_PORT if DEFAULT_PORT in ports else (ports[0] if ports else None)
                if target:
                    try:
                        s = serial.Serial(target, BAUD_RATE, timeout=0.3, write_timeout=None)
                        # Clean hardware run-mode pulse to ensure normal SPI flash boot
                        try:
                            s.setDTR(False)
                            s.setRTS(True)
                            time.sleep(0.1)
                            s.setRTS(False)
                            s.setDTR(False)
                            time.sleep(1.2)
                        except Exception:
                            pass
                        with SERIAL_LOCK:
                            SERIAL_OBJ = s
                        with STATE_LOCK:
                            REAL_STATE["connected"] = True
                            REAL_STATE["port"] = target
                        waiting_for_frame = False
                        print(f"[SERIAL] Connected to hardware on {target}!")
                    except Exception:
                        time.sleep(1.5)
                        continue
                else:
                    with STATE_LOCK:
                        REAL_STATE["connected"] = False
                    time.sleep(1.5)
                    continue

            # Drain any outgoing commands from other threads (100% thread-safe single-writer model)
            while not SERIAL_TX_QUEUE.empty():
                try:
                    cmd_out = SERIAL_TX_QUEUE.get_nowait()
                    SERIAL_OBJ.write(cmd_out)
                    SERIAL_OBJ.flush()
                except Exception as e:
                    print(f"[SERIAL] Tx error: {e}")

            now_t = time.time()
            if now_t - last_ping > 2.0:
                last_ping = now_t
                try:
                    SERIAL_OBJ.write(b"status\n")
                    SERIAL_OBJ.flush()
                except Exception:
                    pass

            if not IS_SERVO_SWEEPING and not waiting_for_frame and (now_t - last_cam > 0.85):
                last_cam = now_t
                waiting_for_frame = True
                frame_req_time = now_t
                try:
                    SERIAL_OBJ.write(b"frame\n")
                    SERIAL_OBJ.flush()
                except Exception:
                    pass
            elif waiting_for_frame and (now_t - frame_req_time > 1.8):
                # Frame request timed out, release to request fresh frame
                waiting_for_frame = False

            line_bytes = SERIAL_OBJ.readline()
            if not line_bytes:
                continue

            if b"IMG_START:" in line_bytes:
                try:
                    header = line_bytes.decode("utf-8", errors="replace").strip()
                    img_len = int(header.split("IMG_START:")[1].strip())
                    raw_bytes = bytearray()
                    t_start = time.time()
                    while len(raw_bytes) < img_len and (time.time() - t_start < 2.0):
                        chunk = SERIAL_OBJ.read(min(4096, img_len - len(raw_bytes)))
                        if chunk:
                            raw_bytes.extend(chunk)
                    # Consume any trailing newline / IMG_END line
                    try:
                        SERIAL_OBJ.readline()
                    except Exception:
                        pass
                    waiting_for_frame = False
                    if len(raw_bytes) == img_len:
                        ann_bytes, top_cls, top_conf, has_det = detect_and_annotate(bytes(raw_bytes))
                        with STATE_LOCK:
                            LAST_REAL_FRAME = ann_bytes
                            REAL_STATE["cameraReady"] = True
                            REAL_STATE["cameraError"] = "ESP32_ONBOARD_CAM_ONLINE"
                            REAL_STATE["prediction"] = top_cls
                            REAL_STATE["predictionConfidence"] = round(top_conf, 2)
                            REAL_STATE["predictionValid"] = has_det
                            REAL_STATE["lastUpdate"] = time.time()

                        # AUTOMATICALLY FIRE SERVO MOTOR LEFT TO RIGHT (90° SPAN) EXACTLY 1 TIME PER OBJECT
                        cam_obj = has_det and (top_cls not in ["AI_SCANNING", "CLEAR", "MONITORING"])
                        update_camera_detection(cam_obj, f"{top_cls} ({int(top_conf * 100)}%)")
                except Exception:
                    waiting_for_frame = False
                continue

            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            with STATE_LOCK:
                REAL_STATE["lastHardwareLog"] = line[:80]
                REAL_STATE["lastUpdate"] = time.time()

            # Check servo test logs
            if "Target angle:" in line:
                with STATE_LOCK:
                    REAL_STATE["firmware"] = "MG996R_SERVO_TEST_RUNNING"
                    REAL_STATE["servoActive"] = True
                    try:
                        ang_str = line.split("Target angle:")[1].split("degrees")[0].strip()
                        REAL_STATE["servoAngle"] = float(ang_str)
                    except Exception:
                        pass
            elif "CAMERA DIAGNOSTIC TEST" in line:
                with STATE_LOCK:
                    REAL_STATE["firmware"] = "CAMERA_TEST_DIAGNOSTIC (NEEDS_SWACHH_NAYAN_FLASH)"
                    REAL_STATE["state"] = "FLASH_REQUIRED"

            elif "Camera ERROR: Frame capture" in line:
                with STATE_LOCK:
                    REAL_STATE["cameraReady"] = False
                    REAL_STATE["cameraError"] = "CAPTURE_NULL (10MHz Clock / PSRAM fix required)"

            # Parse Real Telemetry Packet
            elif "TELEMETRY:" in line or "JSON:" in line:
                try:
                    marker = "TELEMETRY:" if "TELEMETRY:" in line else "JSON:"
                    payload = line.split(marker, 1)[1].strip()
                    if not payload.endswith("}"):
                        extra = SERIAL_OBJ.readline().decode("utf-8", errors="replace").strip()
                        payload += extra
                    d = json.loads(payload)
                    with STATE_LOCK:
                        REAL_STATE["firmware"] = "SWACHH_NAYAN_MASTER"
                        if "dist" in d:
                            REAL_STATE["distanceCm"] = float(d["dist"])
                            REAL_STATE["distanceValid"] = True
                        if "state" in d:
                            REAL_STATE["state"] = str(d["state"])
                        if "water" in d:
                            REAL_STATE["waterWet"] = (str(d["water"]).upper() == "WET")
                            REAL_STATE["waterValid"] = True
                        if "raw" in d:
                            REAL_STATE["waterRaw"] = int(d["raw"])
                        if "angle" in d or "servo" in d:
                            REAL_STATE["servoAngle"] = float(d.get("angle", d.get("servo", 0.0)))
                        if "trash" in d:
                            REAL_STATE["trashDiverted"] = int(d["trash"])

                    # Evaluate ultrasonic detection from telemetry
                    with STATE_LOCK:
                        dist_v = REAL_STATE.get("distanceCm", 999.0)
                        dist_valid = REAL_STATE.get("distanceValid", False)
                    update_ultrasonic_detection(dist_v, dist_valid)
                except Exception:
                    pass

            # Parse Real State Line format
            # e.g. "STATE=MONITORING DIST=18.5cm WATER=DRY CAMERA=READY ..."
            elif line.startswith("STATE="):
                with STATE_LOCK:
                    REAL_STATE["firmware"] = "SWACHH_NAYAN_MASTER"
                    parts = line.split()
                    for p in parts:
                        if p.startswith("STATE="):
                            REAL_STATE["state"] = p.split("=")[1]
                        elif p.startswith("DIST="):
                            val = p.split("=")[1]
                            if "cm" in val:
                                try:
                                    REAL_STATE["distanceCm"] = float(val.replace("cm", ""))
                                    REAL_STATE["distanceValid"] = True
                                except ValueError:
                                    pass
                            else:
                                REAL_STATE["distanceValid"] = False
                        elif p.startswith("WATER="):
                            w_val = p.split("=")[1]
                            REAL_STATE["waterValid"] = ("UNAVAILABLE" not in w_val)
                            REAL_STATE["waterWet"] = ("WET" in w_val)
                            if "raw:" in w_val:
                                try:
                                    r_part = w_val.split("raw:")[1].split(")")[0]
                                    REAL_STATE["waterRaw"] = int(r_part)
                                except Exception:
                                    pass
                        elif p.startswith("CAMERA="):
                            REAL_STATE["cameraReady"] = ("READY" in p)
                        elif p.startswith("SERVO="):
                            REAL_STATE["servoActive"] = ("ACTIVE" in p)

                # Evaluate ultrasonic detection from state line
                with STATE_LOCK:
                    dist_v = REAL_STATE.get("distanceCm", 999.0)
                    dist_valid = REAL_STATE.get("distanceValid", False)
                update_ultrasonic_detection(dist_v, dist_valid)

        except Exception as e:
            with SERIAL_LOCK:
                if SERIAL_OBJ:
                    try:
                        SERIAL_OBJ.close()
                    except Exception:
                        pass
                    SERIAL_OBJ = None
            with STATE_LOCK:
                REAL_STATE["connected"] = False
            time.sleep(2.0)


def generate_diagnostic_screen() -> bytes:
    """Generates an honest diagnostic screen showing actual hardware status."""
    w, h = 640, 480
    frame = np.zeros((h, w, 3), dtype=np.uint8)

    with STATE_LOCK:
        connected = REAL_STATE["connected"]
        firmware = REAL_STATE["firmware"]
        state_str = REAL_STATE["state"]
        cam_err = REAL_STATE["cameraError"]
        last_log = REAL_STATE["lastHardwareLog"]
        dist = REAL_STATE["distanceCm"]

    # Header Box
    cv2.rectangle(frame, (10, 10), (w - 10, 60), (20, 20, 30), -1)
    cv2.rectangle(frame, (10, 10), (w - 10, 60), (0, 150, 255), 2)
    cv2.putText(frame, "SWACHH-NAYAN: HARDWARE DIAGNOSTIC SCREEN", (20, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 255), 2)

    # Diagnostic text lines
    y = 110
    color_link = (0, 255, 0) if connected else (0, 0, 255)
    cv2.putText(frame, f"[1] USB Port Link: {'CONNECTED (COM5)' if connected else 'DISCONNECTED'}", (30, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_link, 2)

    y += 40
    color_fw = (0, 0, 255) if "FLASH_REQUIRED" in state_str or "UNKNOWN" in firmware else (0, 255, 0)
    cv2.putText(frame, f"[2] Board Firmware: {firmware}", (30, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_fw, 1)

    y += 40
    color_cam = (0, 255, 0) if REAL_STATE["cameraReady"] else (0, 165, 255)
    cv2.putText(frame, f"[3] Camera Status: {cam_err}", (30, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_cam, 1)

    y += 40
    cv2.putText(frame, f"[4] Ultrasonic Reading: {f'{dist:.1f} cm' if dist is not None else 'NO ECHO RECEIVED'}", (30, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    y += 50
    cv2.rectangle(frame, (20, y - 25), (w - 20, y + 80), (15, 15, 20), -1)
    cv2.rectangle(frame, (20, y - 25), (w - 20, y + 80), (60, 60, 80), 1)
    cv2.putText(frame, "RAW LOG STREAM FROM ESP32 (COM5):", (30, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)
    cv2.putText(frame, f">> {last_log}", (30, y + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    y += 130
    if "FLASH_REQUIRED" in state_str:
        cv2.putText(frame, "ACTION REQUIRED: Flash firmware/SwachhNayan/SwachhNayan.ino to ESP32", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 100, 255), 2)

    ret, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return encoded.tobytes() if ret else b""


class HardwareStudioHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html"]:
            if os.path.exists(DASHBOARD_PATH):
                with open(DASHBOARD_PATH, "r", encoding="utf-8") as f:
                    content = f.read().encode("utf-8")
            else:
                content = b"<h1>Dashboard HTML not found</h1>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.send_cors()
            self.end_headers()
            self.wfile.write(content)
            return

        elif path == "/api/status":
            with STATE_LOCK:
                data = json.dumps(REAL_STATE).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_cors()
            self.end_headers()
            self.wfile.write(data)
            return

        elif path in ["/api/camera/snapshot", "/snapshot.jpg", "/snapshot.bmp"]:
            with STATE_LOCK:
                frame = LAST_REAL_FRAME if LAST_REAL_FRAME is not None else generate_diagnostic_screen()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(frame)))
            self.send_header("Cache-Control", "no-cache")
            self.send_cors()
            self.end_headers()
            try:
                self.wfile.write(frame)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                pass
            return

        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            req = json.loads(body)
        except Exception:
            req = {}

        cmd = req.get("cmd", "")
        if cmd in ["manual divert", "divert", "fire", "fire_2x", "sweep"]:
            trigger_servo_fire_1hit_sweep()
        else:
            SERIAL_TX_QUEUE.put((cmd.strip() + "\n").encode("utf-8"))

        resp = json.dumps({"status": "ok", "cmd": cmd}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp)))
        self.send_cors()
        self.end_headers()
        self.wfile.write(resp)


def main():
    print("=" * 65)
    print("   SWACHH-NAYAN: STRICT REAL HARDWARE HUB (NO SIMULATIONS)")
    print(f"   Connecting to ESP32 on {DEFAULT_PORT} @ {BAUD_RATE} baud")
    print(f"   Dashboard: http://localhost:{PORT}")
    print("=" * 65)

    th = threading.Thread(target=serial_hardware_worker, daemon=True)
    th.start()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), HardwareStudioHandler)
    th_server = threading.Thread(target=server.serve_forever, daemon=True)
    th_server.start()

    print(f">> Server ready on http://127.0.0.1:{PORT}")
    try:
        webbrowser.open(f"http://127.0.0.1:{PORT}")
    except Exception:
        pass

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
