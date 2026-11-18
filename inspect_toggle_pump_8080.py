import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

stdin, stdout, stderr = client.exec_command("strings -t x /userdata/swachh_nayan/swachh_nayan_app | grep -C 5 toggle_pump")
print("Strings around toggle_pump:")
print(stdout.read().decode())

stdin, stdout, stderr = client.exec_command("curl -s http://127.0.0.1:8080/api/stats")
print("Stats response from 8080:")
print(stdout.read().decode())

stdin, stdout, stderr = client.exec_command("curl -s -X POST http://127.0.0.1:8080/api/toggle_pump")
print("Response of toggle_pump on 8080:")
print(stdout.read().decode())

client.close()
