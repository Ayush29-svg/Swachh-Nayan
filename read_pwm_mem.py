import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

remote_code = """
import mmap, struct
with open('/dev/mem', 'r+b') as f:
    m = mmap.mmap(f.fileno(), 4096, offset=0xff490000)
    words = struct.unpack('<16I', m[0x00:0x40])
    print('Memory at 0xff490000:')
    for i, w in enumerate(words):
        print('  0x{:02x}: 0x{:08x} ({})'.format(i*4, w, w))
"""

sftp = client.open_sftp()
with sftp.file('/tmp/mem_read.py', 'w') as f:
    f.write(remote_code)
sftp.close()

stdin, stdout, stderr = client.exec_command('python3 /tmp/mem_read.py')
print(stdout.read().decode())
err = stderr.read().decode()
if err: print('ERR:', err)
client.close()
