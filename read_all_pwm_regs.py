import mmap
import struct

PAGE_SIZE = 4096
PWM_BASE = 0xff490000

with open('/dev/mem', 'r+b') as f:
    mem = mmap.mmap(f.fileno(), PAGE_SIZE, offset=PWM_BASE)
    for ch, off in [('PWM8', 0x00), ('PWM9', 0x10), ('PWM10', 0x20), ('PWM11', 0x30)]:
        r0, r1, r2, r3 = struct.unpack('<IIII', mem[off:off+16])
        print(f"{ch} (0x{PWM_BASE+off:08x}):")
        print(f"  reg0 (DUTY):   0x{r0:08x} ({r0})")
        print(f"  reg1 (PERIOD): 0x{r1:08x} ({r1})")
        print(f"  reg2 (COUNT):  0x{r2:08x} ({r2})")
        print(f"  reg3 (CTRL):   0x{r3:08x} ({r3})")
