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
from pathlib import Path
from typing import Optional, List, Dict

MESH_DIR = Path.home() / ".openclaw" / "vpn-mesh"
CONFIG_DIR = MESH_DIR / "configs"
REGISTRY_FILE = MESH_DIR / "registry.json"
STATE_FILE = MESH_DIR / "state.json"
PRIVATE_KEY_FILE = MESH_DIR / "private.key"
PUBLIC_KEY_FILE = MESH_DIR / "public.key"
CONFIG_FILE = MESH_DIR / "wg0.conf"

# Default public registry (GitHub Gist - users replace with their own)
DEFAULT_REGISTRY = "https://gist.githubusercontent.com/stigg86/vpn-mesh-nodes/raw/nodes.json"

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
    return None


def get_private_key() -> Optional[str]:
    """Get this node's private key"""
    if PRIVATE_KEY_FILE.exists():
        return PRIVATE_KEY_FILE.read_text().strip()
    return None


def generate_keypair() -> tuple:
    """Generate WireGuard keypair"""
    try:
        # Use wg command to generate keys
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


def setup_node(announce: bool = False) -> bool:
    """Setup this node"""
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
            data = json.loads(resp.read().decode())
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
    
    # Create registry entry
    node_info = {
        "node_id": node_id,
        "public_key": pubkey,
        "private_key": privkey,  # Keep for peer config generation
        "endpoint": f"{external_ip}:{listen_port}",
        "vpn_ip": vpn_ip,
        "country": country,
        "city": city,
        "version": "0.3.0",
        "uptime": "100%",
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    
    REGISTRY_FILE.write_text(json.dumps(node_info, indent=2))
    
    # Create WireGuard config
    create_wireguard_config(node_info)
    
    print(f"""
✅ VPN Mesh node '{node_id}' configured!
   
   🇪🇸 Country: {COUNTRY_NAMES.get(country, country)}
   📍 City: {city or 'Unknown'}
   🌐 Endpoint: {external_ip}:{listen_port}
   🔑 Public Key: {pubkey[:40]}...
   💾 Config: {CONFIG_FILE}

To start VPN interface:
   sudo wg-quick up {CONFIG_FILE}

To connect to this node, other nodes need your public key.
Run 'vpn_mesh.py status' to see your node info.
""")
    
    # Optionally announce to registry
    if announce:
        print("📡 Node ready to announce to mesh network")
    
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
# Peer traffic will be masqueraded to the internet
"""
    
    CONFIG_FILE.write_text(config)
    os.chmod(CONFIG_FILE, 0o600)


def add_peer(peer_pubkey: str, peer_endpoint: str, peer_vpn_ip: str = "10.0.0.3/32") -> bool:
    """Add a peer to the WireGuard config"""
    if not CONFIG_FILE.exists():
        print("❌ No config found. Run 'vpn-mesh-setup' first.")
        return False
    
    privkey = get_private_key()
    if not privkey:
        print("❌ No private key found. Run 'vpn-mesh-setup' first.")
        return False
    
    # Read existing config
    config = CONFIG_FILE.read_text()
    
    # Add peer section
    peer_config = f"""

[Peer]
PublicKey = {peer_pubkey}
Endpoint = {peer_endpoint}
AllowedIPs = {peer_vpn_ip}
PersistentKeepalive = 25
"""
    
    config += peer_config
    CONFIG_FILE.write_text(config)
    
    return True


def connect_peer(node_id: str, peer_pubkey: str, peer_endpoint: str, peer_vpn_ip: str) -> bool:
    """Connect to a peer node"""
    state = get_state()
    
    # Disconnect existing first
    if state.get("active"):
        disconnect_peer()
    
    # Add peer
    if not add_peer(peer_pubkey, peer_endpoint, peer_vpn_ip):
        return False
    
    # Bring up interface
    try:
        result = subprocess.run(
            ["sudo", "wg-quick", "up", str(CONFIG_FILE)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to connect: {result.stderr}")
            return False
        
        save_state({
            "connected_to": node_id,
            "active": True,
            "peer_pubkey": peer_pubkey,
            "peer_endpoint": peer_endpoint,
            "peer_vpn_ip": peer_vpn_ip,
            "connected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        })
        
        print(f"✅ Connected to {node_id}")
        print(f"   Endpoint: {peer_endpoint}")
        print(f"   VPN IP: {peer_vpn_ip}")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def disconnect_peer() -> bool:
    """Disconnect from current peer"""
    state = get_state()
    
    if not state.get("active"):
        print("Not connected to any peer.")
        return True
    
    try:
        subprocess.run(
            ["sudo", "wg-quick", "down", str(CONFIG_FILE)],
            capture_output=True, text=True
        )
    except:
        pass
    
    # Remove peers from config but keep interface config
    if CONFIG_FILE.exists():
        privkey = get_private_key()
        if privkey:
            config = f"""[Interface]
PrivateKey = {privkey}
Address = 10.0.0.2/24
ListenPort = 51820
"""
            CONFIG_FILE.write_text(config)
    
    save_state({"connected_to": None, "active": False})
    print("🔌 Disconnected from mesh.")
    return True


def list_nodes() -> List[Dict]:
    """List all available nodes in the mesh"""
    # Try local registry
    if REGISTRY_FILE.exists():
        local = json.loads(REGISTRY_FILE.read_text())
        return [local]
    
    # Try public registry
    registry_url = os.environ.get("VPN_MESH_REGISTRY", DEFAULT_REGISTRY)
    try:
        import urllib.request
        with urllib.request.urlopen(registry_url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            nodes = data if isinstance(data, list) else data.get("nodes", [])
            # Filter out current node
            my_pubkey = get_public_key()
            return [n for n in nodes if n.get("public_key") != my_pubkey]
    except Exception as e:
        print(f"⚠️  Could not fetch registry: {e}")
    
    return []


def connect_country(country_code: str) -> bool:
    """Connect to best available node in a specific country"""
    all_nodes = list_nodes()
    
    # Find nodes in requested country
    matching = [n for n in all_nodes if n.get("country", "").upper() == country_code.upper()]
    
    if not matching:
        # Show available countries
        countries = set(n.get("country", "XX") for n in all_nodes)
        available = ", ".join([f"{FLAG_EMOJI.get(c, '🏳️')} {COUNTRY_NAMES.get(c, c)}" for c in sorted(countries)])
        print(f"❌ No nodes available in {COUNTRY_NAMES.get(country_code, country_code)}")
        print(f"   Available: {available or 'None yet'}")
        return False
    
    # Pick first available (could add latency check)
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
        print("❌ Node not configured. Run 'vpn-mesh-setup' first.")
        return None
    
    # Create compact code: COUNTRY-BASE64PUBKEY-ENDPOINT
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
    
    # The code format is shortened - we need full peer info
    # In a real system, the code would encode enough to find/connect
    # For demo, we'll use a simplified approach
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
Then share your public key with other node operators.
""")
        return {"configured": False}
    
    flag = FLAG_EMOJI.get(node_info.get("country", "XX"), "🏳️")
    print(f"""
✅ Node Configured
   ID: {node_info['node_id']}
   {flag} Country: {COUNTRY_NAMES.get(node_info.get('country', 'XX'), 'Unknown')}
   📍 City: {node_info.get('city', 'Unknown')}
   🌐 Endpoint: {node_info['endpoint']}
   🔑 Public Key: {node_info['public_key'][:40]}...
   📊 Uptime: {node_info.get('uptime', '100%')}
   🕐 Last updated: {node_info.get('updated', 'Unknown')[:16]}
""")
    
    if state.get("active"):
        print(f"""🔗 Connected to: {state['connected_to']}
   Peer: {state.get('peer_endpoint', 'Unknown')}
   Since: {state.get('connected_at', 'Unknown')[:16]}
""")
    else:
        print("🔌 Not connected to any peer")
    
    # Show available nodes
    nodes = list_nodes()
    if nodes:
        print(f"""
🖧 Available Nodes: {len(nodes)}
""")
        for n in nodes:
            flag = FLAG_EMOJI.get(n.get("country", "XX"), "🏳️")
            print(f"   {flag} {n['node_id']} ({n.get('endpoint', 'N/A')})")
    
    return {
        "configured": True,
        "node_id": node_info.get("node_id"),
        "country": node_info.get("country"),
        "connected": state.get("active"),
        "peer": state.get("connected_to"),
        "available_nodes": len(nodes)
    }


