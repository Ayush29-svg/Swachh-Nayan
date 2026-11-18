import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

files_to_check = [
    "/userdata/swachh_nayan_v2/hal/relay.py",
    "/userdata/swachh_nayan_v2/hal/servo.py",
    "/userdata/swachh_nayan_v2/hal/controller.py"
]

for f in files_to_check:
    print(f"==================== {f} ====================")
    stdin, stdout, stderr = client.exec_command(f"cat {f}")
    print(stdout.read().decode())

client.close()
