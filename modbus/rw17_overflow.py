#!/usr/bin/env python3
"""
rw17_overflow.py  –  Function 0x17: read 1 reg, write 125 regs (250 B).
Legal but maximal; stresses heap in many stacks.
"""

import os, time, struct, serial, random

def crc(b):
    c=0xFFFF
    for x in b:
        c ^= x
        for _ in range(8):
            c=(c>>1)^0xA001 if c&1 else c>>1
    return struct.pack("<H",c)

ser=serial.Serial("/dev/cu.usbserial-BG018ZD3",115200,8,'N',2)

WR=125
payload=os.urandom(WR*2)
body=struct.pack(">B B H H H",1,0x17,0x0050,1,WR)+struct.pack(">B",WR*2)+payload
frame=body+crc(body)

while True:
    ser.write(frame)
    print("→ 0x17 125-reg frame sent")
    time.sleep(1)
