#!/usr/bin/env python3
"""
broadcast_writer.py  –  Every 300 ms broadcasts Write-Single-Register
to 0x0051 with a random value.
"""

import os, time, serial, struct, random

def crc(b):
    c = 0xFFFF
    for x in b:
        c ^= x
        for _ in range(8):
            c = (c>>1) ^ 0xA001 if c & 1 else c >> 1
    return struct.pack("<H", c)

ser = serial.Serial("/dev/cu.usbserial-BG018ZD3", 115200, 8, 'N', 2)

while True:
    val  = random.randint(0, 0xFFFF)
    body = struct.pack(">BBHH", 0, 0x06, 0x0051, val)
    ser.write(body + crc(body))
    print(f"→ {val:04X}")
    time.sleep(0.3)
