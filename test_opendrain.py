import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("Stopping previous relay clicker...")
run("pkill -9 -f relay_clicker 2>/dev/null || true")

# Open-Drain toggle script:
# When in (High-Z) -> 5V optocoupler is completely OFF (LED OFF)
# When out, 0 -> 5V optocoupler is pulled to GND (LED ON, Relay CLICKS)
script = """
import time

while True:
    # State 1: OFF (Input / High-Z)
    with open('/sys/class/gpio/gpio54/direction', 'w') as f:
        f.write('in\\n')
    time.sleep(1.0)

    # State 2: ON (Output LOW)
    with open('/sys/class/gpio/gpio54/direction', 'w') as f:
        f.write('out\\n')
    with open('/sys/class/gpio/gpio54/value', 'w') as f:
        f.write('0\\n')
    time.sleep(1.0)
"""

with client.open_sftp().file('/tmp/opendrain_relay.py', 'w') as f:
    f.write(script)

run("pkill -9 -f opendrain_relay 2>/dev/null || true")
run("nohup python3 /tmp/opendrain_relay.py >/dev/null 2>&1 &")

ps = run("ps -ef | grep opendrain_relay | grep -v grep")
print("Open-drain relay clicker running:\n" + ps)
client.close()
