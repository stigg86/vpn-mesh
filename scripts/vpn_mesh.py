#!/usr/bin/env python3
"""
VPN Mesh - Core API
Full mesh VPN network for OpenClaw agents
Every node connects to every other node = true mesh
"""

import json
import os
import base64
import hashlib
import struct
import subprocess
import sys
import time
import re
from pathlib import Path
from typing import Optional, List, Dict

MESH_DIR = Path.home() / ".openclaw" / "vpn-mesh"
CONFIG_DIR = MESH_DIR / "configs"
REGISTRY_FILE = MESH_DIR / "registry.json"
STATE_FILE = MESH_DIR / "state.json"
PRIVATE_KEY_FILE = MESH_DIR / "private.key"
PUBLIC_KEY_FILE = MESH_DIR / "public.key"
CONFIG_FILE = MESH_DIR / "wg0.conf"

# Default public registry (GitHub Gist)
DEFAULT_REGISTRY = "https://gist.githubusercontent.com/stigg86/420f5fec0c401586b2d9b98cc5d969c5/raw/nodes.json"
GIST_ID = "420f5fec0c401586b2d9b98cc5d969c5"

# VPN IP range for mesh - each node gets unique IP
# Use /16 for 65k nodes (10.0.0.0/16 = 10.0.0.1 through 10.0.255.254)
VPN_NETWORK = "10.0.0.0/16"
VPN_IP_BASE = "10.0"

COUNTRY_NAMES = {
    "ES": "Spain", "GB": "United Kingdom", "US": "United States", "DE": "Germany",
    "FR": "France", "NL": "Netherlands", "SE": "Sweden", "NO": "Norway",
    "FI": "Finland", "DK": "Denmark", "PL": "Poland", "IT": "Italy",
    "PT": "Portugal", "IE": "Ireland", "BE": "Belgium", "AT": "Austria",
    "CH": "Switzerland", "AU": "Australia", "CA": "Canada", "JP": "Japan",
    "KR": "South Korea", "SG": "Singapore", "IN": "India", "BR": "Brazil",
}

FLAG_EMOJI = {
    "ES": "🇪🇸", "GB": "🇬🇧", "US": "🇺🇸", "DE": "🇩🇪", "FR": "🇫🇷",
    "NL": "🇳🇱", "SE": "🇸🇪", "NO": "🇳🇴", "FI": "🇫🇮", "DK": "🇩🇰",
    "PL": "🇵🇱", "IT": "🇮🇹", "PT": "🇵🇹", "IE": "🇮🇪", "BE": "🇧🇪",
    "AT": "🇦🇹", "CH": "🇨🇭", "AU": "🇦🇺", "CA": "🇨🇦", "JP": "🇯🇵",
    "KR": "🇰🇷", "SG": "🇸🇬", "IN": "🇮🇳", "BR": "🇧🇷",
}


def ensure_mesh_dir():
    """Ensure mesh directory exists"""
    MESH_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_state() -> Dict:
    """Get current connection state"""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"connected_to": None, "active": False, "interface": None, "peers": []}


def save_state(state: Dict):
    """Save connection state"""
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_node_info() -> Optional[Dict]:
    """Get this node's info"""
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    return None


def get_public_key() -> Optional[str]:
    """Get this node's public key"""
    if PUBLIC_KEY_FILE.exists():
        return PUBLIC_KEY_FILE.read_text().strip()
    # Fallback to registry if file doesn't exist
    if REGISTRY_FILE.exists():
        try:
            data = json.loads(REGISTRY_FILE.read_text())
            return data.get("public_key", "")
        except:
            pass
    return None


def get_private_key() -> Optional[str]:
    """Get this node's private key"""
    # Check private.key file first, but only return if it has content
    if PRIVATE_KEY_FILE.exists():
        content = PRIVATE_KEY_FILE.read_text().strip()
        if content:
            return content
    # Fallback to registry if file doesn't exist or is empty
    if REGISTRY_FILE.exists():
        try:
            data = json.loads(REGISTRY_FILE.read_text())
            return data.get("private_key", "")
        except:
            pass
    return None


