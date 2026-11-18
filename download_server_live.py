import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

sftp = client.open_sftp()
sftp.get("/userdata/swachh_nayan_v2/server_live.py", "server_live_backup.py")
sftp.close()
client.close()
print("Downloaded server_live.py to local server_live_backup.py successfully!")
