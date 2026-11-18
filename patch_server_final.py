with open('generate_server_live_final.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Increase pulses in _pulse_pin35 from 30 to 50
text = text.replace(
    'for _ in range(30):',
    'for _ in range(50):'
)

# 2. Add Cache-Control headers to do_GET for / and /index.html
old_get_headers = '''            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_cors_headers()
            self.end_headers()'''

new_get_headers = '''            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.send_cors_headers()
            self.end_headers()'''

text = text.replace(old_get_headers, new_get_headers, 1)

# 3. Add explicit print in do_POST for /api/set_servo_angle
old_post_angle = 'angle = float(data.get("angle", 0.0))\n                actuate_servo_to_angle(angle)'
new_post_angle = 'angle = float(data.get("angle", 0.0))\n                print(f">> [API POST] /api/set_servo_angle received: {angle} deg")\n                actuate_servo_to_angle(angle)'
text = text.replace(old_post_angle, new_post_angle, 1)

with open('generate_server_live_final.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated generate_server_live_final.py with cache-busting and 50-pulse train!")
