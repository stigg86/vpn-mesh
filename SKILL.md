---
name: vpn-mesh
description: "Turn your OpenClaw agent into a secure VPN exit node. Mesh network for agents to route traffic through peer nodes worldwide."
metadata:
  {
    "version": "0.6.0",
    "openclaw": {
      "requires": { "bins": ["wg", "wg-quick"] },
      "install": [
        {
          "id": "wireguard",
          "kind": "system",
          "package": "wireguard-tools",
          "label": "WireGuard tools"
        }
      ],
      "post_install": "python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py setup"
    },
    "license": "MIT",
    "homepage": "https://github.com/stigg86/vpn-mesh",
    "allowed-tools": ["exec", "read", "write"]
  }
---

# VPN Mesh 🌐

**Decentralized VPN network for AI agents.** Turn your OpenClaw agent into a secure VPN exit node. Route traffic through peer nodes worldwide with one command.

```
Install:  clawhub install vpn-mesh
Setup:    Auto-runs on first use via `vpn_mesh.py setup`
Map:      https://stigg86.github.io/vpn-mesh/
```

## Live Network Map

**🌐 https://stigg86.github.io/vpn-mesh/** — Live map auto-updates every 60 seconds.

## Quick Start

```bash
# 1. Install the skill
clawhub install vpn-mesh

# 2. Setup & announce your node (auto-runs on install, announces to registry)
python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py setup

# 3. Start the VPN interface (requires WireGuard installed)
sudo wg-quick up ~/.openclaw/vpn-mesh/wg0.conf

# 4. View your node on the live map
#    https://stigg86.github.io/vpn-mesh/
```

## Commands

### `setup` — Configure and announce this node
```bash
python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py setup
```
Creates WireGuard keypair, detects your location, creates VPN config, and **announces to the public registry** so your node appears on the live map.

### `announce` — Re-announce to registry
```bash
python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py announce
```
Re-announces your node to the mesh registry.

### `status` — Show node info and connection state
```bash
python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py status
```
Shows:
- Node ID, country, city
- Public key (share this with others)
- Connection status
- Available peers in the mesh

### `list` — Show all mesh nodes
```bash
python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py list
```
Displays all nodes in the network with:
- 🇪🇸 Country flags
- 📍 City and endpoint
- 🔑 Public key (first 30 chars)

### `connect <node_id>` — Connect to a specific node
```bash
python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py connect node-id
```
Routes your agent's traffic through the specified peer node.

### `connect-country <CC>` — Connect to a country
```bash
python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py connect-country ES
```
Finds the best available node in the specified country and connects automatically.

**Supported countries:** ES, GB, US, DE, FR, NL, SE, NO, FI, DK, PL, IT, PT, IE, BE, AT, CH, AU, CA, JP, KR, SG, IN, BR

### `disconnect` — Revert to local routing
```bash
python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py disconnect
```
Stops routing through mesh, returns to normal internet.

### `pair` — Generate/share pairing code
```bash
# Generate your pairing code
python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py pair

# Connect using a code (from another node)
python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py pair SPAIN-ABC123
```

## Visual Map

Generate an interactive world map showing all mesh nodes:

```bash
# ASCII art map (terminal)
python3 ~/.openclaw/skills/vpn-mesh/scripts/mesh_map.py

# HTML map (open in browser)
python3 ~/.openclaw/skills/vpn-mesh/scripts/mesh_map.py --html

# With demo nodes
python3 ~/.openclaw/skills/vpn-mesh/scripts/mesh_map.py --demo --html
```

The HTML map shows:
- 🗺️ Interactive world map with node markers
- 📊 Stats: total nodes, countries, avg uptime
- 🔴 Live network status indicator
- 🖧 Node cards with connect buttons
- ✨ Dark theme, smooth animations

## Security

**Built on WireGuard — the gold standard of VPN security.**

### Private Key Protection
```
- Private key generated LOCALLY on your server
- Never transmitted over the network
- Stored with 600 permissions (root only)
- Each node has unique keypair
```

### Peer Authentication
```
- Only public keys exchanged between peers
- WireGuard handshake usesCurve25519
- Forward secrecy — compromised keys can't decrypt old traffic
- No passwords to brute-force
```

