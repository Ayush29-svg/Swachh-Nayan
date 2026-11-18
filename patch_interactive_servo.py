import re

with open('studio_dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

replacement_js = """let directServoDebounce = null;
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

pattern = r'function\s+selectPresetAngle\s*\(ang\)\s*\{[\s\S]*?showToast[\s\S]*?\}'
new_html, count = re.subn(pattern, replacement_js, html, count=1)
print(f"Replaced {count} occurrences of selectPresetAngle!")

with open('studio_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Saved updated studio_dashboard.html!")
