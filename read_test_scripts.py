import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

for f in ['/userdata/swachh_nayan/test_hardware.sh', '/userdata/swachh_nayan/test_servo_standalone.py']:
    print(f"=== {f} ===")
    stdin, stdout, stderr = client.exec_command(f"cat {f}")
    print(stdout.read().decode('utf-8', errors='replace'))

client.close()
