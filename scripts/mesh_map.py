#!/usr/bin/env python3
"""
VPN Mesh - Interactive World Map
Generates a stunning HTML visualization of the mesh network
"""

import json
import sys
import time
import os
from pathlib import Path

MESH_DIR = Path.home() / ".openclaw" / "vpn-mesh"
REGISTRY_FILE = MESH_DIR / "registry.json"

# Public registry - can be overridden via VPN_MESH_REGISTRY env var
DEFAULT_REGISTRY = "https://gist.githubusercontent.com/stigg86/420f5fec0c401586b2d9b98cc5d969c5/raw/nodes.json"

# Country coordinates
COUNTRY_COORDS = {
    "ES": (39.5, -4.0), "GB": (54.0, -2.0), "US": (40.0, -100.0),
    "DE": (51.0, 10.0), "FR": (46.0, 2.0), "NL": (52.5, 5.5),
    "SE": (62.0, 15.0), "NO": (64.0, 10.0), "FI": (64.0, 26.0),
    "DK": (56.0, 10.0), "PL": (52.0, 20.0), "IT": (42.5, 12.5),
    "PT": (39.5, -8.0), "IE": (53.0, -8.0), "BE": (50.5, 4.5),
    "AT": (47.5, 14.5), "CH": (47.0, 8.0), "AU": (-25.0, 134.0),
    "CA": (60.0, -100.0), "JP": (36.0, 138.0), "KR": (37.5, 128.0),
    "SG": (1.35, 103.8), "IN": (20.0, 78.0), "BR": (-15.0, -55.0),
}

COUNTRY_NAMES = {
    "ES": "Spain", "GB": "United Kingdom", "US": "United States",
    "DE": "Germany", "FR": "France", "NL": "Netherlands",
    "SE": "Sweden", "NO": "Norway", "FI": "Finland", "DK": "Denmark",
    "PL": "Poland", "IT": "Italy", "PT": "Portugal", "IE": "Ireland",
    "BE": "Belgium", "AT": "Austria", "CH": "Switzerland",
    "AU": "Australia", "CA": "Canada", "JP": "Japan", "KR": "South Korea",
    "SG": "Singapore", "IN": "India", "BR": "Brazil",
}

FLAG_EMOJI = {
    "ES": "🇪🇸", "GB": "🇬🇧", "US": "🇺🇸", "DE": "🇩🇪", "FR": "🇫🇷",
    "NL": "🇳🇱", "SE": "🇸🇪", "NO": "🇳🇴", "FI": "🇫🇮", "DK": "🇩🇰",
    "PL": "🇵🇱", "IT": "🇮🇹", "PT": "🇵🇹", "IE": "🇮🇪", "BE": "🇧🇪",
    "AT": "🇦🇹", "CH": "🇨🇭", "AU": "🇦🇺", "CA": "🇨🇦", "JP": "🇯🇵",
    "KR": "🇰🇷", "SG": "🇸🇬", "IN": "🇮🇳", "BR": "🇧🇷",
}


def get_public_registry():
    """Get registry URL from env or default"""
    return os.environ.get("VPN_MESH_REGISTRY", DEFAULT_REGISTRY)


def load_nodes_from_gist_api(gist_id):
    """Fetch nodes using GitHub API to get current raw_url"""
    import urllib.request
    
    # Try to get raw_url from Gist API (more reliable than hardcoded URLs)
    token = os.environ.get("GITHUB_TOKEN", "")
    
    try:
        req = urllib.request.Request(f"https://api.github.com/gists/{gist_id}")
        if token:
            req.add_header("Authorization", f"token {token}")
        req.add_header("Accept", "application/vnd.github+json")
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            gist = json.loads(resp.read())
            raw_url = gist["files"]["nodes.json"]["raw_url"]
            
            # Fetch from raw_url
            req2 = urllib.request.Request(raw_url)
            with urllib.request.urlopen(req2) as resp2:
                return json.loads(resp2.read())
    except Exception as e:
        print(f"  ⚠️ Could not fetch from Gist API: {e}")
    
    return []


