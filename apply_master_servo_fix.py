import re

with open('studio_dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Uncheck autoReturnCheck by default so the servo STAYS at target angle!
html = html.replace(
    '<input type="checkbox" id="autoReturnCheck" checked>',
    '<input type="checkbox" id="autoReturnCheck">'
)

# 2. Add Sticky Quick Bar right after <body>
quick_bar = """<body>
    <!-- DIRECT SERVO OVERRIDE BAR -->
    <div class="servo-quick-bar" style="background: linear-gradient(90deg, #0369a1, #0284c7); padding: 10px 20px; display: flex; align-items: center; justify-content: space-between; gap: 12px; border-bottom: 2px solid #38bdf8; position: sticky; top: 0; z-index: 1000; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
        <div style="font-weight: 800; color: #fff; font-size: 0.9rem; letter-spacing: 0.5px; display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 1.2rem;">⚡</span> DIRECT SERVO HARDWARE CONTROL:
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button onclick="directMoveServo(0)" style="padding: 7px 15px; background: #0f172a; color: #38bdf8; border: 1px solid #38bdf8; font-weight: 700; border-radius: 6px; cursor: pointer; font-size: 0.85rem;">0° (REST)</button>
            <button onclick="directMoveServo(45)" style="padding: 7px 15px; background: #0f172a; color: #38bdf8; border: 1px solid #38bdf8; font-weight: 700; border-radius: 6px; cursor: pointer; font-size: 0.85rem;">45° (QUARTER)</button>
            <button onclick="directMoveServo(90)" style="padding: 7px 15px; background: #38bdf8; color: #020617; border: 1px solid #38bdf8; font-weight: 800; border-radius: 6px; cursor: pointer; font-size: 0.85rem;">90° (DIVERT)</button>
            <button onclick="directMoveServo(135)" style="padding: 7px 15px; background: #0f172a; color: #38bdf8; border: 1px solid #38bdf8; font-weight: 700; border-radius: 6px; cursor: pointer; font-size: 0.85rem;">135° (WIDE)</button>
            <button onclick="directMoveServo(180)" style="padding: 7px 15px; background: #0f172a; color: #38bdf8; border: 1px solid #38bdf8; font-weight: 700; border-radius: 6px; cursor: pointer; font-size: 0.85rem;">180° (MAX)</button>
            <button onclick="triggerTestSweep()" style="padding: 7px 16px; background: #f59e0b; color: #020617; border: none; font-weight: 800; border-radius: 6px; cursor: pointer; font-size: 0.85rem;">🔄 RUN TEST SWEEP</button>
        </div>
    </div>"""

if '<div class="servo-quick-bar"' not in html:
    html = html.replace('<body>', quick_bar, 1)

# 3. Save updated studio_dashboard.html
with open('studio_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Updated studio_dashboard.html successfully!")
