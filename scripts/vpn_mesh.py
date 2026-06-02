#!/usr/bin/env python3
"""
VPN Mesh - Core API
Secure VPN mesh network for OpenClaw agents
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
    return {"connected_to": None, "active": False, "interface": None}


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
    if PRIVATE_KEY_FILE.exists():
        return PRIVATE_KEY_FILE.read_text().strip()
    return None


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
        print("   Run 'vpn-mesh-setup' first, or use Docker mode")
        return None, None


def announce_to_registry(node_info: Dict) -> bool:
    """Announce this node to the public registry (GitHub Gist)"""
    import urllib.request
    
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("⚠️  GITHUB_TOKEN not set. Skipping registry announce.")
        print("   Set export GITHUB_TOKEN='your-token' to enable auto-announce.")
        return False
    
    try:
        # Get current nodes from Gist
        req = urllib.request.Request(f"https://api.github.com/gists/{GIST_ID}")
        req.add_header("Authorization", f"token {token}")
        req.add_header("Accept", "application/vnd.github+json")
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            gist = json.loads(resp.read())
            raw_url = gist["files"]["nodes.json"]["raw_url"]
        
        # Fetch current nodes
        req2 = urllib.request.Request(raw_url)
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            content = resp2.read().decode()
            try:
                current_nodes = json.loads(content) if content else []
            except:
                current_nodes = []
        
        # Add/update this node
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
        
        # Update Gist
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


def setup_node(announce: bool = True) -> bool:
    """Setup this node - generates keys, creates config, optionally announces to registry"""
    ensure_mesh_dir()
    
    # Check if already configured
    if REGISTRY_FILE.exists():
        print("ℹ️  Node already configured. Use 'vpn_mesh.py reconnect' to reset.")
        if announce:
            node_info = get_node_info()
            if node_info:
                announce_to_registry(node_info)
        return True
    
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
    vpn_ip = "10.0.0.2/24"
    listen_port = 51820
    
    # Create registry entry (exclude private_key for sharing)
    node_info = {
        "node_id": node_id,
        "public_key": pubkey,
        "endpoint": f"{external_ip}:{listen_port}",
        "vpn_ip": vpn_ip,
        "country": country,
        "city": city,
        "version": "0.3.0",
        "uptime": "100%",
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    
    # Save registry (full version with private key for local use)
    full_info = node_info.copy()
    full_info["private_key"] = privkey
    REGISTRY_FILE.write_text(json.dumps(full_info, indent=2))
    
    # Create WireGuard config
    create_wireguard_config(node_info)
    
    flag = FLAG_EMOJI.get(country, "🌍")
    print(f"""
✅ VPN Mesh node '{node_id}' configured!
   
   {flag} Country: {COUNTRY_NAMES.get(country, country)}
   📍 City: {city or 'Unknown'}
   🌐 Endpoint: {external_ip}:{listen_port}
   🔑 Public Key: {pubkey[:40]}...
   💾 Config: {CONFIG_FILE}
""")
    
    # Announce to registry
    if announce:
        print("📡 Announcing to mesh registry...")
        announce_to_registry(node_info)
    
    print(f"""
🌐 Your node is now visible on the network map:
   https://stigg86.github.io/vpn-mesh/

To start VPN interface:
   sudo wg-quick up {CONFIG_FILE}
""")
    
    return True


def create_wireguard_config(node_info: Dict):
    """Create WireGuard interface config"""
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
    
    config = f"""[Interface]
PrivateKey = {node_info['private_key']}
Address = {node_info['vpn_ip']}
ListenPort = 51820

# NAT/masquerade for forwarding peer traffic
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o {default_iface} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o {default_iface} -j MASQUERADE

# Allow all peers to forward traffic through this node

[Peer]
# Pre-shared key for additional security (optional)
# PSK = 