def load_nodes():
    """Load nodes from registry — merges local + public"""
    all_nodes = []
    seen_ids = set()
    
    # Load local registry first
    if REGISTRY_FILE.exists():
        try:
            data = json.loads(REGISTRY_FILE.read_text())
            if isinstance(data, list):
                for n in data:
                    if n.get("node_id"):
                        all_nodes.append(n)
                        seen_ids.add(n["node_id"])
            elif isinstance(data, dict) and data.get("node_id"):
                all_nodes.append(data)
                seen_ids.add(data["node_id"])
        except Exception as e:
            print(f"  ⚠️ Error reading local registry: {e}")
    
    # Try public registry - first via API for reliability
    registry = get_public_registry()
    
    # Extract Gist ID if this is a Gist URL
    import re
    gist_match = re.search(r'gist\.github(?:usercontent)?\.com/([^/]+)/([a-f0-9]+)', registry)
    
    if gist_match:
        # It's a Gist URL - use API for reliability
        gist_id = gist_match.group(2)
        public_nodes = load_nodes_from_gist_api(gist_id)
        for node in public_nodes:
            if node.get("node_id") not in seen_ids:
                all_nodes.append(node)
                seen_ids.add(node["node_id"])
    else:
        # Try direct URL fetch
        try:
            import urllib.request
            with urllib.request.urlopen(registry, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if isinstance(data, list):
                    for node in data:
                        if node.get("node_id") not in seen_ids:
                            all_nodes.append(node)
                            seen_ids.add(node["node_id"])
                elif isinstance(data, dict) and data.get("node_id") not in seen_ids:
                    all_nodes.append(data)
        except Exception as e:
            print(f"  ⚠️ Could not fetch public registry: {e}")
    
    return all_nodes


def get_coords(country):
    return COUNTRY_COORDS.get(country, (20, 0))


def generate_html(nodes):
    """Generate stunning HTML visualization"""
    nodes_json = json.dumps(nodes, ensure_ascii=False)
    coords_json = json.dumps({c: get_coords(c) for c in set(n.get("country", "XX") for n in nodes)})
    
    # Calculate stats
    total_nodes = len(nodes)
    countries = set(n.get("country", "XX") for n in nodes)
    total_countries = len(countries)
    avg_uptime = sum(float(n.get("uptime", "0").rstrip("%")) for n in nodes if n.get("uptime")) / max(total_nodes, 1)
    
    # Get current node
    current_pubkey = None
    if REGISTRY_FILE.exists():
        try:
            current = json.loads(REGISTRY_FILE.read_text())
            current_pubkey = current.get("public_key", "")
        except:
            pass
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌐 VPN Mesh Network</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root {{
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a25;
            --accent: #6366f1;
            --accent-glow: rgba(99, 102, 241, 0.3);
            --text-primary: #ffffff;
            --text-secondary: #a0a0b0;
            --border: rgba(255, 255, 255, 0.1);
            --success: #22c55e;
            --warning: #f59e0b;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }}
        
        .bg-pattern {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: 
                radial-gradient(circle at 20% 80%, var(--accent-glow) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 40%);
            pointer-events: none;
            z-index: 0;
        }}
        
        .container {{
            position: relative;
            z-index: 1;
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        
        header {{
            text-align: center;
            padding: 60px 0;
        }}
        
        h1 {{
            font-size: 3.5em;
            font-weight: 700;
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 16px;
            letter-spacing: -0.02em;
        }}
        
        .subtitle {{
            font-size: 1.25em;
            color: var(--text-secondary);
            font-weight: 400;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 24px;
            margin: 40px 0;
        }}
        
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 28px;
            text-align: center;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3), 0 0 60px var(--accent-glow);
        }}
        
        .stat-value {{
            font-size: 3em;
            font-weight: 700;
            background: linear-gradient(135deg, #6366f1, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            color: var(--text-secondary);
            margin-top: 8px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}
        
        .live-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: var(--bg-card);
            border-radius: 20px;
            font-size: 0.85em;
            margin-top: 20px;
        }}
        
        .live-dot {{
            width: 8px;
            height: 8px;
            background: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        .map-section {{
            margin: 40px 0;
        }}
        
        #map {{
            height: 500px;
            border-radius: 16px;
            z-index: 1;
        }}
        
        .nodes-section {{
            margin-top: 40px;
        }}
        
        .section-title {{
            font-size: 1.5em;
            font-weight: 600;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .nodes-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }}
        
        .node-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .node-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}
        
        .node-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
        }}
        
        .node-id {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.1em;
            font-weight: 600;
        }}
        
        .node-flag {{
            font-size: 2em;
        }}
        
        .node-info {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 16px;
        }}
        
        .info-item {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        
        .info-label {{
            font-size: 0.75em;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .info-value {{
            font-size: 0.95em;
            font-weight: 500;
        }}
        
        .node-status {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 500;
        }}
        
        .node-status.online {{
            background: rgba(34, 197, 94, 0.15);
            color: var(--success);
        }}
        
        .connect-btn {{
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 10px;
            font-size: 0.9em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            background: var(--accent);
            color: white;
        }}
        
        .connect-btn:hover {{
            transform: scale(1.02);
            box-shadow: 0 4px 20px var(--accent-glow);
        }}
        
        .footer {{
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }}
        
        .footer a {{
            color: var(--accent);
            text-decoration: none;
        }}
        
        /* Leaflet custom styles */
        .custom-marker {{
            background: transparent;
        }}
        
        .marker-pin {{
            width: 40px;
            height: 40px;
            border-radius: 50% 50% 50% 0;
            background: var(--accent);
            position: absolute;
            transform: rotate(-45deg);
            left: -20px;
            top: -40px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 20px rgba(99, 102, 241, 0.5);
        }}
        
        .marker-pin::after {{
            content: '';
            width: 20px;
            height: 20px;
            background: white;
            border-radius: 50%;
            transform: rotate(45deg);
        }}
        
        .leaflet-popup-content-wrapper {{
            background: var(--bg-card);
            color: var(--text-primary);
            border-radius: 12px;
        }}
        
        .leaflet-popup-tip {{
            background: var(--bg-card);
        }}
    </style>
</head>
<body>
    <div class="bg-pattern"></div>
    <div class="container">
        <header>
            <h1>🌐 VPN Mesh</h1>
            <p class="subtitle">Decentralized VPN exit nodes powered by OpenClaw agents</p>
            <div class="live-indicator">
                <span class="live-dot"></span>
                <span>Live Network • Updated just now</span>
            </div>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{total_nodes}</div>
                <div class="stat-label">Active Nodes</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_countries}</div>
                <div class="stat-label">Countries</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{avg_uptime:.0f}%</div>
                <div class="stat-label">Avg Uptime</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len([n for n in nodes if n.get('endpoint')])}</div>
                <div class="stat-label">Peers Online</div>
            </div>
        </div>
        
        <div class="map-section">
            <div id="map"></div>
        </div>
        
        <div class="nodes-section">
            <h2 class="section-title">🖧 Nodes ({total_nodes})</h2>
            <div class="nodes-grid">
