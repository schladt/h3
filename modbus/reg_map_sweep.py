#!/usr/bin/env python3
"""
reg_map_sweep.py  –  Enumerate the Modbus-RTU holding-register map
on the DSE899 without mistaking bus chatter for data.

• Scans 0x0000-0xFFFF (1 → 65536).
• Prints only registers that return a valid, CRC-correct 2-byte value.
• Works at 115 200 bps, 8-N-2.
"""

import serial, struct, time

PORT = "/dev/cu.usbserial-BG018ZD3"
BAUD = 115_200

ser = serial.Serial(PORT, BAUD, bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO,
                    timeout=0.05)

def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc & 0xFFFF

def le_crc(data: bytes) -> bytes:
    return struct.pack("<H", crc16(data))

def read_reply(expected_reg: int) -> bytes | None:
    """Return data bytes if reply matches our query, else None."""
    hdr = ser.read(3)                        # slave, func, byte-count
    if len(hdr) < 3:
        return None
    sid, func, bc = hdr
    payload = ser.read(bc + 2)               # data + CRC
    frame = hdr + payload
    if len(payload) != bc + 2:
        return None                          # frame incomplete
    if le_crc(frame[:-2]) != frame[-2:]:
        return None                          # CRC fail
    if sid != 1 or func != 3 or bc != 2:
        return None                          # not our 1-register reply
    # Verify the register echoed in the RTU frame (address is in request only),
    # so we just trust order: if we get here, assume it’s for the last request.
    return frame[3:-2]                       # two-byte data field

print(f"[+] Sweeping registers via {PORT} @ {BAUD} 8-N-2")
for reg in range(0x0000, 0x10000):
    # Build 01 03 <regHi> <regLo> 00 01 CRC
    req_body = struct.pack(">BBHH", 1, 3, reg, 1)
    ser.write(req_body + le_crc(req_body))
    time.sleep(0.01)                         # 10 ms spacing prevents collisions
    data = read_reply(reg)
    if data:
        val = struct.unpack(">H", data)[0]
        print(f"0x{reg:04X}  0x{val:04X}")