def get_vpn_ip(node_index: int) -> str:
    """Generate deterministic VPN IP for a node based on index"""
    # Node 0 = 10.0.0.1, Node 1 = 10.0.0.2, etc.
    return f"{VPN_IP_BASE}.0.{node_index + 1}/32"


def generate_keypair() -> tuple:
    """Generate WireGuard keypair"""
    try:
        privkey = subprocess.check_output(
            ["wg", "genkey"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        pubkey = subprocess.check_output(
            ["wg", "pubkey"],
            input=privkey.encode(),
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return privkey, pubkey
    except Exception as e:
        print(f"⚠️  WireGuard not available: {e}")
        print("   Run 'sudo apt install wireguard' to install")
        return None, None


def announce_to_registry(node_info: Dict) -> bool:
    """Announce this node to the public registry (GitHub Gist)"""
    import urllib.request
    
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("⚠️  GITHUB_TOKEN not set. Set 'export GITHUB_TOKEN=...' to enable announce.")
        return False
    
    try:
        req = urllib.request.Request(f"https://api.github.com/gists/{GIST_ID}")
        req.add_header("Authorization", f"token {token}")
        req.add_header("Accept", "application/vnd.github+json")
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            gist = json.loads(resp.read().decode("utf-8"))
            raw_url = gist["files"]["nodes.json"]["raw_url"]
        
        req2 = urllib.request.Request(raw_url)
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            content = resp2.read().decode("utf-8")
            try:
                current_nodes = json.loads(content) if content else []
            except:
                current_nodes = []
        
        my_pubkey = node_info.get("public_key", "")
        updated = False
        new_nodes = []
        for n in current_nodes:
            if n.get("public_key") == my_pubkey:
                new_nodes.append(node_info)
                updated = True
            else:
                new_nodes.append(n)
        
        if not updated:
            new_nodes.append(node_info)
        
        data = json.dumps({
            "files": {
                "nodes.json": {
                    "content": json.dumps(new_nodes, indent=2)
                }
            }
        }).encode()
        
        req3 = urllib.request.Request(f"https://api.github.com/gists/{GIST_ID}", data=data, method="PATCH")
        req3.add_header("Authorization", f"token {token}")
        req3.add_header("Content-Type", "application/json")
        
        with urllib.request.urlopen(req3, timeout=10) as resp3:
            result = json.loads(resp3.read())
            print(f"   ✅ Announced to registry ({len(new_nodes)} total nodes)")
            return True
            
    except Exception as e:
        print(f"⚠️  Failed to announce: {e}")
        return False


def load_public_registry() -> List[Dict]:
    """Load nodes from public registry using GitHub API for reliability"""
    import urllib.request
    
    token = os.environ.get("GITHUB_TOKEN", "")
    nodes = []
    
    try:
        req = urllib.request.Request(f"https://api.github.com/gists/{GIST_ID}")
        if token:
            req.add_header("Authorization", f"token {token}")
        req.add_header("Accept", "application/vnd.github+json")
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            gist = json.loads(resp.read().decode("utf-8"))
            raw_url = gist["files"]["nodes.json"]["raw_url"]
            
            req2 = urllib.request.Request(raw_url)
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                content = resp2.read().decode("utf-8")
                nodes = json.loads(content) if content else []
    except Exception as e:
        print(f"⚠️  Could not fetch public registry: {e}")
    
    return nodes if isinstance(nodes, list) else []


def sync_peers() -> int:
    """Fetch all nodes from registry and add as WireGuard peers.
    Returns number of peers added."""
    my_pubkey = get_public_key()
    my_privkey = get_private_key()
    
    if not my_pubkey or not my_privkey:
        print("❌ Node not configured. Run 'vpn_mesh.py setup' first.")
        return 0
    
    node_info = get_node_info()
    if not node_info:
        print("❌ Node info not found.")
        return 0
    
    # Get all nodes from registry
    all_nodes = load_public_registry()
    
    # Filter out self
    other_nodes = [n for n in all_nodes if n.get("public_key") != my_pubkey]
    
    if not other_nodes:
        print("📭 No other nodes in registry yet. Be the first!")
        return 0
    
    print(f"🔗 Adding {len(other_nodes)} peers to mesh...")
    
    # Assign VPN IPs to peers (start from .2 since .1 is often used for gateway)
    # In a full mesh, every node needs to know every other node's VPN IP
    # For simplicity, use endpoint-based assignment or store VPN IP in registry
    
    # Build WireGuard config with all peers
    default_iface = "eth0"
    try:
        result = subprocess.run(
            ["ip", "-4", "route", "show", "default"],
            capture_output=True, text=True
        )
        if result.stdout:
            default_iface = result.stdout.split()[4]
    except:
        pass
    
    # Use node's stored VPN IP or assign based on index
    my_vpn_ip = node_info.get("vpn_ip", "10.0.0.2/32")
    
    config = f"""[Interface]
PrivateKey = {my_privkey}
Address = {my_vpn_ip}
ListenPort = 51820

# NAT/masquerade for forwarding peer traffic
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o {default_iface} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o {default_iface} -j MASQUERADE

"""
    
    for i, peer in enumerate(other_nodes):
        peer_pubkey = peer.get("public_key", "")
        peer_endpoint = peer.get("endpoint", "")
        peer_vpn_ip = peer.get("vpn_ip", f"10.0.0.{i+3}/32")  # fallback
        
        if not peer_pubkey or not peer_endpoint:
            continue
        
        # AllowedIPs: /32 means only route that single IP through the peer
        # For full mesh, we want all nodes to be reachable
        # Use the peer's VPN IP range
        config += f"""[Peer]
# {peer.get('node_id', 'peer')} - {FLAG_EMOJI.get(peer.get('country', ''), '🌍')} {peer.get('city', '')}
PublicKey = {peer_pubkey}
Endpoint = {peer_endpoint}
AllowedIPs = {peer_vpn_ip}
PersistentKeepalive = 25

"""
    
    CONFIG_FILE.write_text(config)
    print(f"   ✅ Config written with {len(other_nodes)} peers: {CONFIG_FILE}")
    
    # Update state
    state = get_state()
    state["active"] = True
    state["peers"] = [n.get("node_id") for n in other_nodes]
    save_state(state)
    
    return len(other_nodes)


def connect_mesh():
    """Start the mesh VPN interface"""
    if not CONFIG_FILE.exists():
        print("❌ Config not found. Run 'vpn_mesh.py setup' first.")
        return False
    
    # Ensure WireGuard is available
    if not os.path.exists("/usr/bin/wg"):
        print("❌ WireGuard not installed. Run: sudo apt install wireguard")
        return False
    
    try:
        # Bring up WireGuard interface
        result = subprocess.run(
            ["sudo", "wg-quick", "up", str(CONFIG_FILE)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to bring up mesh: {result.stderr}")
            return False
        
        print("✅ Mesh VPN interface UP")
        
        state = get_state()
        state["active"] = True
        save_state(state)
        
        return True
    except Exception as e:
        print(f"❌ Error starting mesh: {e}")
        return False


def disconnect_mesh():
    """Stop the mesh VPN interface"""
    if not CONFIG_FILE.exists():
        return False
    
    try:
        result = subprocess.run(
            ["sudo", "wg-quick", "down", str(CONFIG_FILE)],
            capture_output=True,
            text=True
        )
        
        state = get_state()
        state["active"] = False
        save_state(state)
        
        print("🔌 Mesh VPN interface DOWN")
        return True
    except Exception as e:
        print(f"❌ Error stopping mesh: {e}")
        return False


def list_mesh_nodes() -> List[Dict]:
    """List all nodes in the mesh registry with their VPN IPs"""
    my_pubkey = get_public_key()
    all_nodes = load_public_registry()
    
    nodes = []
    for n in all_nodes:
        is_me = n.get("public_key") == my_pubkey
        nodes.append({
            "node_id": n.get("node_id", "unknown"),
            "public_key": n.get("public_key", ""),
            "endpoint": n.get("endpoint", ""),
            "vpn_ip": n.get("vpn_ip", ""),
            "country": n.get("country", ""),
            "city": n.get("city", ""),
            "is_me": is_me
        })
    
    return nodes


def route_all_through(node_id: str) -> bool:
    """Route ALL traffic through a specific mesh node (VPN exit)
    
    Use this when you want an agent to tunnel through a specific country.
    The target node becomes your internet exit point.
    
    Args:
        node_id: The node_id from the mesh registry
        
    Returns:
        True if routing was configured successfully
    """
    nodes = list_mesh_nodes()
    target = None
    for n in nodes:
        if n["node_id"] == node_id:
            target = n
            break
    
    if not target:
        print(f"❌ Node '{node_id}' not found in mesh registry")
        return False
    
    if target.get("is_me"):
        print("❌ Cannot route through yourself")
        return False
    
    peer_vpn_ip = target.get("vpn_ip", "").replace("/32", "")
    if not peer_vpn_ip:
        print(f"❌ Node has no VPN IP assigned")
        return False
    
    print(f"🌐 Routing ALL traffic through {node_id} ({target.get('city')}, {target.get('country')})...")
    
    # Enable IP forwarding
    try:
        subprocess.run(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"], check=True, capture_output=True)
        subprocess.run(["sudo", "sysctl", "-w", "net.ipv6.conf.all.forwarding=1"], check=True, capture_output=True)
    except Exception as e:
        print(f"⚠️  Could not enable IP forwarding: {e}")
    
    # Add route: all traffic (0.0.0.0/0) goes through the peer
    # We use the peer's VPN IP as the gateway
    try:
        # Delete any existing default route via WireGuard
        subprocess.run(["sudo", "ip", "route", "del", "default", "dev", "wg0"], capture_output=True)
    except:
        pass
    
    try:
        # Add route: everything goes through wg0 to the peer
        # The peer will forward to internet (via its NAT/masquerade)
        result = subprocess.run(
            ["sudo", "ip", "route", "add", "default", "via", peer_vpn_ip, "dev", "wg0"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"⚠️  Route failed: {result.stderr}")
            # Try alternative approach: use peer as gateway directly
            result = subprocess.run(
                ["sudo", "ip", "route", "add", "default", "dev", "wg0"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"❌ Could not set default route: {result.stderr}")
                return False
    except Exception as e:
        print(f"❌ Error configuring routing: {e}")
        return False
    
    # Save routing state
    state = get_state()
    state["routing_through"] = node_id
    state["exit_peer"] = peer_vpn_ip
    save_state(state)
    
    flag = FLAG_EMOJI.get(target.get("country", ""), "🌍")
    print(f"""
✅ Routing configured!
   Exit node: {flag} {node_id} ({target.get('city')})
   Peer VPN IP: {peer_vpn_ip}
   
   All your traffic now exits via this node.
   To verify: curl --interface wg0 ifconfig.me
   To stop: vpn_mesh.py stop-routing
""")
    return True


def stop_routing():
    """Stop routing traffic through mesh and return to normal internet"""
    try:
        # Remove default route via wg0
        subprocess.run(["sudo", "ip", "route", "del", "default", "dev", "wg0"], capture_output=True)
    except:
        pass
    
    state = get_state()
    state.pop("routing_through", None)
    state.pop("exit_peer", None)
    save_state(state)
    
    print("✅ Routing stopped. Traffic now goes directly via your ISP.")


def setup_node(announce: bool = True) -> bool:
    """Setup this node - generates keys, creates config, announces to registry, syncs peers"""
    ensure_mesh_dir()
    
    privkey, pubkey = generate_keypair()
    if not privkey:
        return False
    
    # Save keys
    PRIVATE_KEY_FILE.write_text(privkey)
    PUBLIC_KEY_FILE.write_text(pubkey)
    os.chmod(PRIVATE_KEY_FILE, 0o600)
    
    # Get external IP and country
    try:
        import urllib.request
        with urllib.request.urlopen("https://ipapi.co/json/", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            external_ip = data.get("ip", "unknown")
            country = data.get("country", "XX")
            city = data.get("city", "")
    except:
        external_ip = "unknown"
        country = "XX"
        city = ""
    
    node_id = os.environ.get("NODE_ID", f"node-{hashlib.md5(pubkey[:20].encode()).hexdigest()[:8]}")
    listen_port = 51820
    
    # Determine VPN IP - based on hash of pubkey for consistency
    # This ensures same node always gets same IP across re-installs
    ip_hash = int(hashlib.md5(pubkey.encode()).hexdigest()[:8], 16)
    vpn_ip_num = (ip_hash % 65023) + 2  # Between .2 and .65534
    vpn_ip = f"10.0.{vpn_ip_num // 256}.{vpn_ip_num % 256}/32"
    
    # Create registry entry (exclude private_key for sharing)
    node_info = {
        "node_id": node_id,
        "public_key": pubkey,
        "endpoint": f"{external_ip}:{listen_port}",
        "vpn_ip": vpn_ip,
        "country": country,
        "city": city,
        "version": "0.4.0",
        "uptime": "100%",
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    
    # Save registry (full version with private key for local use)
    full_info = node_info.copy()
    full_info["private_key"] = privkey
    REGISTRY_FILE.write_text(json.dumps(full_info, indent=2))
    
    flag = FLAG_EMOJI.get(country, "🌍")
    print(f"""
✅ VPN Mesh node '{node_id}' configured!
   
   {flag} Country: {COUNTRY_NAMES.get(country, country)}
   📍 City: {city or 'Unknown'}
   🌐 Endpoint: {external_ip}:{listen_port}
   🔑 Public Key: {pubkey[:40]}...
   💻 VPN IP: {vpn_ip.replace('/32', '')}
   💾 Config: {CONFIG_FILE}
""")
    
    # Announce to registry
    if announce:
        print("📡 Announcing to mesh registry...")
        announce_to_registry(node_info)
    
    # Sync peers from registry
    print("🔗 Syncing peers from registry...")
    peer_count = sync_peers()
    
    print(f"""
🌐 Your node is now visible on the network map:
   https://stigg86.github.io/vpn-mesh/

{'🔗 Connected to ' + str(peer_count) + ' peers!' if peer_count > 0 else ''}
   
To start VPN mesh:
   sudo wg-quick up {CONFIG_FILE}

To see peer status:
   sudo wg show
""")
    
    return True


def status() -> Dict:
    """Show current mesh status"""
    node_info = get_node_info()
    state = get_state()
    
    print("""
🌐 VPN Mesh Status
==================""")
    
    if not node_info:
        print("""
❌ Node not configured

Run 'vpn_mesh.py setup' to create your node identity.
""")
        return {}
    
    flag = FLAG_EMOJI.get(node_info.get("country", ""), "🌍")
    
    # Check if WireGuard interface is active
    wg_active = False
    try:
        result = subprocess.run(["wg", "show"], capture_output=True, text=True)
        wg_active = result.returncode == 0 and len(result.stdout) > 0
    except:
        pass
    
    print(f"""
✅ Node Configured
   ID: {node_info.get('node_id')}
   {flag} Country: {node_info.get('country', 'Unknown')}
   📍 City: {node_info.get('city', 'Unknown')}
   🌐 Endpoint: {node_info.get('endpoint')}
   💻 VPN IP: {node_info.get('vpn_ip', 'unknown').replace('/32', '')}
   🔑 Public Key: {node_info.get('public_key', '')[:30]}...
   📊 Uptime: {node_info.get('uptime', '100%')}
   🕐 Last updated: {node_info.get('updated', 'Unknown')}

🔌 Mesh Status: {'ACTIVE' if wg_active else 'DOWN'}
   Peers: {len(state.get('peers', []))} configured
""")
    
    if wg_active:
        print("   ✅ WireGuard interface is UP")
        # Show connected peers
        try:
            result = subprocess.run(["wg", "show"], capture_output=True, text=True)
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if "peer:" in line.lower():
                    peer_key = line.split("peer:")[1].strip()
                    print(f"   🔗 Peer: {peer_key[:30]}...")
        except:
            pass
    else:
        print("   ⚠️  WireGuard interface is DOWN")
        print("   Run 'sudo wg-quick up ~/.openclaw/vpn-mesh/wg0.conf' to start")
    
    # Show all nodes in registry
    all_nodes = load_public_registry()
    my_pubkey = get_public_key()
    other_nodes = [n for n in all_nodes if n.get("public_key") != my_pubkey]
    
    print(f"\n📡 Registry: {len(all_nodes)} total nodes ({len(other_nodes)} other)")
    for n in other_nodes[:5]:
        pflag = FLAG_EMOJI.get(n.get("country", ""), "🌍")
        print(f"   {pflag} {n.get('node_id')} - {n.get('endpoint')} ({n.get('city', 'Unknown')})")
    if len(other_nodes) > 5:
        print(f"   ... and {len(other_nodes) - 5} more")
    
    return node_info


def main():
    if len(sys.argv) < 2:
        print("""
🌐 VPN Mesh - Full Mesh VPN
============================

Commands:
   setup          Setup this node (generates keys, announces, syncs peers)
   start          Start the mesh VPN interface
   stop           Stop the mesh VPN interface  
   sync           Re-sync peers from registry
   status         Show current status
   list           List all nodes in registry
   route <id>     Route ALL traffic through a mesh node (VPN exit)
   stop-routing   Stop routing through mesh, return to normal internet
   
Quick Start:
   vpn_mesh.py setup        # One-time setup
   sudo wg-quick up wg0     # Start mesh (or 'vpn_mesh.py start')
   sudo wg show             # Check peers

Examples:
   vpn_mesh.py setup
   vpn_mesh.py sync
   sudo wg-quick up ~/.openclaw/vpn-mesh/wg0.conf
""")
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == "setup":
        setup_node(announce=True)
    elif cmd == "start":
        connect_mesh()
    elif cmd == "stop":
        disconnect_mesh()
    elif cmd == "sync":
        count = sync_peers()
        print(f"✅ Synced {count} peers")
        if count > 0:
            print("   Run 'sudo wg-quick up ~/.openclaw/vpn-mesh/wg0.conf' to apply changes")
    elif cmd == "status":
        status()
    elif cmd == "list":
        nodes = load_public_registry()
        my_pubkey = get_public_key()
        print(f"📡 Registry: {len(nodes)} total nodes")
        for n in nodes:
            flag = FLAG_EMOJI.get(n.get("country", ""), "🌍")
            is_me = " (YOU)" if n.get("public_key") == my_pubkey else ""
            print(f"   {flag} {n.get('node_id')}{is_me} - {n.get('endpoint')} ({n.get('city', 'Unknown')})")
    elif cmd == "route":
        if len(sys.argv) < 3:
            print("Usage: vpn_mesh.py route <node_id>")
            print("   Run 'vpn_mesh.py list' to see available nodes")
        else:
            route_all_through(sys.argv[2])
    elif cmd == "stop-routing":
        stop_routing()
    else:
        print(f"Unknown command: {cmd}")
        print("Run 'vpn_mesh.py' for help.")


if __name__ == "__main__":
    main()