[Peer]
# Demo peer for testing (remove in production)
PublicKey = demo-key-placeholder
Endpoint = demo.example.com:51820
"""
    
    CONFIG_FILE.write_text(config)
    print(f"   💾 WireGuard config written to {CONFIG_FILE}")


def add_peer(peer_pubkey: str, peer_endpoint: str, peer_vpn_ip: str = "10.0.0.3/32") -> bool:
    """Add a peer to the WireGuard config"""
    if not CONFIG_FILE.exists():
        print("❌ Config not found. Run setup first.")
        return False
    
    config = CONFIG_FILE.read_text()
    
    # Check if peer already exists
    if peer_pubkey in config:
        print(f"ℹ️  Peer already configured")
        return True
    
    # Add peer section
    peer_config = f"""

[Peer]
PublicKey = {peer_pubkey}
Endpoint = {peer_endpoint}
AllowedIPs = {peer_vpn_ip}
"""
    
    config += peer_config
    CONFIG_FILE.write_text(config)
    
    # Apply changes
    try:
        subprocess.run(["wg", "syncconf", "wg0", CONFIG_FILE], capture_output=True)
    except:
        pass
    
    return True


def connect_peer(node_id: str, peer_pubkey: str, peer_endpoint: str, peer_vpn_ip: str) -> bool:
    """Connect to a peer"""
    if not add_peer(peer_pubkey, peer_endpoint, peer_vpn_ip):
        return False
    
    state = get_state()
    state["connected_to"] = node_id
    state["active"] = True
    save_state(state)
    
    print(f"✅ Connected to {node_id}")
    return True


def disconnect_peer() -> bool:
    """Disconnect from current peer"""
    state = get_state()
    if not state.get("connected_to"):
        print("❌ Not connected to any peer")
        return False
    
    node_id = state["connected_to"]
    state["connected_to"] = None
    state["active"] = False
    save_state(state)
    
    print(f"🔌 Disconnected from {node_id}")
    return True


def load_public_registry() -> List[Dict]:
    """Load nodes from public registry using GitHub API for reliability"""
    import urllib.request
    
    token = os.environ.get("GITHUB_TOKEN", "")
    nodes = []
    
    try:
        # Use GitHub API to get current raw_url (more reliable than hardcoded URLs)
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


def list_nodes() -> List[Dict]:
    """List all available nodes in the mesh"""
    all_nodes = []
    seen_ids = set()
    
    # Load local registry first
    if REGISTRY_FILE.exists():
        try:
            local = json.loads(REGISTRY_FILE.read_text())
            if isinstance(local, list):
                for n in local:
                    if n.get("node_id"):
                        all_nodes.append(n)
                        seen_ids.add(n["node_id"])
            elif isinstance(local, dict) and local.get("node_id"):
                all_nodes.append(local)
                seen_ids.add(local["node_id"])
        except:
            pass
    
    # Also load from public registry
    public_nodes = load_public_registry()
    for node in public_nodes:
        if node.get("node_id") not in seen_ids:
            all_nodes.append(node)
            seen_ids.add(node["node_id"])
    
    # Filter out current node from list
    my_pubkey = get_public_key()
    other_nodes = [n for n in all_nodes if n.get("public_key") != my_pubkey]
    
    return other_nodes


def connect_country(country_code: str) -> bool:
    """Connect to best available node in a specific country"""
    all_nodes = list_nodes()
    
    # Find nodes in requested country
    matching = [n for n in all_nodes if n.get("country", "").upper() == country_code.upper()]
    
    if not matching:
        countries = set(n.get("country", "XX") for n in all_nodes)
        available = ", ".join([f"{FLAG_EMOJI.get(c, '🏳️')} {COUNTRY_NAMES.get(c, c)}" for c in sorted(countries)])
        print(f"❌ No nodes available in {COUNTRY_NAMES.get(country_code, country_code)}")
        print(f"   Available: {available or 'None yet'}")
        return False
    
    node = matching[0]
    return connect_peer(
        node["node_id"],
        node["public_key"],
        node["endpoint"],
        node.get("vpn_ip", "10.0.0.3/32")
    )


def generate_pairing_code() -> str:
    """Generate a short pairing code for easy peer exchange"""
    node_info = get_node_info()
    if not node_info:
        print("❌ Node not configured. Run 'vpn_mesh.py setup' first.")
        return None
    
    pubkey_short = base64.urlsafe_b64encode(node_info["public_key"][:16].encode()).decode().rstrip("=")
    code = f"{node_info['country']}-{pubkey_short}"
    
    print(f"""
