"""
Pre-flight connectivity checker.
Run before starting the full stack to verify all targets are reachable.

Usage:
    python scripts/test_connectivity.py
"""
import socket
import sys
import yaml
from pathlib import Path

CONFIG = Path("agents/server-agent/config/targets.yaml")


def check_tcp(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def check_udp_snmp(host: str, port: int = 161) -> str:
    """SNMP is UDP — we can only say the host DNS resolves."""
    try:
        socket.gethostbyname(host)
        return "dns_ok (UDP — actual SNMP test requires pysnmp)"
    except socket.gaierror:
        return "dns_fail"


def main():
    if not CONFIG.exists():
        print(f"Config not found: {CONFIG}")
        sys.exit(1)

    with open(CONFIG) as f:
        config = yaml.safe_load(f) or {}

    print("\n=== Windows Servers ===")
    for srv in config.get("windows_servers", []):
        host = srv["hostname"]
        method = srv.get("collection_method", "snmp")
        if method == "snmp":
            result = check_udp_snmp(host)
            print(f"  [{srv['id']}] {host} SNMP: {result}")
        else:
            ok = check_tcp(host, 5985)
            status = "OK" if ok else "FAIL (WinRM port 5985 unreachable)"
            print(f"  [{srv['id']}] {host} WinRM: {status}")

    vmware = config.get("vmware", {})
    if vmware.get("enabled") and vmware.get("vcenter", {}).get("host"):
        host = vmware["vcenter"]["host"]
        ok = check_tcp(host, 443)
        status = "OK" if ok else "FAIL (port 443 unreachable)"
        print(f"\n=== VMware vCenter ===")
        print(f"  {host}:443 HTTPS: {status}")

    print("\nDone.")


if __name__ == "__main__":
    main()
