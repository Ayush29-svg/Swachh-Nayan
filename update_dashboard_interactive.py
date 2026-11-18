with open('studio_dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update slider to add onchange
html = html.replace(
    'oninput="onSliderInput(this.value)"',
    'oninput="onSliderInput(this.value)" onchange="directMoveServo(this.value)"'
)

# 2. Update number input to add onchange
html = html.replace(
    'oninput="onNumInput(this.value)"',
    'oninput="onNumInput(this.value)" onchange="directMoveServo(this.value)"'
)

# 3. Add Test Sweep Button next to Return Home
target_btn_row = '<button class="btn-action btn-secondary" onclick="returnServoHome()">'
new_btn_row = '''<button class="btn-action btn-info" onclick="triggerTestSweep()" style="background:#0284c7; color:#fff;" title="Run automated hardware sweep test">
                            <span>🔄</span> TEST SWEEP (0° ➔ 180°)
                        </button>
                        <button class="btn-action btn-secondary" onclick="returnServoHome()">'''

if target_btn_row in html:
    html = html.replace(target_btn_row, new_btn_row, 1)

# 4. Update JavaScript functions: directMoveServo, selectPresetAngle, triggerTestSweep
target_js = """        function selectPresetAngle(ang) {
            onSliderInput(ang);
            showToast(`Target angle set to ${ang}?`, "info");
        }"""

replacement_js = """        let directServoDebounce = null;
        async function directMoveServo(angle) {
            const clamped = Math.max(0, Math.min(180, parseFloat(angle)));
            commandedServoAngle = clamped;
            updateServoVisuals(clamped);
            document.getElementById("servoOpStatusPill").innerText = `MOVING TO ${clamped.toFixed(0)}°`;
            document.getElementById("servoOpStatusPill").className = "status-pill status-active";

            if (directServoDebounce) clearTimeout(directServoDebounce);
            directServoDebounce = setTimeout(async () => {
                try {
                    logEvent("SERVO", `Sending angle ${clamped.toFixed(1)}° to controller...`);
                    const res = await fetch(BASE_URL + "/api/set_servo_angle", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ angle: clamped })
                    });
                    if (res.ok) {
                        const data = await res.json().catch(() => ({}));
                        confirmedServoAngle = clamped;
                        updateServoVisuals(clamped);
                        document.getElementById("servoOpStatusPill").innerText = `HOLDING AT ${clamped.toFixed(0)}°`;
                        document.getElementById("servoOpStatusPill").className = "status-pill status-idle";
                        showToast(`Servo positioned at ${clamped.toFixed(0)}°`, "success");
                        logEvent("SERVO", `Physical servo confirmed at ${clamped.toFixed(1)}° (duty: ${data.duty_ns || 'calibrated'} ns).`);
                    } else {
                        throw new Error("HTTP " + res.status);
                    }
                } catch (err) {
                    showToast("Servo command failed: " + err.message, "error");
                    logEvent("ERR", "Servo command error: " + err.message);
                }
            }, 100);
        }

        async function selectPresetAngle(ang) {
            onSliderInput(ang);
            await directMoveServo(ang);
        }

        async function triggerTestSweep() {
            showToast("Initiating Physical Servo Sweep Test...", "info");
            logEvent("SERVO", "Hardware Test Sweep initiated: 0° -> 45° -> 90° -> 135° -> 180° -> 0°");
            document.getElementById("servoOpStatusPill").innerText = "TEST SWEEPING...";
            document.getElementById("servoOpStatusPill").className = "status-pill status-warn";
            try {
                const res = await fetch(BASE_URL + "/api/test_servo_sweep", { method: "POST" });
                if (res.ok) {
                    showToast("Physical servo test sweep running on hardware!", "success");
                }
            } catch (err) {
                showToast("Sweep trigger error: " + err.message, "error");
            }
        }"""

if target_js in html:
    html = html.replace(target_js, replacement_js, 1)
    print("SUCCESS: selectPresetAngle and directMoveServo replaced!")
else:
    # Try with CRLF replacement
    html_crlf = html.replace('\r\n', '\n')
    target_js_crlf = target_js.replace('\r\n', '\n')
    replacement_js_crlf = replacement_js.replace('\r\n', '\n')
    if target_js_crlf in html_crlf:
        html = html_crlf.replace(target_js_crlf, replacement_js_crlf, 1)
        print("SUCCESS: selectPresetAngle replaced using CRLF normalization!")
    else:
        print("FAILED: target_js not found in studio_dashboard.html")

with open('studio_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Saved updated studio_dashboard.html!")
