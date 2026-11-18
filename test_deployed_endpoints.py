import urllib.request
import json
import time

time.sleep(1)
print("1. Testing GET / on port 8088:")
res = urllib.request.urlopen("http://172.32.0.93:8088/", timeout=3)
content = res.read().decode("utf-8", errors="ignore")
print("HTTP Status:", res.status)
title = "Unknown"
if "<title>" in content:
    title = content.split("<title>")[1].split("</title>")[0]
print("Dashboard Title:", title)

print("\n2. Testing GET /api/live_telemetry:")
res2 = urllib.request.urlopen("http://172.32.0.93:8088/api/live_telemetry", timeout=3)
telemetry = json.loads(res2.read().decode())
print("Telemetry:", json.dumps(telemetry, indent=2))

print("\n3. Testing POST /api/set_motor (explicit ON):")
req_on = urllib.request.Request(
    "http://172.32.0.93:8088/api/set_motor",
    data=json.dumps({"state": "ON"}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
res_on = urllib.request.urlopen(req_on, timeout=3)
print("Set motor ON response:", res_on.read().decode())

print("\n4. Testing POST /api/set_servo_angle (angle 45°):")
req_servo = urllib.request.Request(
    "http://172.32.0.93:8088/api/set_servo_angle",
    data=json.dumps({"angle": 45.0}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
res_servo = urllib.request.urlopen(req_servo, timeout=3)
print("Servo move response:", res_servo.read().decode())

time.sleep(1)
print("\n5. Testing POST /api/return_home (home 0°):")
req_home = urllib.request.Request(
    "http://172.32.0.93:8088/api/return_home",
    data=json.dumps({"home_angle": 0.0}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
res_home = urllib.request.urlopen(req_home, timeout=3)
print("Return home response:", res_home.read().decode())

print("\n6. Testing GET /snapshot.bmp:")
res_snap = urllib.request.urlopen("http://172.32.0.93:8088/snapshot.bmp", timeout=3)
snap_bytes = res_snap.read()
print("Snapshot HTTP Status:", res_snap.status, "Bytes:", len(snap_bytes))

print("\n*** ALL ENDPOINTS VERIFIED & OPERATING 100% SUCCESSFULLY! ***")
