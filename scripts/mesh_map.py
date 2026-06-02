#!/usr/bin/env python3
"""
VPN Mesh - Interactive World Map
Generates a stunning HTML visualization of the mesh network
"""

import json
import sys
import time
from pathlib import Path

MESH_DIR = Path.home() / ".openclaw" / "vpn-mesh"
REGISTRY_FILE = MESH_DIR / "registry.json"
PUBLIC_REGISTRY = "https://gist.githubusercontent.com/stigg86/420f5fec0c401586b2d9b98cc5d969c5/raw/nodes.json"

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


def load_nodes():
    """Load nodes from registry"""
    if REGISTRY_FILE.exists():
        try:
            data = json.loads(REGISTRY_FILE.read_text())
            if isinstance(data, list):
                return data
            return [data]
        except:
            pass
    
    # Try public registry
    try:
        import urllib.request
        with urllib.request.urlopen(PUBLIC_REGISTRY, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data if isinstance(data, list) else data.get("nodes", [])
    except:
        pass
    
    return []


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
        
        /* Animated background */
        .bg-pattern {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
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
        
        /* Header */
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
        
        /* Stats Grid */
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
            color: var(--accent);
            line-height: 1;
            margin-bottom: 8px;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}
        
        /* Map Container */
        .map-container {{
            position: relative;
            border-radius: 24px;
            overflow: hidden;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            margin: 40px 0;
            box-shadow: 0 0 80px rgba(99, 102, 241, 0.1);
        }}
        
        #map {{
            width: 100%;
            height: 500px;
            background: var(--bg-secondary);
        }}
        
        .map-overlay {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 20px;
            z-index: 1000;
        }}
        
        .map-overlay h3 {{
            font-size: 0.85em;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 8px;
        }}
        
        .live-indicator {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .pulse {{
            width: 10px;
            height: 10px;
            background: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.5; transform: scale(1.2); }}
        }}
        
        /* Nodes Grid */
        .nodes-section {{
            margin: 60px 0;
        }}
        
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }}
        
        .section-header h2 {{
            font-size: 1.5em;
            font-weight: 600;
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
            transition: all 0.3s;
        }}
        
        .node-card:hover {{
            border-color: var(--accent);
            box-shadow: 0 0 30px var(--accent-glow);
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
            color: var(--text-primary);
        }}
        
        .node-flag {{
            font-size: 2em;
        }}
        
        .node-info {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
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
            color: var(--text-primary);
        }}
        
        .node-status {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            margin-top: 16px;
        }}
        
        .node-status.online {{
            background: rgba(34, 197, 94, 0.15);
            color: var(--success);
        }}
        
        .node-status.offline {{
            background: rgba(239, 68, 68, 0.15);
            color: #ef4444;
        }}
        
        /* Connect Button */
        .connect-btn {{
            background: linear-gradient(135deg, var(--accent) 0%, #8b5cf6 100%);
            border: none;
            color: white;
            padding: 12px 24px;
            border-radius: 10px;
            font-size: 0.9em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            width: 100%;
            margin-top: 16px;
        }}
        
        .connect-btn:hover {{
            transform: scale(1.02);
            box-shadow: 0 10px 30px var(--accent-glow);
        }}
        
        /* Empty State */
        .empty-state {{
            text-align: center;
            padding: 80px 40px;
            background: var(--bg-card);
            border-radius: 24px;
            border: 1px dashed var(--border);
        }}
        
        .empty-state h2 {{
            font-size: 1.5em;
            margin-bottom: 16px;
            color: var(--text-secondary);
        }}
        
        .empty-state p {{
            color: var(--text-secondary);
            max-width: 400px;
            margin: 0 auto;
        }}
        
        /* Footer */
        footer {{
            text-align: center;
            padding: 60px 0 30px;
            color: var(--text-secondary);
            font-size: 0.85em;
        }}
        
        footer a {{
            color: var(--accent);
            text-decoration: none;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            h1 {{ font-size: 2.5em; }}
            .stats-grid {{ grid-template-columns: 1fr 1fr; }}
            #map {{ height: 350px; }}
        }}
        
        /* Custom Leaflet Styles */
        .leaflet-container {{
            background: var(--bg-secondary);
            font-family: 'Inter', sans-serif;
        }}
        
        .leaflet-popup-content-wrapper {{
            background: var(--bg-card);
            color: var(--text-primary);
            border-radius: 12px;
            border: 1px solid var(--border);
        }}
        
        .leaflet-popup-tip {{
            background: var(--bg-card);
            border: 1px solid var(--border);
        }}
        
        .custom-marker {{
            background: var(--accent);
            border-radius: 50%;
            border: 3px solid white;
            box-shadow: 0 4px 20px rgba(99, 102, 241, 0.5);
        }}
    </style>
</head>
<body>
    <div class="bg-pattern"></div>
    
    <div class="container">
        <header>
            <h1>🌐 VPN Mesh Network</h1>
            <p class="subtitle">Decentralized VPN exit nodes powered by OpenClaw agents</p>
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
                <div class="stat-value">24/7</div>
                <div class="stat-label">Always On</div>
            </div>
        </div>
        
        <div class="map-container">
            <div class="map-overlay">
                <h3>Network Status</h3>
                <div class="live-indicator">
                    <div class="pulse"></div>
                    <span>Live</span>
                </div>
            </div>
            <div id="map"></div>
        </div>
        
        <div class="nodes-section">
            <div class="section-header">
                <h2>🖧 All Nodes ({total_nodes})</h2>
                <span style="color: var(--text-secondary); font-size: 0.9em;">Click to connect</span>
            </div>
            
            {"<div class='nodes-grid'>" if nodes else "<div class='empty-state'><h2>No nodes online yet</h2><p>Be the first to join the network! Install the vpn-mesh skill and run setup to become a node.</p></div>"}
"""

    for node in nodes:
        country = node.get("country", "XX")
        flag = FLAG_EMOJI.get(country, "🏳️")
        name = COUNTRY_NAMES.get(country, country)
        coords = get_coords(country)
        is_current = node.get("public_key") == current_pubkey
        
        html += f"""
            <div class="node-card">
                <div class="node-header">
                    <div>
                        <div class="node-id">{node.get('node_id', 'Unknown')}{"</span>" if is_current else ""}</div>
                        <span style="font-size: 0.8em; color: var(--text-secondary);">{"Your node" if is_current else flag + " " + name}</span>
                    </div>
                    <div class="node-flag">{flag}</div>
                </div>
                <div class="node-info">
                    <div class="info-item">
                        <span class="info-label">City</span>
                        <span class="info-value">{node.get('city', name)}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Uptime</span>
                        <span class="info-value">{node.get('uptime', '100%')}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Endpoint</span>
                        <span class="info-value" style="font-family: 'JetBrains Mono', monospace; font-size: 0.85em;">{node.get('endpoint', 'N/A')}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Last Seen</span>
                        <span class="info-value">{node.get('updated', 'Unknown')[:10]}</span>
                    </div>
                </div>
                <div class="node-status online">
                    <span>●</span> Online
                </div>
                {"<button class='connect-btn' onclick=\"alert('Connected! Use: vpn_mesh connect " + node.get('node_id', '') + "')\">🌐 Connect to this node</button>" if not is_current else "<button class='connect-btn' style='background: var(--bg-secondary); cursor: default;'>✓ This is your node</button>"}
            </div>"""
    
    if nodes:
        html += "</div>"
    
    html += f"""
        </div>
        
        <footer>
            <p>🌐 VPN Mesh Network · Powered by <a href="https://openclaw.ai">OpenClaw</a> · <a href="https://clawhub.com/skills/vpn-mesh">Get the skill</a></p>
            <p style="margin-top: 8px; opacity: 0.6;">Secure · Decentralized · Agent-native VPN mesh</p>
        </footer>
    </div>
    
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        // Initialize map
        const map = L.map('map', {{
            center: [20, 0],
            zoom: 2,
            minZoom: 2,
            maxZoom: 8,
            scrollWheelZoom: true,
        }});
        
        // Dark map tiles
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
            maxZoom: 19
        }}).addTo(map);
        
        // Node data
        const nodes = {nodes_json};
        const coords = {coords_json};
        
        // Custom node icon
        const nodeIcon = L.divIcon({{
            className: 'custom-marker',
            iconSize: [16, 16],
            iconAnchor: [8, 8],
        }});
        
        // Add nodes to map
        const markers = [];
        nodes.forEach((node, i) => {{
            const country = node.country || 'XX';
            const coord = coords[country] || [20, 0];
            const flag = {{""" + ", ".join(f'"{k}": "{v}"' for k, v in FLAG_EMOJI.items()) + """}}[country] || '🏳️';
            
            const marker = L.marker(coord, {{ icon: nodeIcon }}).addTo(map);
            
            const popup = L.popup({{
                closeButton: false,
                className: 'node-popup'
            }}).setContent(`
                <div style="min-width: 180px;">
                    <div style="font-size: 1.2em; font-weight: 600; margin-bottom: 4px;">
                        {flag} ${{node.node_id}}
                    </div>
                    <div style="color: #a0a0b0; font-size: 0.9em; margin-bottom: 8px;">
                        ${{node.city || country}}
                    </div>
                    <div style="font-size: 0.8em; color: #a0a0b0;">
                        ● Online · ${{node.uptime || '100%'}} uptime
                    </div>
                </div>
            `);
            
            marker.bindPopup(popup);
            markers.push({{ marker, node }});
            
            // Animate marker on hover
            marker.on('mouseover', function() {{
                this.getElement().style.transform = 'scale(1.5)';
                this.getElement().style.transition = 'transform 0.2s';
            }});
            
            marker.on('mouseout', function() {{
                this.getElement().style.transform = 'scale(1)';
            }});
        }});
        
        // Draw connection lines between nearby nodes (visual effect)
        for (let i = 0; i < markers.length; i++) {{
            for (let j = i + 1; j < markers.length; j++) {{
                const coord1 = coords[markers[i].node.country] || [20, 0];
                const coord2 = coords[markers[j].node.country] || [20, 0];
                
                // Only draw line if nodes are in same region
                const latDiff = Math.abs(coord1[0] - coord2[0]);
                const lonDiff = Math.abs(coord1[1] - coord2[1]);
                
                if (latDiff < 30 && lonDiff < 30) {{
                    const polyline = L.polyline([coord1, coord2], {{
                        color: 'rgba(99, 102, 241, 0.2)',
                        weight: 1,
                        dashArray: '5, 10'
                    }}).addTo(map);
                }}
            }}
        }}
        
        // Auto-refresh every 30 seconds
        setTimeout(() => {{
            location.reload();
        }}, 30000);
    </script>
</body>
</html>"""
    
    return html


def main():
    nodes = load_nodes()
    
    if "--demo" in sys.argv:
        # Use demo nodes
        demo_path = MESH_DIR / "demo_nodes.json"
        if demo_path.exists():
            nodes = json.loads(demo_path.read_text())
    
    html = generate_html(nodes)
    
    output = MESH_DIR / "mesh-map.html"
    output.write_text(html, encoding='utf-8')
    
    print(f"""
✅ VPN Mesh Map Generated
━━━━━━━━━━━━━━━━━━━━━━━━━

📍 Location: {output}
🖧 Nodes shown: {len(nodes)}
🌐 Countries: {len(set(n.get('country', 'XX') for n in nodes))}

Open in browser to see the interactive world map.

To include demo nodes:
   python3 mesh_map.py --demo

To show real network nodes:
   python3 mesh_map.py

━━━━━━━━━━━━━━━━━━━━━━━━━
    """)


if __name__ == "__main__":
    main()