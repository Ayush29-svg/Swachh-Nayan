import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("--- Checking devmem on PWM11 (0xff490030) ---")
read_regs_script = """
import mmap
import os
import struct

PAGE_SIZE = 4096
PWM11_BASE = 0xff490000
OFFSET = 0x30

try:
    with open('/dev/mem', 'r+b') as f:
        mem = mmap.mmap(f.fileno(), PAGE_SIZE, offset=PWM11_BASE)
        # Read 4 registers at OFFSET (0x30): CTRL, PERIOD, DUTY, COUNT
        ctrl, period, duty, count = struct.unpack('<IIII', mem[OFFSET:OFFSET+16])
        print(f'PWM11 Hardware Registers:')
        print(f'  CTRL:   0x{ctrl:08x}')
        print(f'  PERIOD: 0x{period:08x} ({period} clock cycles)')
        print(f'  DUTY:   0x{duty:08x} ({duty} clock cycles)')
        print(f'  COUNT:  0x{count:08x}')
except Exception as e:
    print('Register read error:', e)
"""

stdin, stdout, stderr = client.exec_command(f"python3 -c \"{read_regs_script}\"")
print(stdout.read().decode('utf-8', errors='replace'))
print('STDERR:', stderr.read().decode('utf-8', errors='replace'))

client.close()
