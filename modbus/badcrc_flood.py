#!/usr/bin/env python3
"""
badcrc_flood.py  –  Streams 10 kB random bytes with zero CRC every 50 ms.
Aims to overrun UART RX FIFO / ISR.
"""

import os, serial, time

PORT="/dev/cu.usbserial-BG018ZD3"
ser = serial.Serial(PORT,115200,8,'N',2)

CHUNK = os.urandom(10_000) + b"\x00\x00"   # bogus CRC
while True:
    ser.write(CHUNK)
    time.sleep(0.05)
