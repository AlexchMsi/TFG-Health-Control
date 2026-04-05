"""
discover_snap7.py — Test Snap7 connectivity and read basic PLC info.

Usage:
    python scripts/discover_snap7.py --host 10.10.5.50
    python scripts/discover_snap7.py --host 10.10.5.50 --rack 0 --slot 1
"""

import argparse
import sys

import snap7


def probe(host: str, rack: int, slot: int) -> None:
    print(f"Connecting to {host} (rack={rack}, slot={slot})...")
    client = snap7.client.Client()
    client.set_connection_type(1)  # PG connection — read-only
    client.connect(host, rack, slot)

    # CPU info
    info = client.get_cpu_info()
    print(f"  Module type  : {info.ModuleTypeName.decode('utf-8', errors='replace').strip(chr(0))}")
    print(f"  Firmware     : {info.SWVersion.decode('utf-8', errors='replace').strip(chr(0))}")
    print(f"  Serial       : {info.SerialNumber.decode('utf-8', errors='replace').strip(chr(0))}")

    # CPU state
    state = client.get_cpu_state()
    print(f"  CPU state    : {state}")

    # Memory (SZL 0x0090)
    try:
        szl = client.read_szl(0x0090, 0)
        if szl and len(szl.list) > 0:
            print(f"  SZL 0x0090   : OK ({len(szl.list)} entries)")
    except Exception as e:
        print(f"  SZL 0x0090   : {e}")

    client.disconnect()
    print("\nSnap7 connection successful.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Snap7 connectivity")
    parser.add_argument("--host", required=True, help="PLC IP address")
    parser.add_argument("--rack", type=int, default=0, help="Rack number (default 0)")
    parser.add_argument("--slot", type=int, default=1, help="Slot number (default 1)")
    args = parser.parse_args()

    try:
        probe(args.host, args.rack, args.slot)
    except Exception as exc:
        print(f"\nFailed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