### Network Isolation
```
- Peers can only access VPN interface, not your local network
- iptables firewall locks down exposed services
- All traffic is encrypted end-to-end
- Compromised peer = revoke their public key, instant lockout
```

### Privacy by Design
```
- No central server to hack
- No user accounts or auth tokens
- Registry only contains public keys + endpoints
- Even if registry is compromised, attackers get nothing useful
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     VPN Mesh Network                     │
│                                                          │
│   ┌─────────┐         ┌─────────┐         ┌─────────┐ │
│   │ Node ES │◄────────►│ Node DE │◄────────►│ Node UK │ │
│   │(Spain)  │          │(Germany)│          │(London) │ │
│   └─────────┘         └─────────┘         └─────────┘ │
│        ▲                   ▲                   ▲       │
│        │                   │                   │       │
│   ┌────┴────┐         ┌────┴────┐         ┌────┴────┐ │
│   │ Your     │         │ Peer    │         │ Peer    │ │
│   │ Agent    │         │ Agent   │         │ Agent   │ │
│   └─────────┘         └─────────┘         └─────────┘ │
│                                                          │
│   Connect to any country with:                           │
│   vpn_mesh connect-country ES  → Routes through Spain    │
│   vpn_mesh connect-country DE  → Routes through Germany │
│   vpn_mesh connect-country UK  → Routes through UK      │
└─────────────────────────────────────────────────────────┘
```

## Mesh Architecture

**Full mesh network** — Every node is connected to every other node.
When you run `setup`, you automatically get all existing mesh nodes as WireGuard peers.

**For agents to use mesh nodes on-demand:**
1. Run `vpn_mesh.py list` to see available exit nodes
2. Run `vpn_mesh.py route <node_id>` to route ALL traffic through that node
3. Run `vpn_mesh.py stop-routing` to return to normal internet

**Example use case:**
- Your agent is on a Raspberry Pi in Spain
- A user asks for content only available in the US
- Agent runs `vpn_mesh.py route us-node` → traffic exits via US peer
- User gets US-restricted content ✅
- Agent runs `vpn_mesh.py stop-routing` → back to normal

## Use Cases

**1. Bypass geo-restrictions**
```
Spain blocks Polymarket → vpn_mesh connect-country GB → Access from UK
```

**2. Route AI agent through specific country**
```
Your agent in Spain → connects to German node → appears in Germany
```

**3. Decentralized privacy**
```
No single company controls the network. Each node is independent.
Traffic routes through peer nodes, not through a corporate VPN.
```

**4. Prediction market access**
```
Access prediction markets blocked in your country by connecting
through a node in a country where they're available.
```

## Registry

Nodes announce themselves to a shared registry (GitHub Gist by default).

**Registry format:**
```json
{
  "node_id": "stigs-umbrel",
  "public_key": "abc123...",
  "endpoint": "79.116.132.72:51820",
  "country": "ES",
  "city": "Lanzarote",
  "version": "0.3.0",
  "uptime": "99%",
  "updated": "2026-06-01T20:00:00Z"
}
```

**To use a custom registry:**
```bash
export VPN_MESH_REGISTRY=https://your-gist/raw/nodes.json
python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py list
```

## Troubleshooting

**WireGuard not installed:**
```bash
sudo apt update && sudo apt install wireguard
```

**Can't connect to peer:**
- Verify peer's public key matches
- Check endpoint IP:port is accessible
- Ensure both nodes have WireGuard running

**Node not showing on map:**
- Check registry.json exists at ~/.openclaw/vpn-mesh/
- Verify public_key is present
- Check last_updated timestamp

**Permission denied:**
```bash
sudo wg-quick up ~/.openclaw/vpn-mesh/wg0.conf
```

## Demo Mode

The skill includes demo nodes to showcase the visualization:

```bash
python3 ~/.openclaw/skills/vpn-mesh/scripts/mesh_map.py --demo --html
```

Shows 6 sample nodes across: Spain, Germany, UK, Netherlands, US, Japan

## Files

```
~/.openclaw/vpn-mesh/
├── registry.json      # Your node info
├── private.key        # Your private key (KEEP SECRET)
├── public.key        # Your public key (share this)
├── wg0.conf          # WireGuard config
├── demo_nodes.json   # Demo nodes for visualization
└── mesh-map.html     # Interactive world map
```

## License

MIT — Free to use, modify, and redistribute. No attribution required.