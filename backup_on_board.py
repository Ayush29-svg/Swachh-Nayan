import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

# Backup the original server_live.py on the board first
stdin, stdout, stderr = client.exec_command("cp /userdata/swachh_nayan_v2/server_live.py /userdata/swachh_nayan_v2/server_live.py.orig_backup")
print("Board backup status:", stdout.read().decode(), stderr.read().decode())
client.close()
print("Backup created on Luckfox Pico: /userdata/swachh_nayan_v2/server_live.py.orig_backup")
