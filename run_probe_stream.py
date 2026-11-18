import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

channel = client.get_transport().open_session()
channel.exec_command('/userdata/swachh_nayan/hw_probe_all')

start = time.time()
while time.time() - start < 15:
    if channel.recv_ready():
        data = channel.recv(1024).decode('utf-8', errors='replace')
        print(data, end='', flush=True)
    if channel.exit_status_ready():
        break
    time.sleep(0.2)

client.close()