"""

    for node in nodes:
        flag = FLAG_EMOJI.get(node.get("country", ""), "🌍")
        country_name = COUNTRY_NAMES.get(node.get("country", ""), node.get("country", "Unknown"))
        city = node.get("city", "Unknown")
        uptime = node.get("uptime", "0%")
        node_id = node.get("node_id", "unknown")
        pubkey = node.get("public_key", "")
        is_current = pubkey == current_pubkey
        
        btn_html = f"<button class='connect-btn' style='background: var(--bg-secondary); cursor: default;'>✓ This is your node</button>" if is_current else f"<button class='connect-btn' onclick='alert(\"Run: vpn_mesh connect {node_id}\")'>Connect</button>"
        
        html += f"""
            <div class="node-card">
                <div class="node-header">
                    <div>
                        <div class="node-id">{node_id}</span></div>
                        {"<span style='font-size: 0.8em; color: var(--text-secondary);'>Your node</span>" if is_current else ""}
                    </div>
                    <div class="node-flag">{flag}</div>
                </div>
                <div class="node-info">
                    <div class="info-item">
                        <span class="info-label">Country</span>
                        <span class="info-value">{country_name}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">City</span>
                        <span class="info-value">{city}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Uptime</span>
                        <span class="info-value">{uptime}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Version</span>
                        <span class="info-value">{node.get("version", "unknown")}</span>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="node-status online">✓ Online</span>
                </div>
                {btn_html}
            </div>
