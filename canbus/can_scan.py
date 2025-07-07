"""
can_scan.py
────────────────────────────────────────────────────────
Iterate over a set of CAN bit-rates, bring the interface
up for each one, optionally inject a probe frame, and
print any traffic seen.

Requires:
  • python-can      (pip install python-can)
  • iproute2        (the `ip` command – already on Kali)
Run with sudo OR make sure your user can run `ip link`.

Usage examples
──────────────
# just listen at each speed for 2 seconds
python can_scan.py

# send a random 8-byte probe on every try
python can_scan.py --send

# scan only 500 k and 1 M with 5-second windows
python can_scan.py -b 500000 1000000 -t 5

"""
import argparse, os, subprocess, time, random, sys

try:
    import can
except ImportError:
    sys.exit("pip install python-can  (inside your venv)")

DEF_IFACE  = "can0"                             # slcan0 if using slcand
SCAN_RATES = [125_000, 250_000, 500_000, 1_000_000]

# ── sudo-wrapped ip-link ----------------------------------------------
def ip_link(cmd) -> None:
    full = ["sudo"] + cmd
    res  = subprocess.run(full, capture_output=True, text=True)
    if res.returncode:
        raise RuntimeError(res.stderr.strip() or "ip link error")

def set_bitrate(iface: str, bitrate: int) -> None:
    ip_link(["ip", "link", "set", iface, "down"])
    ip_link(["ip", "link", "set", iface, "type", "can",
             "bitrate", str(bitrate), "restart-ms", "100"])
    ip_link(["ip", "link", "set", iface, "up"])

# ── CLI ---------------------------------------------------------------
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--iface", default=DEF_IFACE,
                help=f"SocketCAN net-device (default {DEF_IFACE})")
ap.add_argument("-b", "--bitrates", type=int, nargs="+", default=SCAN_RATES,
                help="bit-rates to test in bit/s")
ap.add_argument("-t", "--time", type=float, default=2.0,
                help="seconds to listen at each rate")
ap.add_argument("--send", action="store_true",
                help="send an 8-byte random probe each cycle")
args = ap.parse_args()

# ── main loop ----------------------------------------------------------
for br in args.bitrates:
    print(f"\n=== {args.iface} @ {br//1000} kbit/s ===")
    try:
        set_bitrate(args.iface, br)
    except Exception as e:
        print(f"  !  could not set bit-rate: {e}")
        continue

    try:
        bus = can.interface.Bus(channel=args.iface, interface="socketcan")
    except Exception as e:
        print(f"  !  open error: {e}")
        continue

    if args.send:
        payload = os.urandom(8)
        msg = can.Message(arbitration_id=0x123, data=payload,
                          is_extended_id=False)
        try:
            bus.send(msg)
            print(f"  →  probe 123#{payload.hex()}")
        except can.CanError as e:
            print(f"  !  TX error: {e}")

    seen = False
    end  = time.time() + args.time
    while time.time() < end:
        m = bus.recv(timeout=0.25)
        if m:
            if not seen:
                print("  ←  traffic:")
                seen = True
            ts = f"{m.timestamp:.6f}"
            canid = f"{m.arbitration_id:08X}" if m.is_extended_id else f"{m.arbitration_id:03X}"
            print(f"    {ts}  {canid}  [{m.dlc}]  {m.data.hex()}")

    if not seen:
        print("  (silence)")
    bus.shutdown()

print("\nScan complete.")