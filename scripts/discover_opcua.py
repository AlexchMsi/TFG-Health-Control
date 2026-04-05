"""
discover_opcua.py — Test OPC UA connectivity before adding a target.

Usage:
    python scripts/discover_opcua.py --host 10.10.5.50 --port 4840
    python scripts/discover_opcua.py --url opc.tcp://10.10.5.50:4840
"""

import argparse
import asyncio
import sys

from asyncua import Client


async def probe(url: str, timeout: int) -> None:
    print(f"Connecting to {url} (timeout={timeout}s)...")
    async with Client(url=url, timeout=timeout) as client:
        # Read server state
        state_node = client.get_node("ns=0;i=2259")
        state = await state_node.read_value()
        state_names = {
            0: "Running", 1: "Failed", 2: "NoConfig",
            3: "Suspended", 4: "Shutdown", 5: "Test",
            6: "CommunicationFault", 7: "Unknown",
        }
        print(f"  Server state : {state_names.get(state, state)} ({state})")

        # Read server name
        try:
            name_node = client.get_node("ns=0;i=2261")
            name = await name_node.read_value()
            print(f"  Product name : {name}")
        except Exception:
            pass

        # Try to list root objects
        objects = client.get_node("ns=0;i=85")
        children = await objects.get_children()
        print(f"  Root objects ({len(children)}):")
        for child in children[:10]:
            try:
                browse_name = await child.read_browse_name()
                print(f"    - {browse_name.Name}")
            except Exception:
                pass

    print("\nOPC UA connection successful.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test OPC UA connectivity")
    parser.add_argument("--url", help="Full OPC UA endpoint URL")
    parser.add_argument("--host", help="PLC IP address")
    parser.add_argument("--port", type=int, default=4840, help="OPC UA port (default 4840)")
    parser.add_argument("--timeout", type=int, default=10, help="Connection timeout in seconds")
    args = parser.parse_args()

    if args.url:
        url = args.url
    elif args.host:
        url = f"opc.tcp://{args.host}:{args.port}"
    else:
        parser.print_help()
        sys.exit(1)

    try:
        asyncio.run(probe(url, args.timeout))
    except Exception as exc:
        print(f"\nFailed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
