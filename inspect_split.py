import os

# We will read server_live_backup.py up to line 314 (before HTML_DASHBOARD),
# then inject the new modern Studio UI HTML_DASHBOARD,
# then inject the enhanced LiveRequestHandler with do_OPTIONS, /api/set_motor, /api/move_servo_with_return, /api/return_home.

with open("server_live_backup.py", "r", encoding="utf-8") as f:
    orig_code = f.read()

# Find where HTML_DASHBOARD begins and where LiveRequestHandler begins
idx_html_start = orig_code.find('HTML_DASHBOARD = r"""<!DOCTYPE html>')
if idx_html_start == -1:
    idx_html_start = orig_code.find('HTML_DASHBOARD = """<!DOCTYPE html>')

idx_class_start = orig_code.find('class LiveRequestHandler(BaseHTTPRequestHandler):')

print("Found HTML_DASHBOARD at:", idx_html_start)
print("Found LiveRequestHandler at:", idx_class_start)
