with open('studio_dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

target = """                // If toggling or explicitly setting state
                let res;
                if (targetState !== confirmedMotorState) {
                    res = await fetch(BASE_URL + "/api/toggle_pump", { method: "POST" });
                } else {
                    res = { ok: true };
                }

                if (res.ok) {
                    confirmedMotorState = targetState;
                    applyMotorVisualState(targetState);
                    showToast(`12V DC Motor confirmed: ${targetState}`, "success");
                    logEvent("MOTOR", `12V DC Motor successfully confirmed ${targetState}.`);
                    document.getElementById("motorLastCmdTxt").innerText = `Switched ${targetState} at ` + new Date().toTimeString().split(" ")[0];
                } else {
                    throw new Error("Relay controller response error");
                }"""

replacement = """                // Send explicit ON / OFF state command to physical GPIO54 relay
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
                }"""

content_crlf = content.replace('\r\n', '\n')
target_crlf = target.replace('\r\n', '\n')
replacement_crlf = replacement.replace('\r\n', '\n')

if target_crlf in content_crlf:
    content_crlf = content_crlf.replace(target_crlf, replacement_crlf, 1)
    with open('studio_dashboard.html', 'w', encoding='utf-8', newline='') as f:
        f.write(content_crlf)
    print("SUCCESS: studio_dashboard.html updated!")
else:
    print("FAILED: Target not found.")
