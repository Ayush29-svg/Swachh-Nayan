import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

sftp = client.open_sftp()
sftp.get('/userdata/swachh_nayan/hw_probe_all', 'hw_probe_all_local')
sftp.close()
client.close()
print("Downloaded hw_probe_all_local successfully!")
