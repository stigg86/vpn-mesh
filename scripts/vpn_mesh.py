import os, json, hashlib, time
from pathlib import Path

MESH_DIR = Path.home() / ".openclaw" / "vpn-mesh"
PRIVATE_KEY_FILE = MESH_DIR / "privatekey"
PUBLIC_KEY_FILE = MESH_DIR / "publickey"
CONFIG_FILE = MESH_DIR / "wg0.conf"
REGISTRY_FILE = MESH_DIR / "registry.json"
MESH_CONFIG = MESH_DIR / "config.json"
GIST_ID = "420f5fec0c401586b2d9b98cc5d969c5"

def get_github_token():
    """Get GitHub token from config file or environment"""
    if MESH_CONFIG.exists():
        try:
            cfg = json.loads(MESH_CONFIG.read_text())
            if cfg.get("github_token"):
                return cfg["github_token"]
        except: pass
    return os.environ.get("GITHUB_TOKEN", "")

GITHUB_TOKEN = get_github_token()
VPN_NETWORK = "10.0.0.0/16"
VPN_IP_BASE = "10.0"

COUNTRY_NAMES = {
    "ES": "Spain", "GB": "United Kingdom", "US": "United States", "DE": "Germany",
    "FR": "France", "NL": "Netherlands", "SE": "Sweden", "NO": "Norway",
    "FI": "Finland", "DK": "Denmark", "PL": "Poland", "IT": "Italy",
    "PT": "Portugal", "IE": "Ireland", "BE": "Belgium", "AT": "Austria",
    "CH": "Switzerland", "AU": "Australia", "CA": "Canada", "JP": "Japan",
}
FLAG_EMOJI = {"ES": "🇪🇸", "GB": "🇬🇧", "US": "🇺🇸", "DE": "🇩🇪", "FR": "🇫🇷",
              "NL": "🇳🇱", "SE": "🇸🇪", "NO": "🇳🇴", "FI": "🇫🇮", "DK": "🇩🇰",
              "PL": "🇵🇱", "IT": "🇮🇹", "PT": "🇵🇹", "IE": "🇮🇪", "BE": "🇧🇪",
              "AT": "🇦🇹", "CH": "🇨🇭", "AU": "🇦🇺", "CA": "🇨🇦", "JP": "🇯🇵"}

def ensure_mesh_dir(): MESH_DIR.mkdir(parents=True, exist_ok=True)

def generate_keypair():
    import subprocess
    try:
        result = subprocess.run(["wg", "genkey"], capture_output=True, timeout=5)
        privkey = result.stdout.decode().strip()
        result = subprocess.run(["wg", "pubkey"], input=privkey.encode(), capture_output=True, timeout=5)
        return privkey, result.stdout.decode().strip()
    except Exception as e:
        print(f"⚠️  WireGuard not available: {e}")
        return None, None

def announce_to_registry(node_info):
    import urllib.request
    token = GITHUB_TOKEN
    if not token:
        print("⚠️  No GitHub token - cannot announce to registry")
        print("   Create config with: mkdir -p ~/.openclaw/vpn-mesh && echo '{\"github_token\":\"ghp_YOUR_TOKEN\"}' > ~/.openclaw/vpn-mesh/config.json")
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
            current_nodes = json.loads(content) if content else []
        new_nodes = [node_info if n.get("public_key") == node_info.get("public_key") else n for n in current_nodes]
        if not any(n.get("public_key") == node_info.get("public_key") for n in current_nodes):
            new_nodes.append(node_info)
        data = json.dumps({"files": {"nodes.json": {"content": json.dumps(new_nodes, indent=2)}}}).encode()
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

def load_public_registry():
    import urllib.request
    token = GITHUB_TOKEN
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
    except: pass
    return nodes

def setup_node(announce=True):
    ensure_mesh_dir()
    privkey, pubkey = generate_keypair()
    if not privkey: return False
    PRIVATE_KEY_FILE.write_text(privkey)
    os.chmod(PRIVATE_KEY_FILE, 0o600)
    PUBLIC_KEY_FILE.write_text(pubkey)
    try:
        import urllib.request
        with urllib.request.urlopen("https://ipapi.co/json/", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            external_ip = data.get("ip", "unknown")
            country = data.get("country", "XX")
            city = data.get("city", "")
    except:
        external_ip = "unknown"; country = "XX"; city = ""
    node_id = os.environ.get("NODE_ID", f"node-{hashlib.md5(pubkey[:20].encode()).hexdigest()[:8]}")
    ip_hash = int(hashlib.md5(pubkey.encode()).hexdigest()[:8], 16)
    vpn_ip_num = (ip_hash % 65023) + 2
    vpn_ip = f"10.0.{vpn_ip_num // 256}.{vpn_ip_num % 256}/32"
    node_info = {"node_id": node_id, "public_key": pubkey, "endpoint": f"{external_ip}:51820", "vpn_ip": vpn_ip, "country": country, "city": city, "version": "0.8.0", "uptime": "100%", "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    full_info = node_info.copy(); full_info["private_key"] = privkey
    REGISTRY_FILE.write_text(json.dumps(full_info, indent=2))
    flag = FLAG_EMOJI.get(country, "🌍")
    print(f"""✅ VPN Mesh node '{node_id}' configured!
   {flag} Country: {COUNTRY_NAMES.get(country, country)}
   📍 City: {city or 'Unknown'}
   🌐 Endpoint: {external_ip}:51820
   🔑 Public Key: {pubkey[:40]}...
   💻 VPN IP: {vpn_ip.replace('/32', '')}""")
    if announce: announce_to_registry(node_info)
    print(f"\n🌐 Map: https://stigg86.github.io/vpn-mesh/")
    if not GITHUB_TOKEN:
        print("⚠️  Token required - create ~/.openclaw/vpn-mesh/config.json with {\"github_token\": \"ghp_...\"}")
    return True

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "setup": setup_node()
    elif cmd == "status":
        if REGISTRY_FILE.exists():
            d = json.loads(REGISTRY_FILE.read_text())
            print(f"Node: {d.get('node_id')} ({d.get('country')}/{d.get('city')})")
            print(f"Version: {d.get('version')}")
        else: print("Not configured")
    elif cmd == "list":
        nodes = load_public_registry()
        print(f"📡 Registry: {len(nodes)} total nodes")
        for n in nodes: print(f"   {FLAG_EMOJI.get(n.get('country','??'),'🌍')} {n.get('node_id')} - {n.get('country')}/{n.get('city')}")
    else: print("Commands: setup, status, list")
