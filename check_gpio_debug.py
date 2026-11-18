import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

cmds = [
    "grep -rn 'relay' /userdata/swachh_nayan* 2>/dev/null | head -n 30",
    "grep -rn 'GPIO' /userdata/swachh_nayan/hw_probe_all 2>/dev/null",
    "cat /sys/kernel/debug/gpio 2>/dev/null || cat /sys/class/gpio/gpio*/direction"
]

for cmd in cmds:
    print(f"=== {cmd} ===")
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))

client.close()
