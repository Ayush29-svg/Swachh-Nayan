import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

cmds = [
    "ls -ld /sys/class/gpio/gpio54 2>/dev/null || echo 'not exported'",
    "python3 -c 'from hal.relay import PumpRelay; r = PumpRelay(); print(\"PumpRelay init success, is_on:\", r.is_on())' 2>&1"
]

for cmd in cmds:
    print(f"=== {cmd} ===")
    stdin, stdout, stderr = client.exec_command(f"cd /userdata/swachh_nayan_v2 && {cmd}")
    print(stdout.read().decode('utf-8', errors='replace'))

client.close()
