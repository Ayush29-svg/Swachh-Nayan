import paramiko
import time
import requests

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("1. Uploading server_live_final.py to Luckfox Pico...")
sftp = client.open_sftp()
sftp.put("server_live_final.py", "/userdata/swachh_nayan_v2/server_live.py")
sftp.close()
print("   Uploaded successfully.")

print("2. Stopping any running server_live.py processes...")
run("killall -9 python3 2>/dev/null || true")
time.sleep(1)

print("3. Launching fresh unbuffered server_live.py...")
run("nohup python3 -u /userdata/swachh_nayan_v2/server_live.py >> /userdata/swachh_nayan_v2/server_live.log 2>&1 &")
time.sleep(2)

print("4. Checking process status on Pico...")
ps_out = run("ps | grep python")
print("   Running python processes:\n" + ps_out)

client.close()

print("5. Verifying HTTP responses on port 8088...")
for attempt in range(5):
    try:
        r = requests.get("http://172.32.0.93:8088/", timeout=3)
        if r.status_code == 200:
            print(f"   [SUCCESS] Port 8088 online! Dashboard size: {len(r.text)} bytes")
            break
    except Exception as e:
        print(f"   Waiting for server (attempt {attempt+1})...")
        time.sleep(1)

t_res = requests.get("http://172.32.0.93:8088/api/live_telemetry", timeout=3)
print("   Telemetry check:", t_res.json().get("gate_status"), "servo_angle:", t_res.json().get("servo_angle"))
print("\nDEPLOYMENT COMPLETE!")