def main():
    if len(sys.argv) < 2:
        print("""
🌐 VPN Mesh - Secure VPN Network for OpenClaw Agents

Usage:
   vpn_mesh.py setup              Setup this node
   vpn_mesh.py status            Show node and connection status
   vpn_mesh.py list              List available mesh nodes
   vpn_mesh.py connect <node_id> Connect to a specific node
   vpn_mesh.py connect-country <CC>  Connect to a country (e.g., ES, GB, DE)
   vpn_mesh.py disconnect        Disconnect from mesh
   vpn_mesh.py pair              Generate pairing code to share
   vpn_mesh.py pair <code>       Connect using a pairing code
   vpn_mesh.py help              Show this help

Examples:
   vpn_mesh.py setup             # Create your node identity
   vpn_mesh.py list              # See who's in the mesh
   vpn_mesh.py connect spain     # Route through Spain
   vpn_mesh.py connect node-abc  # Connect to specific node
""")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "setup":
        setup_node(announce=True)
    
    elif cmd == "status":
        status()
    
    elif cmd == "list":
        nodes = list_nodes()
        if not nodes:
            print("🖧 No other nodes in mesh yet.")
            print("   Run 'vpn_mesh.py setup' to become the first node!")
        else:
            print(f"🖧 Mesh Nodes ({len(nodes)}):")
            print("-" * 50)
            for n in nodes:
                flag = FLAG_EMOJI.get(n.get("country", "XX"), "🏳️")
                print(f"   {flag} {n['node_id']}")
                print(f"      📍 {n.get('city', n.get('country', 'Unknown'))}")
                print(f"      🌐 {n.get('endpoint', 'N/A')}")
                print(f"      🔑 {n.get('public_key', '')[:30]}...")
                print()
    
    elif cmd == "connect":
        if len(sys.argv) < 3:
            print("Usage: vpn_mesh.py connect <node_id>")
            sys.exit(1)
        node_id = sys.argv[2]
        # For demo, we need full peer info - this would come from registry
        print(f"📡 Connecting to {node_id}...")
        print("   (In production, this fetches peer info from registry)")
    
    elif cmd == "connect-country":
        if len(sys.argv) < 3:
            print("Usage: vpn_mesh.py connect-country <CC>")
            print("   Example: vpn_mesh.py connect-country ES")
            sys.exit(1)
        country_code = sys.argv[2].upper()
        connect_country(country_code)
    
    elif cmd == "disconnect":
        disconnect_peer()
    
    elif cmd == "pair":
        if len(sys.argv) > 2:
            parse_pairing_code(sys.argv[2])
        else:
            generate_pairing_code()
    
    elif cmd in ["help", "--help", "-h"]:
        main()
    
    else:
        print(f"Unknown command: {cmd}")
        print("Run 'vpn_mesh.py' for help.")
        sys.exit(1)


if __name__ == "__main__":
    main()