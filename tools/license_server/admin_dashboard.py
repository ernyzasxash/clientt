#!/usr/bin/env python3
import requests
import json
import sys
from tabulate import tabulate
from datetime import datetime

BASE_URL = "http://localhost:5000"
ADMIN_TOKEN = "your_admin_token_here"

def api_call(endpoint, method="GET", data=None):
    """Make API call to license server"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"X-Admin-Token": ADMIN_TOKEN, "Content-Type": "application/json"}
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=5)
        else:
            resp = requests.post(url, headers=headers, json=data, timeout=5)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def format_time(iso_time):
    """Format ISO timestamp to readable format"""
    try:
        dt = datetime.fromisoformat(iso_time)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_time

def cmd_connections():
    """Show active connections"""
    result = api_call("/admin/connections")
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    conns = result.get('connections', [])
    if not conns:
        print("No active connections")
        return
    
    table_data = []
    for c in conns:
        table_data.append([
            c.get('ip'),
            c.get('asn', 'N/A'),
            c.get('org', 'N/A')[:30],
            c.get('device_name', 'Unknown'),
            c.get('key', 'N/A')[:20],
            format_time(c.get('timestamp', ''))
        ])
    
    headers = ["IP", "ASN", "Organization", "Device", "Key", "Connected"]
    print("\n=== ACTIVE CONNECTIONS ===")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"\nTotal: {len(conns)} active connection(s)")

def cmd_failed_logins():
    """Show failed login attempts"""
    result = api_call("/admin/failed-logins")
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    failed = result.get('failed', [])
    if not failed:
        print("No failed logins")
        return
    
    table_data = []
    for f in failed[-20:]:  # Show last 20
        table_data.append([
            f.get('ip'),
            f.get('asn', 'N/A'),
            f.get('key', 'N/A')[:20],
            f.get('device_name', 'Unknown'),
            format_time(f.get('timestamp', ''))
        ])
    
    headers = ["IP", "ASN", "Key", "Device", "Timestamp"]
    print("\n=== FAILED LOGIN ATTEMPTS (Last 20) ===")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"\nTotal failed attempts: {len(failed)}")

def cmd_bans():
    """List all bans"""
    result = api_call("/admin/bans")
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    bans = result.get('bans', [])
    if not bans:
        print("No bans")
        return
    
    table_data = []
    for b in bans:
        table_data.append([
            b.get('type').upper(),
            b.get('value'),
            b.get('reason', ''),
            format_time(b.get('timestamp', ''))
        ])
    
    headers = ["Type", "Value", "Reason", "Added"]
    print("\n=== BAN LIST ===")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"\nTotal bans: {len(bans)}")

def cmd_ban(ban_type, value, reason=""):
    """Add ban"""
    result = api_call("/admin/ban", "POST", {
        "type": ban_type,
        "value": value,
        "reason": reason
    })
    
    if result.get('result') == 'added':
        print(f"✓ Banned {ban_type}: {value}")
    elif result.get('result') == 'exists':
        print(f"⚠ Already banned: {value}")
    else:
        print(f"✗ Error: {result}")

def cmd_unban(ban_type, value):
    """Remove ban"""
    result = api_call("/admin/unban", "POST", {
        "type": ban_type,
        "value": value
    })
    
    if result.get('result') == 'removed':
        print(f"✓ Unbanned {ban_type}: {value}")
    else:
        print(f"✗ Error: {result}")

def cmd_keys():
    """List all keys"""
    result = api_call("/admin/list")
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    keys = result.get('keys', [])
    if not keys:
        print("No keys")
        return
    
    print("\n=== AUTHORIZED KEYS ===")
    for i, k in enumerate(keys, 1):
        print(f"{i}. {k}")
    print(f"\nTotal: {len(keys)} key(s)")

def cmd_add_key(key):
    """Add new key"""
    result = api_call("/admin/add", "POST", {"key": key})
    
    if result.get('result') == 'added':
        print(f"✓ Key added: {key}")
    elif result.get('result') == 'exists':
        print(f"⚠ Key already exists")
    else:
        print(f"✗ Error: {result}")

def cmd_remove_key(key):
    """Remove key"""
    result = api_call("/admin/remove", "POST", {"key": key})
    
    if result.get('result') == 'removed':
        print(f"✓ Key removed: {key}")
    else:
        print(f"✗ Error: {result}")

def print_help():
    """Print help"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║           LICENSE SERVER ADMIN DASHBOARD                       ║
╚════════════════════════════════════════════════════════════════╝

Commands:
  connections              - Show active connections
  failed-logins           - Show failed login attempts
  bans                    - List all bans
  ban <type> <value>      - Ban IP/ASN/key (type: ip, asn, key)
                            Example: ban ip 192.168.1.100
  unban <type> <value>    - Unban
  keys                    - List authorized keys
  add-key <key>           - Add new key
  remove-key <key>        - Remove key
  help                    - Show this help
  exit                    - Exit program

Examples:
  ban ip 192.168.1.100
  ban asn AS12345
  ban key TEST-KEY-123
  unban ip 192.168.1.100
  connections
  failed-logins
""")

def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║     NASH3D LICENSE SERVER ADMIN DASHBOARD (Terminal Mode)      ║
╚════════════════════════════════════════════════════════════════╝
    """)
    print("Type 'help' for commands\n")
    
    while True:
        try:
            cmd = input(">> ").strip()
            
            if not cmd:
                continue
            
            parts = cmd.split()
            command = parts[0].lower()
            
            if command == "connections":
                cmd_connections()
            elif command == "failed-logins":
                cmd_failed_logins()
            elif command == "bans":
                cmd_bans()
            elif command == "ban":
                if len(parts) < 3:
                    print("Usage: ban <type> <value> [reason]")
                    continue
                ban_type = parts[1].lower()
                value = parts[2]
                reason = " ".join(parts[3:]) if len(parts) > 3 else ""
                cmd_ban(ban_type, value, reason)
            elif command == "unban":
                if len(parts) < 3:
                    print("Usage: unban <type> <value>")
                    continue
                ban_type = parts[1].lower()
                value = parts[2]
                cmd_unban(ban_type, value)
            elif command == "keys":
                cmd_keys()
            elif command == "add-key":
                if len(parts) < 2:
                    print("Usage: add-key <key>")
                    continue
                key = parts[1]
                cmd_add_key(key)
            elif command == "remove-key":
                if len(parts) < 2:
                    print("Usage: remove-key <key>")
                    continue
                key = parts[1]
                cmd_remove_key(key)
            elif command == "help":
                print_help()
            elif command == "exit" or command == "quit":
                print("Goodbye!")
                break
            else:
                print(f"Unknown command: {command}. Type 'help' for help.")
        
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    main()
