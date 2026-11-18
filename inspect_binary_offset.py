import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

stdin, stdout, stderr = client.exec_command("grep -a -b -o '/sys/class/pwm/pwmchip11/pwm0/duty_cycle' /userdata/swachh_nayan/swachh_nayan_app")
print("Offsets of duty_cycle in swachh_nayan_app:")
print(stdout.read().decode())

stdin, stdout, stderr = client.exec_command("strings -t x /userdata/swachh_nayan/swachh_nayan_app | grep duty_cycle")
print("Hex offset:")
print(stdout.read().decode())

client.close()
