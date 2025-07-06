#!/usr/bin/env python3
"""
rs485_fuzz.py
-----------------------------------------
• Logs every frame on the RS-485 line
• Acts as Modbus-RTU slave (ID default 1)
• Can fuzz replies on a schedule

Run   python rs485_fuzz.py  --help   for flags.

Requires:  pip install pyserial
"""

import sys, argparse, time, random, serial, struct, textwrap
from binascii import crc_hqx

# ---------- serial & protocol defaults ----------
PORT_DEFAULT = "/dev/cu.usbserial-BG018ZD3"   # change if needed
BAUD         = 115_200                        # confirmed speed
BYTESIZE     = serial.EIGHTBITS
PARITY       = serial.PARITY_NONE
STOPBITS     = serial.STOPBITS_TWO            # 8-N-2 framing

SLAVE_ID  = 0x01          # DSE899 polls slave 1 by default
POLL_REG  = 0x0051        # register it keeps reading
POLL_CNT  = 0x0001

FUZZ_STYLES = ("crc", "func", "big", "rand")  # four flavours
# -----------------------------------------------------------

def crc(frame: bytes) -> bytes:
    """True Modbus CRC-16 (poly 0xA001, init 0xFFFF) – little-endian"""
    crc_val = 0xFFFF
    for b in frame:
        crc_val ^= b
        for _ in range(8):
            if crc_val & 1:
                crc_val = (crc_val >> 1) ^ 0xA001
            else:
                crc_val >>= 1
    return struct.pack("<H", crc_val)

# -----------------------------------------------



def good_response():
    # Build: 01 03 02 <hi> <lo> CRC
    val  = random.randint(0, 0xFFFF)
    body = struct.pack(">BBBH", SLAVE_ID, 0x03, 0x02, val)
    return body + crc(body)

# -- fuzzers ------------------------------------------------
def fuzz_crc(frame):                     # body OK, CRC zeroed
    return frame[:-2] + b"\x00\x00"

def fuzz_illegal_function():
    body = struct.pack(">BBBB", SLAVE_ID, 0x04, 0x00, 0x00)
    return body + crc(body)

def fuzz_big_count():
    BIG = 252                       # maximum spec-conformant data bytes
    body    = struct.pack(">BBBH", SLAVE_ID, 0x03, BIG, 0x0000)
    payload = bytes(range(256))[:BIG]          # 0x00…0xFB
    return body + payload + crc(body + payload)




def fuzz_random():
    payload = bytes(random.getrandbits(8) for _ in range(random.randint(5,50)))
    body    = struct.pack(">B", SLAVE_ID) + payload
    return body + crc(body)

FUZZ_MAP = {"crc": fuzz_crc,
            "func": lambda _: fuzz_illegal_function(),
            "big":  lambda _: fuzz_big_count(),
            "rand": lambda _: fuzz_random()}
# -----------------------------------------------------------

def hexline(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)

def parse_cli():
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="RS-485 logger / responder / fuzzer for DSE899",
        epilog=textwrap.dedent("""\
            Examples:
              python rs485_fuzz.py
              python rs485_fuzz.py --fuzz 8 --fuzz-type crc
              python rs485_fuzz.py --port /dev/cu.usbserial-FT4Z --id 5
        """))
    p.add_argument("--port",      default=PORT_DEFAULT)
    p.add_argument("--id",        type=lambda x:int(x,0), default=SLAVE_ID,
                   help="slave address in hex/dec (default 1)")
    p.add_argument("--fuzz",      type=int, default=0,
                   help="inject fuzz every N polls (0 = never)")
    p.add_argument("--fuzz-type", choices=FUZZ_STYLES,
                   help="choose one fuzz style (default: rotate)")
    return p.parse_args()

def main():
    opts = parse_cli()
    global SLAVE_ID; SLAVE_ID = opts.id

    ser = serial.Serial(opts.port, BAUD, BYTESIZE, PARITY, STOPBITS, timeout=0.05)
    print(f"[+] Listening on {ser.port} 115200-8N2  as slave {SLAVE_ID}")

    poll, fuzz_cycle = 0, list(FUZZ_STYLES)
    while True:
        if (head := ser.read(1)) != bytes([SLAVE_ID]):
            continue                    # not addressed to us

        req = head + ser.read(7)        # full 8-byte request
        if len(req) < 8:
            continue
        print(f"←  {hexline(req)}")

        if crc(req[:-2]) != req[-2:]:
            print("   [!] bad CRC in request")
            continue

        func, reg, cnt = req[1], *struct.unpack(">HH", req[2:6])

        # Decide whether to fuzz
        if opts.fuzz and poll % opts.fuzz == 0:
            style = opts.fuzz_type or fuzz_cycle[(poll // opts.fuzz) % 4]
            frame = FUZZ_MAP[style](req)
            ser.write(frame)
            print(f"→  (FUZZ:{style}) {hexline(frame)}")
            poll += 1
            continue

        # Normal reply or exception
        if func == 0x03 and reg == POLL_REG and cnt == POLL_CNT:
            resp = good_response()
            ser.write(resp)
            print(f"→  {hexline(resp)}  (ok)")
        else:
            exc  = struct.pack(">BBB", SLAVE_ID, func | 0x80, 0x02)
            ser.write(exc + crc(exc))
            print(f"→  {hexline(exc + crc(exc))}  (exc)")

        poll += 1

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[+] Stopped")
