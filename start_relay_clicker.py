import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("Setting up continuous 1-second Relay Clicker on Pin 5 (GPIO 54)...")
run("echo 54 > /sys/class/gpio/export 2>/dev/null || true")
run("echo out > /sys/class/gpio/gpio54/direction 2>/dev/null || true")

script = """
import time

while True:
    try:
        with open('/sys/class/gpio/gpio54/value', 'w') as f:
            f.write('1\\n')
    except:
        pass
    time.sleep(1.0)
    try:
        with open('/sys/class/gpio/gpio54/value', 'w') as f:
            f.write('0\\n')
    except:
        pass
    time.sleep(1.0)
"""

with client.open_sftp().file('/tmp/relay_clicker.py', 'w') as f:
    f.write(script)

run("pkill -9 -f relay_clicker 2>/dev/null || true")
run("nohup python3 /tmp/relay_clicker.py >/dev/null 2>&1 &")

ps = run("ps -ef | grep relay_clicker | grep -v grep")
print("Process status:\n" + ps)
client.close()
print("Relay clicker is NOW RUNNING CONTINUOUSLY on Pin 5!")
