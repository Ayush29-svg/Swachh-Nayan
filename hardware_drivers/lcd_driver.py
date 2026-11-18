"""
Swachh Nayan — 16x2 I2C LCD Display Driver
Board: Luckfox Pico (RV1103) via PCF8574 I2C Backpack (/dev/i2c-1)
"""

import time
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class LCD1602I2CDriver:
    def __init__(self, bus_id=config.I2C_BUS, addr=config.I2C_LCD_ADDR):
        self.bus_id = bus_id
        self.addr = addr
        self.smbus_available = False
        self.bus = None

        try:
            import smbus2
            self.bus = smbus2.SMBus(self.bus_id)
            self.smbus_available = True
            self._lcd_init()
            print(f"[LCD] 16x2 I2C LCD initialized at address 0x{self.addr:02X} on bus {self.bus_id}")
        except Exception as e:
            print(f"[LCD] I2C Hardware unavailable ({e}). Operating in terminal simulation mode.")

    def _write_byte(self, data):
        if self.smbus_available and self.bus:
            try:
                self.bus.write_byte(self.addr, data)
            except Exception as e:
                pass

    def _toggle_enable(self, bits):
        time.sleep(0.0005)
        self._write_byte(bits | 0x04) # Enable High
        time.sleep(0.0005)
        self._write_byte(bits & ~0x04) # Enable Low
        time.sleep(0.0005)

    def _send_nibble(self, bits, mode):
        # mode: 0 for command, 1 for data
        data_bits = mode | (bits & 0xF0) | 0x08 # Backlight ON (0x08)
        self._write_byte(data_bits)
        self._toggle_enable(data_bits)

    def _send_byte(self, bits, mode):
        self._send_nibble(bits & 0xF0, mode)
        self._send_nibble((bits << 4) & 0xF0, mode)

    def _lcd_init(self):
        self._send_nibble(0x30, 0)
        self._send_nibble(0x30, 0)
        self._send_nibble(0x30, 0)
        self._send_nibble(0x20, 0) # 4-bit mode

        self._send_byte(0x28, 0) # 2 lines, 5x8 font
        self._send_byte(0x0C, 0) # Display ON, Cursor OFF
        self._send_byte(0x06, 0) # Entry mode: increment
        self.clear()

    def clear(self):
        self._send_byte(0x01, 0)
        time.sleep(0.002)

    def display_line(self, line, text):
        """Display text on line 1 or line 2 (max 16 chars)."""
        text = text.ljust(16)[:16]
        line_addr = 0x80 if line == 1 else 0xC0
        
        if self.smbus_available:
            self._send_byte(line_addr, 0)
            for char in text:
                self._send_byte(ord(char), 1)
        else:
            print(f"[LCD Line {line}]: |{text}|")

    def update_status(self, trash_count, status_str="SYSTEM READY"):
        """Convenience method to format live system status."""
        self.display_line(1, f"TRASH CT: {trash_count:04d}")
        self.display_line(2, status_str)


if __name__ == "__main__":
    lcd = LCD1602I2CDriver()
    lcd.update_status(0, "SWACHH NAYAN AI")
    time.sleep(2)
    lcd.update_status(1, "TRASH SCOOPING")
