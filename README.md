# VPN Mesh 🌐

**Decentralized VPN network for AI agents.** Turn your OpenClaw agent into a secure VPN exit node. Route traffic through peer nodes worldwide with one command.

[![Published on ClawHub](https://img.shields.io/badge/ClawHub-Install-blue)](https://clawhub.ai/stigg86/vpn-mesh)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

**[🌐 View Live Network Map](https://stigg86.github.io/vpn-mesh/)** — Auto-updates every 60 seconds.

---

## ⚠️ Prerequisites

**Before installing, you need:**

1. **Root/sudo access** — WireGuard requires system-level installation
2. **WireGuard tools** — Install with: `sudo apt-get install wireguard-tools`

---

## 🚀 Quick Start

### 1. Install WireGuard (requires sudo)

```bash
sudo apt-get update && sudo apt-get install -y wireguard-tools
```

Verify: `wg --version`

### 2. Install the skill

```bash
clawhub install vpn-mesh
```

### 3. Setup and announce your node

```bash
python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py setup
```

### 4. Start the VPN (requires sudo)

```bash
sudo wg-quick up ~/.openclaw/vpn-mesh/wg0.conf
```

### 5. Verify it worked

```bash
python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py status
```

Your node should now show as 🟢 **Online** on the [Live Map](https://stigg86.github.io/vpn-mesh/)!

---

## 📡 Commands

| Command | Description |
|---------|-------------|
| `vpn_mesh.py setup` | Create keys, detect location, announce to registry |
| `vpn_mesh.py status` | Show node info and connection state |
| `vpn_mesh.py list` | Show all nodes in the mesh network |
| `vpn_mesh.py announce` | Re-announce to registry (if needed) |
| `wg-quick up wg0.conf` | Start the VPN interface |
| `wg-quick down wg0.conf` | Stop the VPN interface |

---

## 🔧 Troubleshooting

### "wg: command not found"
WireGuard is not installed. Run:
```bash
sudo apt-get update && sudo apt-get install -y wireguard-tools
```

### "Permission denied" on wg-quick up
You need sudo access. Make sure your user is in the `sudo` group:
```bash
sudo usermod -aG sudo $USER
# Then log out and back in
```

### Node shows as ⚫ Offline on the map
- Check WireGuard is running: `sudo wg show`
- Re-announce: `python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py announce`
- Check firewall: UDP port 51820 must be open

---

## 🌍 How It Works

1. Each node generates a WireGuard keypair
2. Node announces itself to a shared GitHub Gist registry
3. Other nodes can discover peers and create mesh tunnels
4. Traffic is routed through the mesh network encrypted

---

## 📊 Current Network

View the live map at: **https://stigg86.github.io/vpn-mesh/**

---

## 📝 Files

- `SKILL.md` — OpenClaw skill definition (for agents)
- `README.md` — This file (for humans)
- `scripts/vpn_mesh.py` — Main CLI tool
- `scripts/setup.sh` — Setup helper script
- `scripts/mesh_map.py` — Map generator

---

## 🤝 Contributing

Issues and PRs welcome! [GitHub Repository](https://github.com/stigg86/vpn-mesh)