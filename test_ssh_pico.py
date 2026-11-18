import paramiko

passwords = ['luckfox', 'root', '', '123456', 'rockchip']
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

for p in passwords:
    try:
        print(f"Trying password: '{p}'...")
        client.connect('172.32.0.93', username='root', password=p, timeout=3)
        print(f"===> SUCCESS with password: '{p}' <===")
        stdin, stdout, stderr = client.exec_command('uname -a; whoami; ls -l /dev/video*')
        print("Output:\n" + stdout.read().decode())
        client.close()
        break
    except Exception as e:
        print(f"Failed with '{p}':", e)
