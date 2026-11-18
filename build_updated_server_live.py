with open("server_live_backup.py", "r", encoding="utf-8") as f:
    orig = f.read()

with open("studio_dashboard.html", "r", encoding="utf-8") as f:
    new_html = f.read()

# 1. Replace HTML_DASHBOARD content
idx_html_start = orig.find('HTML_DASHBOARD = r"""<!DOCTYPE html>')
if idx_html_start == -1:
    idx_html_start = orig.find('HTML_DASHBOARD = """<!DOCTYPE html>')

idx_class_start = orig.find('class LiveRequestHandler(BaseHTTPRequestHandler):')

prefix = orig[:idx_html_start]
suffix = orig[idx_class_start:]

# 2. Add do_OPTIONS right after class LiveRequestHandler(BaseHTTPRequestHandler):
options_method = """    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, User-Agent")
        self.end_headers()

"""

suffix = suffix.replace("class LiveRequestHandler(BaseHTTPRequestHandler):\n", "class LiveRequestHandler(BaseHTTPRequestHandler):\n" + options_method, 1)

# In do_GET, add CORS header to /api/live_telemetry:
old_telemetry_hdr = 'self.send_header("Content-Type", "application/json")\n            self.send_header("Content-Length", str(len(data)))'
new_telemetry_hdr = 'self.send_header("Content-Type", "application/json")\n            self.send_header("Content-Length", str(len(data)))\n            self.send_header("Access-Control-Allow-Origin", "*")'
suffix = suffix.replace(old_telemetry_hdr, new_telemetry_hdr, 1)

# In do_GET, add CORS header to /snapshot.bmp:
old_snap_hdr = 'self.send_header("Content-Type", "image/bmp")\n                    self.send_header("Content-Length", str(len(bmp_bytes)))'
new_snap_hdr = 'self.send_header("Content-Type", "image/bmp")\n                    self.send_header("Content-Length", str(len(bmp_bytes)))\n                    self.send_header("Access-Control-Allow-Origin", "*")'
suffix = suffix.replace(old_snap_hdr, new_snap_hdr, 1)

# Add new POST routes: /api/set_motor and /api/return_home (8 spaces indent for elif)
new_post_routes = """        elif path == "/api/set_motor":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(body)
                target_state = str(data.get("state", "")).upper()
                current_state = LIVE_STATE.get("pump_status", "OFF")
                if target_state in ["ON", "OFF"] and target_state != current_state:
                    try:
                        req = urllib.request.Request("http://127.0.0.1:8080/api/toggle_pump", data=b"", method="POST")
                        urllib.request.urlopen(req, timeout=1.0)
                    except Exception:
                        pass
                    with STATE_LOCK:
                        LIVE_STATE["pump_status"] = target_state
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "state": LIVE_STATE.get("pump_status")}).encode("utf-8"))
            except Exception as e:
                self.send_error(400, f"Error: {e}")
            return

        elif path == "/api/return_home":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(body) if body else {}
                home_angle = float(data.get("home_angle", LIVE_STATE.get("closed_angle", 0.0)))
                home_angle = max(0.0, min(180.0, home_angle))
                actuate_servo_to_angle(home_angle)
                with STATE_LOCK:
                    LIVE_STATE["gate_status"] = "NORMAL"
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "home_angle": home_angle}).encode("utf-8"))
            except Exception as e:
                self.send_error(400, f"Error: {e}")
            return
"""

# Insert new routes into do_POST right before `        elif path == "/api/toggle_pump":`
target_insert = '        elif path == "/api/toggle_pump":'
suffix = suffix.replace(target_insert, new_post_routes + "\n" + target_insert, 1)

# Escape triple quotes if any
escaped_html = new_html.replace('"""', r'\"\"\"')

new_full_server = prefix + 'HTML_DASHBOARD = r"""' + escaped_html + '"""\n\n' + suffix

with open("server_live_upgraded.py", "w", encoding="utf-8") as f:
    f.write(new_full_server)

print("Created server_live_upgraded.py successfully!")
