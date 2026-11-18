import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

stdin, stdout, stderr = client.exec_command("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle; cat /sys/class/gpio/gpio56/value; cat /sys/class/gpio/gpio54/value")
print("Hardware states (PWM11 duty, GPIO56, GPIO54):")
print(stdout.read().decode())

stdin, stdout, stderr = client.exec_command("tail -n 30 /userdata/swachh_nayan_v2/server_live.log")
print("server_live.log tail:")
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