🔗 Pairing Code: {code}

Share this code with another node owner.
They can run: vpn_mesh.py pair {code}
""")
    return code


def parse_pairing_code(code: str) -> Optional[Dict]:
    """Parse a pairing code to get peer info"""
    parts = code.split("-")
    if len(parts) < 2:
        print("❌ Invalid pairing code format.")
        return None
    
    country = parts[0]
    print(f"📍 Pairing code from: {COUNTRY_NAMES.get(country, country)}")
    print("⚠️  Full peer exchange needed - share your public key directly")
    return None


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
    
    print(f"""
✅ Node Configured
   ID: {node_info.get('node_id')}
   {flag} Country: {node_info.get('country', 'Unknown')}
   📍 City: {node_info.get('city', 'Unknown')}
   🌐 Endpoint: {node_info.get('endpoint')}
   🔑 Public Key: {node_info.get('public_key', '')[:30]}...
   📊 Uptime: {node_info.get('uptime', '100%')}
   🕐 Last updated: {node_info.get('updated', 'Unknown')}
""")
    
    if state.get("connected_to"):
        print(f"🔌 Connected to: {state['connected_to']}")
    else:
        print("🔌 Not connected to any peer")
    
    # Show available peers
    peers = list_nodes()
    print(f"\n🖧 Available Nodes: {len(peers)}")
    
    for peer in peers[:10]:
        pflag = FLAG_EMOJI.get(peer.get("country", ""), "🌍")
        print(f"   {pflag} {peer.get('node_id', 'unknown')} ({peer.get('endpoint', 'unknown')})")
    
    if len(peers) > 10:
        print(f"   ... and {len(peers) - 10} more")
    
    return node_info


def main():
    if len(sys.argv) < 2:
        print("""
🌐 VPN Mesh - Help
==================

Commands:
   setup          Setup/announce this node (runs automatically on first install)
   status         Show current status and available peers
   list           List all nodes in the mesh
   connect <id>   Connect to a specific node
   connect-country <CC>   Connect to a country (e.g., ES, GB, DE)
   disconnect     Disconnect from current peer
   pair           Generate pairing code
   announce       Re-announce this node to the registry
   
Examples:
   vpn_mesh.py setup
   vpn_mesh.py status
   vpn_mesh.py connect-country GB
""")
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == "setup":
        setup_node(announce=True)
    elif cmd == "status":
        status()
    elif cmd == "list":
        nodes = list_nodes()
        if not nodes:
            print("No other nodes available yet.")
        for n in nodes:
            flag = FLAG_EMOJI.get(n.get("country", ""), "🌍")
            print(f"{flag} {n.get('node_id')} - {n.get('endpoint')} ({n.get('city', 'Unknown')})")
    elif cmd == "connect":
        if len(sys.argv) < 3:
            print("Usage: vpn_mesh.py connect <node_id>")
            return
        node_id = sys.argv[2]
        nodes = list_nodes()
        match = next((n for n in nodes if n.get("node_id") == node_id), None)
        if not match:
            print(f"❌ Node '{node_id}' not found")
            return
        connect_peer(node_id, match["public_key"], match["endpoint"], match.get("vpn_ip", "10.0.0.3/32"))
    elif cmd == "connect-country":
        if len(sys.argv) < 3:
            print("Usage: vpn_mesh.py connect-country <CC>")
            return
        connect_country(sys.argv[2])
    elif cmd == "disconnect":
        disconnect_peer()
    elif cmd == "pair":
        generate_pairing_code()
    elif cmd == "announce":
        node_info = get_node_info()
        if node_info:
            announce_to_registry(node_info)
        else:
            print("❌ Node not configured. Run 'setup' first.")
    else:
        print(f"Unknown command: {cmd}")
        print("Run 'vpn_mesh.py' for help.")


if __name__ == "__main__":
    main()