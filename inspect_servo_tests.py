import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

files_to_read = [
    "/userdata/swachh_nayan/test_servo_standalone.py",
    "/userdata/swachh_nayan_v2/tools/test_mg996r_pwm.py",
    "/userdata/swachh_nayan_v2/tools/hardware_diagnostics.py"
]

for f in files_to_read:
    print(f"==================== {f} ====================")
    stdin, stdout, stderr = client.exec_command(f"cat {f}")
    print(stdout.read().decode('utf-8', errors='replace'))

client.close()
