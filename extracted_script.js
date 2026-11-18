
        // System Configuration
        let PICO_IP = window.location.hostname === "172.32.0.93" ? "172.32.0.93" : (window.location.hostname || "172.32.0.93");
        let PICO_PORT = window.location.port === "8088" ? "8088" : "8088";
        let BASE_URL = window.location.protocol + "//" + PICO_IP + ":" + PICO_PORT;
        if (window.location.protocol === "file:") {
            BASE_URL = "http://172.32.0.93:8088";
        }

        // State Machine
        let isServoBusy = false;
        let isMotorBusy = false;
        let isStreamPaused = false;
        let streamRefreshMs = 250;
        let streamTimer = null;
        let telemetryTimer = null;
        let confirmedServoAngle = 0.0;
        let commandedServoAngle = 90.0;
        let confirmedMotorState = "ON";

        // Initialization
        window.addEventListener("DOMContentLoaded", () => {
            initStream();
            startTelemetryPolling();
            updateServoVisuals(0.0);
            logEvent("SYS", "Hardware polling worker connected to port 8088.");
        });

        // Theme Switcher
        function toggleTheme() {
            const html = document.documentElement;
            const current = html.getAttribute("data-theme") || "dark";
            const next = current === "dark" ? "light" : "dark";
            html.setAttribute("data-theme", next);
            document.getElementById("themeIcon").innerText = next === "dark" ? "☀️" : "🌙";
            document.getElementById("themeLabel").innerText = next === "dark" ? "Light" : "Dark";
        }

        // Toast Notifications
        function showToast(message, type = "info") {
            const container = document.getElementById("toastContainer");
            const toast = document.createElement("div");
            toast.className = "toast";
            const icons = { info: "ℹ️", success: "✅", warn: "⚠️", error: "❌" };
            toast.innerHTML = `<span>${icons[type] || "ℹ️"}</span><span>${message}</span>`;
            container.appendChild(toast);
            setTimeout(() => {
                toast.style.opacity = "0";
                toast.style.transform = "translateX(100%)";
                setTimeout(() => toast.remove(), 300);
            }, 3200);
        }

        // Activity Logger
        function logEvent(tag, message) {
            const logBox = document.getElementById("activityLogBox");
            const entry = document.createElement("div");
            entry.className = "log-entry";
            const now = new Date().toTimeString().split(" ")[0];
            const tagClasses = {
                SERVO: "tag-servo",
                MOTOR: "tag-motor",
                VISION: "tag-vision",
                SYS: "tag-sys",
                ERR: "tag-err"
            };
            entry.innerHTML = `<span class="log-time">[${now}]</span><span class="log-tag ${tagClasses[tag] || "tag-sys"}">[${tag}]</span><span>${message}</span>`;
            logBox.appendChild(entry);
            logBox.scrollTop = logBox.scrollHeight;
        }

        function clearActivityLog() {
            document.getElementById("activityLogBox").innerHTML = "";
            logEvent("SYS", "Activity log cleared.");
        }

        // Camera Feed Pipeline (Dual-Buffer Smooth Refresh)
        function initStream() {
            if (streamTimer) clearInterval(streamTimer);
            if (isStreamPaused) return;

            streamTimer = setInterval(() => {
                refreshCameraFrame();
            }, streamRefreshMs);
        }

        function refreshCameraFrame() {
            if (isStreamPaused) return;
            const img = document.getElementById("liveCamImg");
            const nextImg = new Image();
            const timestamp = Date.now();
            nextImg.src = BASE_URL + "/snapshot.bmp?t=" + timestamp;
            nextImg.onload = () => {
                img.src = nextImg.src;
                document.getElementById("camStatusPill").innerText = "STREAM ONLINE";
                document.getElementById("camStatusPill").className = "status-pill status-idle";
                const d = new Date(timestamp);
                document.getElementById("frameTimeBadge").innerText = "Frame: " + d.toTimeString().split(" ")[0] + "." + String(d.getMilliseconds()).padStart(3, '0');
            };
            nextImg.onerror = () => {
                onCameraImgError();
            };
        }

        function manualRefreshSnapshot() {
            refreshCameraFrame();
            showToast("Camera frame refreshed", "info");
        }

        function toggleStreamPause() {
            isStreamPaused = !isStreamPaused;
            const btn = document.getElementById("btnPauseStream");
            if (isStreamPaused) {
                if (streamTimer) clearInterval(streamTimer);
                btn.innerHTML = "<span>▶</span> Resume Feed";
                document.getElementById("camStatusPill").innerText = "PAUSED";
                document.getElementById("camStatusPill").className = "status-pill status-warn";
                showToast("Live camera feed paused", "warn");
            } else {
                btn.innerHTML = "<span>⏸</span> Pause Feed";
                initStream();
                showToast("Live camera feed resumed", "info");
            }
        }

        function setRefreshInterval(ms) {
            streamRefreshMs = ms;
            document.querySelectorAll(".rate-btn").forEach(b => b.classList.remove("active"));
            if (ms === 250) document.getElementById("rate250").classList.add("active");
            if (ms === 500) document.getElementById("rate500").classList.add("active");
            if (ms === 1000) document.getElementById("rate1000").classList.add("active");
            initStream();
        }

        function toggleFullscreen() {
            const vp = document.getElementById("camViewport");
            if (!document.fullscreenElement) {
                vp.requestFullscreen().catch(err => alert("Fullscreen error: " + err.message));
            } else {
                document.exitFullscreen();
            }
        }

        function onCameraImgError() {
            document.getElementById("camStatusPill").innerText = "CONNECTING...";
            document.getElementById("camStatusPill").className = "status-pill status-alert";
        }

        // Servo Dial & Visual Gauge Helpers
        function updateServoVisuals(angle) {
            const clamped = Math.max(0, Math.min(180, parseFloat(angle)));
            // Arc progress (total arc is 251.2)
            const arcFrac = clamped / 180.0;
            const offset = 251.2 * (1.0 - arcFrac);
            document.getElementById("dialProgressPath").style.strokeDashoffset = offset;
            
            // Needle rotation: from 0 deg (needle at 0° which is pointing left/down) to 180 deg
            // Base needle x1=90 y1=85 x2=25 y2=85 (pointing 180° in standard math, or 0° of dial)
            document.getElementById("dialNeedle").style.transform = `rotate(${clamped}deg)`;
            document.getElementById("dialAngleText").textContent = Math.round(clamped) + "°";
            document.getElementById("confirmedAngleVal").textContent = clamped.toFixed(1) + "°";

            // Update physical gate cross-section flap rotation
            document.getElementById("gateFlapG").setAttribute("transform", `rotate(${clamped}, 130, 85)`);
            const flapState = document.getElementById("flapVisualState");
            if (clamped < 10) {
                flapState.innerText = "CLOSED (FLOW NORMAL)";
                flapState.style.color = "var(--color-success)";
            } else if (clamped > 60) {
                flapState.innerText = `DIVERTING ACTIVE (${Math.round(clamped)}°)`;
                flapState.style.color = "var(--color-alert)";
            } else {
                flapState.innerText = `PARTIAL (${Math.round(clamped)}°)`;
                flapState.style.color = "var(--color-warning)";
            }
        }

        function onSliderInput(val) {
            commandedServoAngle = parseFloat(val);
            document.getElementById("servoAngleInput").value = val;
            document.getElementById("commandedAngleVal").textContent = parseFloat(val).toFixed(1) + "°";
        }

        function onNumInput(val) {
            let v = parseFloat(val);
            if (isNaN(v)) v = 0;
            v = Math.max(0, Math.min(180, v));
            commandedServoAngle = v;
            document.getElementById("servoAngleSlider").value = v;
            document.getElementById("commandedAngleVal").textContent = v.toFixed(1) + "°";
        }

        let directServoDebounce = null;
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
        }

        // Servo Motor Control: Complete Validated Workflow
        async function executeServoMotionWorkflow() {
            if (isServoBusy) {
                showToast("Servo motion already in progress! Please wait.", "warn");
                return;
            }

            const target = Math.max(0, Math.min(180, parseFloat(document.getElementById("servoAngleInput").value)));
            const home = Math.max(0, Math.min(180, parseFloat(document.getElementById("homeAngleInput").value)));
            const holdSec = Math.max(0.2, Math.min(30, parseFloat(document.getElementById("holdDurationInput").value)));
            const autoReturn = document.getElementById("autoReturnCheck").checked;

            isServoBusy = true;
            document.getElementById("btnMoveServo").disabled = true;
            document.getElementById("servoOpStatusPill").innerText = `MOVING TO ${target}°`;
            document.getElementById("servoOpStatusPill").className = "status-pill status-active";
            logEvent("SERVO", `Initiating motion: Target=${target}°, Home=${home}°, Hold=${holdSec}s, AutoReturn=${autoReturn}`);

            try {
                // 1. Send Target Angle Command to Backend
                const res = await fetch(BASE_URL + "/api/set_servo_angle", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ angle: target })
                });

                if (!res.ok) throw new Error("Hardware rejected angle command");

                confirmedServoAngle = target;
                updateServoVisuals(target);
                showToast(`Servo moved to ${target}°`, "success");

                if (autoReturn) {
                    // 2. Holding Phase with Animated Progress Bar
                    document.getElementById("servoOpStatusPill").innerText = `HOLDING (${holdSec}s)`;
                    document.getElementById("servoOpStatusPill").className = "status-pill status-warn";
                    logEvent("SERVO", `Holding position at ${target}° for ${holdSec}s...`);

                    const prog = document.getElementById("servoWorkflowProgress");
                    prog.style.width = "0%";
                    const startT = Date.now();
                    const holdMs = holdSec * 1000;

                    await new Promise(resolve => {
                        const interval = setInterval(() => {
                            const elapsed = Date.now() - startT;
                            const pct = Math.min(100, (elapsed / holdMs) * 100);
                            prog.style.width = pct + "%";
                            if (elapsed >= holdMs) {
                                clearInterval(interval);
                                resolve();
                            }
                        }, 50);
                    });

                    // 3. Return to Home Phase
                    document.getElementById("servoOpStatusPill").innerText = `RETURNING TO ${home}°`;
                    document.getElementById("servoOpStatusPill").className = "status-pill status-active";
                    logEvent("SERVO", `Auto-Return triggered: Moving back to home position ${home}°...`);

                    const retRes = await fetch(BASE_URL + "/api/set_servo_angle", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ angle: home })
                    });

                    if (!retRes.ok) throw new Error("Hardware failed on return command");

                    confirmedServoAngle = home;
                    updateServoVisuals(home);
                    showToast(`Servo returned home to ${home}°`, "success");
                    logEvent("SERVO", `Servo successfully returned home to ${home}°. Cycle complete.`);
                }
            } catch (err) {
                showToast("Servo Error: " + err.message, "error");
                logEvent("ERR", "Servo motion failure: " + err.message);
            } finally {
                isServoBusy = false;
                document.getElementById("btnMoveServo").disabled = false;
                document.getElementById("servoWorkflowProgress").style.width = "0%";
                document.getElementById("servoOpStatusPill").innerText = `IDLE (${confirmedServoAngle.toFixed(1)}°)`;
                document.getElementById("servoOpStatusPill").className = "status-pill status-idle";
            }
        }

        async function returnServoHome() {
            if (isServoBusy) return;
            const home = Math.max(0, Math.min(180, parseFloat(document.getElementById("homeAngleInput").value)));
            try {
                await fetch(BASE_URL + "/api/set_servo_angle", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ angle: home })
                });
                confirmedServoAngle = home;
                updateServoVisuals(home);
                showToast(`Servo returned home to ${home}°`, "success");
                logEvent("SERVO", `Manual Return Home executed: position=${home}°`);
            } catch (err) {
                showToast("Return Home failed: " + err.message, "error");
            }
        }

        async function forceServoClose() {
            try {
                await fetch(BASE_URL + "/api/force_close", { method: "POST" });
                confirmedServoAngle = 0.0;
                updateServoVisuals(0.0);
                showToast("Servo closed to 0°", "info");
                logEvent("SERVO", "Force close executed: 0.0°");
            } catch (e) {
                showToast("Force close error", "error");
            }
        }

        // DC Motor Control Workflow (ON / OFF / Toggle)
        async function setDcMotorState(targetState) {
            if (isMotorBusy) return;
            isMotorBusy = true;

            const pill = document.getElementById("motorStatusPill");
            const txt = document.getElementById("motorStatusTxt");
            pill.innerText = "COMMANDING...";
            pill.className = "status-pill status-warn";
            txt.innerText = `SWITCHING TO: ${targetState}...`;
            txt.style.color = "var(--color-warning)";

            logEvent("MOTOR", `Command sent: Turn DC Motor ${targetState} (Relay Pin 5 / GPIO54)`);

            try {
                // Send explicit ON / OFF state command to physical GPIO54 relay
                const res = await fetch(BASE_URL + "/api/set_motor", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ state: targetState })
                });

                if (res.ok) {
                    const data = await res.json().catch(() => ({ state: targetState }));
                    const finalState = data.state || targetState;
                    confirmedMotorState = finalState;
                    applyMotorVisualState(finalState);
                    showToast(`12V DC Motor confirmed: ${finalState}`, "success");
                    logEvent("MOTOR", `12V DC Motor confirmed ${finalState} (GPIO54 relay switch active).`);
                    document.getElementById("motorLastCmdTxt").innerText = `Switched ${finalState} at ` + new Date().toTimeString().split(" ")[0];
                } else {
                    throw new Error("Relay controller response error");
                }
            } catch (err) {
                showToast("Motor Control Error: " + err.message, "error");
                logEvent("ERR", "DC Motor toggle error: " + err.message);
                applyMotorVisualState(confirmedMotorState);
            } finally {
                isMotorBusy = false;
            }
        }

        function toggleDcMotorFromRocker() {
            const next = confirmedMotorState === "ON" ? "OFF" : "ON";
            setDcMotorState(next);
        }

        function applyMotorVisualState(state) {
            const rocker = document.getElementById("motorRocker");
            const pill = document.getElementById("motorStatusPill");
            const txt = document.getElementById("motorStatusTxt");
            const turbine = document.getElementById("turbineSvg");

            if (state === "ON") {
                rocker.classList.add("on");
                pill.innerText = "RUNNING (ON)";
                pill.className = "status-pill status-active";
                txt.innerText = "MOTOR CONFIRMED: ON";
                txt.style.color = "var(--color-success)";
                turbine.classList.add("turbine-running");
            } else {
                rocker.classList.remove("on");
                pill.innerText = "STOPPED (OFF)";
                pill.className = "status-pill status-idle";
                txt.innerText = "MOTOR CONFIRMED: OFF";
                txt.style.color = "var(--text-muted)";
                turbine.classList.remove("turbine-running");
            }
        }

        // Auto-Divert Toggle
        async function toggleAutoDivert() {
            try {
                const res = await fetch(BASE_URL + "/api/toggle_auto_divert", { method: "POST" });
                const d = await res.json();
                const isAuto = d.auto_divert;
                updateAutoDivertUi(isAuto);
                showToast("Auto-divert mode: " + (isAuto ? "ARMED" : "STANDBY"), "info");
                logEvent("SYS", "Auto-Divert mode switched to: " + (isAuto ? "ARMED (AUTO ON)" : "STANDBY (MANUAL)"));
            } catch (e) {
                showToast("Failed to toggle auto divert", "error");
            }
        }

        function updateAutoDivertUi(isAuto) {
            const pill = document.getElementById("autoModePill");
            const btn = document.getElementById("autoBtnText");
            if (isAuto) {
                pill.innerText = "ARMED (AUTO ON)";
                pill.className = "status-pill status-alert";
                btn.innerText = "STANDBY";
            } else {
                pill.innerText = "MANUAL STANDBY";
                pill.className = "status-pill status-active";
                btn.innerText = "ARM AUTO";
            }
        }

        async function resetTrashCounter() {
            if (!confirm("Are you sure you want to reset the trash counter?")) return;
            try {
                await fetch(BASE_URL + "/api/reset_trash_counter", { method: "POST" });
                document.getElementById("trashCountDisplay").innerText = "0";
                document.getElementById("massDisplay").innerText = "0.00 kg";
                showToast("Trash counter reset to zero", "info");
                logEvent("VISION", "Trash collection counter reset to 0.");
            } catch (e) {
                showToast("Failed to reset counter", "error");
            }
        }

        async function emergencyPark() {
            showToast("Emergency Park: Halting DC Motor & Closing Flap...", "warn");
            logEvent("SYS", "EMERGENCY PARK TRIGGERED: Halting pump and resetting flap to 0°.");
            try {
                await setDcMotorState("OFF");
                await forceServoClose();
            } catch (e) {
                console.error(e);
            }
        }

        // Live Telemetry Poller
        function startTelemetryPolling() {
            if (telemetryTimer) clearInterval(telemetryTimer);
            telemetryTimer = setInterval(pollTelemetry, 1000);
            pollTelemetry();
        }

        async function pollTelemetry() {
            try {
                const res = await fetch(BASE_URL + "/api/live_telemetry");
                if (!res.ok) throw new Error("Telemetry HTTP " + res.status);
                const d = await res.json();

                // 1. Connection status
                document.getElementById("connDot").style.backgroundColor = "var(--color-success)";
                document.getElementById("connLabel").innerText = "PICO CONNECTED (172.32.0.93)";

                // 2. Counters & Metrics
                document.getElementById("trashCountDisplay").innerText = d.trash_diverted || 0;
                const mass = ((d.trash_diverted || 0) * 0.024).toFixed(2);
                document.getElementById("massDisplay").innerText = mass + " kg";

                // 3. Water Depth (HC-SR04)
                const dist = d.ultrasonic_distance_cm || 0;
                const depth = d.water_depth_cm || 0;
                const pct = Math.max(0, Math.min(100, d.water_percentage || 0));
                document.getElementById("waterDepthTxt").innerText = `${depth.toFixed(1)} cm (Distance: ${dist.toFixed(1)} cm)`;
                document.getElementById("waterProgress").style.width = pct + "%";

                // 4. Hardware PWM11 Stats
                document.getElementById("pwmDutyTxt").innerText = `${(d.servo_duty_ns || 1000000).toLocaleString()} ns (${(d.servo_pulse_ms || 1.0).toFixed(3)} ms)`;

                // 5. FPS & Latency
                const fps = d.camera_fps || 0;
                document.getElementById("fpsLatencyBadge").innerText = `${fps.toFixed(1)} FPS | Core: ${d.core_temp || "45°C"}`;

                // 6. Confirmed Motor State from Backend
                if (d.pump_status && !isMotorBusy) {
                    confirmedMotorState = d.pump_status;
                    applyMotorVisualState(d.pump_status);
                }

                // 7. Confirmed Servo Angle from Backend
                if (d.servo_angle !== undefined && !isServoBusy) {
                    confirmedServoAngle = d.servo_angle;
                    updateServoVisuals(d.servo_angle);
                    document.getElementById("servoOpStatusPill").innerText = `IDLE (${confirmedServoAngle.toFixed(1)}°)`;
                }

                // 8. Auto-divert status
                if (d.auto_divert !== undefined) {
                    updateAutoDivertUi(d.auto_divert);
                }

            } catch (err) {
                document.getElementById("connDot").style.backgroundColor = "var(--color-alert)";
                document.getElementById("connLabel").innerText = "DISCONNECTED (Retrying...)";
            }
        }
    