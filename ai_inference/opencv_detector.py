"""
Swachh Nayan — OpenCV Computer Vision Fallback & Plastic Detection Engine
Features:
1. HSV Color Segmentation & Contour Geometry Analysis (Plastic bottles, wrappers, leaves).
2. Trigger Zone Evaluation: Determines if detected waste is inside the active scoop zone.
"""

import cv2
import numpy as np
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class OpenCVWasteDetector:
    def __init__(self, min_contour_area=1200):
        self.min_contour_area = min_contour_area

    def detect_waste(self, frame):
        """
        Processes frame and returns:
        - annotated_frame (cv2 image with drawn bounding boxes & trigger zone)
        - detections (list of dicts with 'class', 'bbox', 'confidence', 'in_trigger_zone')
        """
        h, w, _ = frame.shape
        annotated_frame = frame.copy()
        detections = []

        # Convert to HSV for robust color segmentation under LED bar
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Mask for white/transparent plastic reflections & colored plastic debris
        # Mask 1: Bright plastic/white bottle reflection
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 60, 255])
        mask1 = cv2.inRange(hsv, lower_white, upper_white)

        # Mask 2: Colored plastic bottles (Blues/Greens/Red)
        lower_color = np.array([80, 50, 50])
        upper_color = np.array([140, 255, 255])
        mask2 = cv2.inRange(hsv, lower_color, upper_color)

        combined_mask = cv2.bitwise_or(mask1, mask2)

        # Morphological noise removal
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)

        # Find contours of floating waste
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Calculate absolute pixel coordinates for trigger zone
        tz_x1 = int(config.TRIGGER_ZONE["xmin"] * w)
        tz_x2 = int(config.TRIGGER_ZONE["xmax"] * w)
        tz_y1 = int(config.TRIGGER_ZONE["ymin"] * h)
        tz_y2 = int(config.TRIGGER_ZONE["ymax"] * h)

        # Draw Trigger Zone Box (Cyan)
        cv2.rectangle(annotated_frame, (tz_x1, tz_y1), (tz_x2, tz_y2), (255, 255, 0), 2)
        cv2.putText(annotated_frame, "SCOOP TRIGGER ZONE", (tz_x1 + 5, tz_y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > self.min_contour_area:
                x, y, bw, bh = cv2.boundingRect(cnt)
                cx = x + bw // 2
                cy = y + bh // 2

                # Check if centroid lies inside Trigger Zone
                in_tz = (tz_x1 <= cx <= tz_x2) and (tz_y1 <= cy <= tz_y2)

                confidence = min(0.95, 0.5 + (area / 10000.0))
                
                det = {
                    "class": "plastic_waste",
                    "bbox": (x, y, bw, bh),
                    "centroid": (cx, cy),
                    "confidence": confidence,
                    "in_trigger_zone": in_tz
                }
                detections.append(det)

                # Draw Bounding Box (Red if in trigger zone, Green if outside)
                color = (0, 0, 255) if in_tz else (0, 255, 0)
                cv2.rectangle(annotated_frame, (x, y), (x + bw, y + bh), color, 2)
                label = f"PLASTIC {confidence*100:.0f}%" + (" [TRIGGER]" if in_tz else "")
                cv2.putText(annotated_frame, label, (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return annotated_frame, detections


if __name__ == "__main__":
    detector = OpenCVWasteDetector()
    test_img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Simulate a white bottle in trigger zone
    cv2.rectangle(test_img, (250, 200), (350, 300), (240, 240, 240), -1)
    
    out_img, dets = detector.detect_waste(test_img)
    print(f"Detections count: {len(dets)}")
    for d in dets:
        print("Det:", d)
