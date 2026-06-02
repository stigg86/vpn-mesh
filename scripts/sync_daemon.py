#!/usr/bin/env python3
"""
VPN Mesh - Peer Sync Daemon
Periodically fetches registry and updates WireGuard peers
Run via cron: */5 * * * * python3 ~/.openclaw/skills/vpn-mesh/scripts/sync_daemon.py
"""

import json
import os
import sys
import time
from pathlib import Path

MESH_DIR = Path.home() / ".openclaw" / "vpn-mesh"
CONFIG_FILE = MESH_DIR / "wg0.conf"
STATE_FILE = MESH_DIR / "state.json"

# Import vpn_mesh functions
sys.path.insert(0, str(Path(__file__).parent))
import vpn_mesh

def sync_and_apply():
    """Sync peers and apply WireGuard config changes"""
    print(f"🔄 [{time.strftime('%Y-%m-%d %H:%M:%S')}] Syncing peers...")
    
    # Sync peers from registry
    count = vpn_mesh.sync_peers()
    
    if count == 0:
        print("   📭 No new peers to add")
        return
    
    # Check if WireGuard interface is up
    try:
        import subprocess
        result = subprocess.run(["wg", "show"], capture_output=True, text=True)
        if result.returncode == 0 and len(result.stdout) > 0:
            # Interface is up - sync config without restarting
            result = subprocess.run(
                ["sudo", "wg", "syncconf", "wg0", str(CONFIG_FILE)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"   ✅ Applied {count} new peers to live interface")
            else:
                print(f"   ⚠️  Could not sync live: {result.stderr[:100]}")
                print("      Run 'sudo wg-quick up wg0' to restart interface")
        else:
            print(f"   ✅ {count} peers added to config")
            print("      Interface not running - start with: sudo wg-quick up wg0")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")

if __name__ == "__main__":
    sync_and_apply()