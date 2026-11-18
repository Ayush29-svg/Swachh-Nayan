import paramiko
import time

print("[DEPLOY] Connecting to Luckfox Pico at 172.32.0.93...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

sftp = client.open_sftp()
print("[DEPLOY] Uploading upgraded server_live.py to /userdata/swachh_nayan_v2/server_live.py...")
sftp.put("server_live_upgraded.py", "/userdata/swachh_nayan_v2/server_live.py")
sftp.close()
print("[DEPLOY] Upload complete.")

print("[DEPLOY] Restarting server_live.py service on Luckfox Pico...")
# Kill previous server_live.py process
client.exec_command("killall -9 python3 2>/dev/null || true")
time.sleep(1)

# Start new server_live.py in background
stdin, stdout, stderr = client.exec_command("nohup python3 /userdata/swachh_nayan_v2/server_live.py >> /userdata/swachh_nayan_v2/server_live.log 2>&1 &")
time.sleep(2)

# Verify process is running
stdin, stdout, stderr = client.exec_command("ps | grep server_live")
print("Process check:", stdout.read().decode())

client.close()
print("[DEPLOY] Deployment finished.")
