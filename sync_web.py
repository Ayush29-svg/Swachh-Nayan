import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

sftp = client.open_sftp()
sftp.put("studio_dashboard.html", "/userdata/swachh_nayan_v2/web/index.html")
sftp.close()
client.close()
print("Synchronized studio_dashboard.html to /userdata/swachh_nayan_v2/web/index.html successfully!")
