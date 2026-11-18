import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("Listing pins around pin 55:")
print(run("cat /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pins | grep -E 'pin (5[0-9]|4[8-9])'"))

client.close()