"""

    html += f"""
            </div>
        </div>
        
        <div class="footer">
            <p>Install your own node → <a href="https://clawhub.ai/stigg86/vpn-mesh">clawhub install vpn-mesh</a></p>
        </div>
    </div>
    
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const nodes = {nodes_json};
        const coords = {coords_json};
        
        const nodeIcon = L.divIcon({{
            className: 'custom-marker',
            html: '<div class="marker-pin"></div>',
            iconSize: [40, 40],
            iconAnchor: [20, 40],
            popupAnchor: [0, -40]
        }});
        
        const map = L.map('map').setView([30, 0], 2);
        
        L.tileLayer('https{{{{}}}}.{{{{}}}}'.replace('{{{{}}}}', '').replace('{{{{}}}}', ''), {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }}).addTo(map);
        
        // Fix tile layer
        L.tileLayer('https://{{}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: 19
        }}).addTo(map);
        
        const markers = [];
        nodes.forEach(node => {{
            const country = node.country || 'XX';
            const [lat, lng] = coords[country] || [20, 0];
            
            const popup = L.popup()
                .setContent(`
                    <div style="min-width: 200px;">
                        <h3 style="margin: 0 0 8px;">${{node.node_id}}</h3>
                        <p style="margin: 4px 0; color: #a0a0b0;">📍 ${{node.city || 'Unknown'}}, ${{node.country}}</p>
                        <p style="margin: 4px 0; color: #a0a0b0;">⏱️ Uptime: ${{node.uptime || 'N/A'}}</p>
                        ${{node.endpoint ? `<p style="margin: 4px 0; color: #a0a0b0;">🌐 ${{node.endpoint}}</p>` : ''}}
                    </div>
                `);
            
            const marker = L.marker([lat, lng], {{ icon: nodeIcon }})
                .bindPopup(popup)
                .addTo(map);
            
            markers.push(marker);
        }});
        
        // Fit bounds if we have nodes
        if (nodes.length > 0) {{
            const group = L.featureGroup(markers);
            map.fitBounds(group.getBounds().pad(0.2));
        }}
    </script>
</body>
</html>"""
    
    return html


def main():
    demo_mode = "--demo" in sys.argv
    html_mode = "--html" in sys.argv
    
    if not html_mode:
        print("🌐 VPN Mesh")
        print("="*20)
        print("\nUsage:")
        print("  mesh_map.py --html    Generate HTML map")
        print("  mesh_map.py --demo   Generate demo map with sample nodes")
        print("\nTo show real network nodes:")
        print("  mesh_map.py")
        return
    
    print("🔄 Loading nodes...")
    nodes = load_nodes()
    
    if demo_mode:
        demo_file = MESH_DIR / "demo_nodes.json"
        if demo_file.exists():
            try:
                demo_nodes = json.loads(demo_file.read_text())
                # Merge demo nodes with existing
                existing_ids = {n.get("node_id") for n in nodes}
                for dn in demo_nodes:
                    if dn.get("node_id") not in existing_ids:
                        nodes.append(dn)
            except:
                pass
    
    print(f"✅ Loaded {len(nodes)} nodes")
    
    html = generate_html(nodes)
    output_file = MESH_DIR / "mesh-map.html"
    output_file.write_text(html)
    
    print(f"📍 Location: {output_file}")
    print(f"🖧 Nodes shown: {len(nodes)}")
    countries = set(n.get("country", "?") for n in nodes)
    print(f"🌐 Countries: {len(countries)}")
    print(f"\nOpen in browser to see the interactive world map.")
    print(f"\nTo include demo nodes:")
    print(f"   python3 mesh_map.py --demo")
    print(f"\nTo show real network nodes:")
    print(f"   python3 mesh_map.py")


if __name__ == "__main__":
    main()