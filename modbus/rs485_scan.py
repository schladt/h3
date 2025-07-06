#!/usr/bin/env python3
"""
rs485_finder.py  –  banner / framing sweeper for serial links

Usage:
    python rs485_finder.py /dev/cu.usbserial-BG018ZD3  [seconds_to_listen]

If no response times are given it listens 0.4 s per test.
"""

import sys, time, itertools, serial
from textwrap import dedent

# -------------------- user-tweakables --------------------
# BAUDS    = [4800, 9600, 14400, 19200, 28800,
#             38400, 57600, 115200]
BAUDS    = [115200]
PARITIES = {'N': serial.PARITY_NONE,
            'E': serial.PARITY_EVEN,
            'O': serial.PARITY_ODD}
BYTESIZE = {7: serial.SEVENBITS,
            8: serial.EIGHTBITS}
STOPBITS = {1: serial.STOPBITS_ONE,
            2: serial.STOPBITS_TWO}
TEST_PAYLOAD = b'\r'          # what we transmit each trial
# ---------------------------------------------------------

def hexdump(data: bytes, width: int = 16) -> str:
    """return a printable hex+ASCII line for bytes"""
    s = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hexpart = ' '.join(f'{b:02X}' for b in chunk).ljust(width*3-1)
        txtpart = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        s.append(f"{hexpart}  {txtpart}")
    return '\n    '.join(s)

def main():
    if len(sys.argv) < 2:
        print(dedent("""\
            Usage: python rs485_finder.py <serial_device> [listen_seconds]
            Example: python rs485_finder.py /dev/cu.usbserial-FTXYZ 0.2"""))
        sys.exit(1)

    port   = sys.argv[1]
    dwell  = float(sys.argv[2]) if len(sys.argv) > 2 else 0.4

    combos = list(itertools.product(BAUDS, PARITIES.items(),
                                    BYTESIZE.items(), STOPBITS.items()))
    print(f"Scanning {len(combos)} permutations on {port}\n")

    for baud, (par_char, parity), (bits, bytesize), (stops, stopbits) in combos:
        label = (f"{baud:6d} {bits}{par_char}{stops}")
        try:
            with serial.Serial(port=port,
                               baudrate=baud,
                               bytesize=bytesize,
                               parity=parity,
                               stopbits=stopbits,
                               timeout=dwell) as ser:
                # Flush & probe
                ser.reset_input_buffer()
                ser.write(TEST_PAYLOAD)
                time.sleep(0.01)         # Give DE line time to release
                data = ser.read(128)

            if data:
                print(f"[+] {label}: {len(data)} byte(s)")
                print(f"    {hexdump(data)}")
            else:
                print(f"[-] {label}: silence")
        except serial.SerialException as e:
            print(f"[!] {label}: {e}")

if __name__ == "__main__":
    main()

