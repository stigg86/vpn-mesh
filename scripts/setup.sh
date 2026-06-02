#!/bin/bash
# VPN Mesh Node Setup
# Installs and configures your node for the mesh network

set -e

MESH_DIR="${MESH_DIR:-$HOME/.openclaw/vpn-mesh}"
CONFIG_DIR="${MESH_DIR}/configs"
REGISTRY="${MESH_DIR}/registry.json"
CONFIG="${MESH_DIR}/wg0.conf"
PRIVATE_KEY_FILE="${MESH_DIR}/private.key"
PUBLIC_KEY_FILE="${MESH_DIR}/public.key"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "=========================================="
echo "   🌐 VPN Mesh Node Setup"
echo "=========================================="
echo -e "${NC}"
echo ""

# Check if already configured
if [ -f "$REGISTRY" ]; then
    echo -e "${YELLOW}⚠️  Node already configured at $MESH_DIR${NC}"
    echo "   Run 'vpn_mesh.py status' to see your node info"
    echo "   Delete $REGISTRY to reconfigure"
    exit 0
fi

mkdir -p "$MESH_DIR" "$CONFIG_DIR"

# Check for WireGuard
check_wireguard() {
    if command -v wg &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Check for Docker (alternative)
check_docker() {
    if command -v docker &> /dev/null; then
        return 0
    else
        return 1
    fi
}

echo -e "${GREEN}✓${NC} Mesh directory created: $MESH_DIR"
echo ""

# Try WireGuard first, then Docker, then generate keys anyway
if check_wireguard; then
    echo -e "${GREEN}✓${NC} WireGuard found"
    WG_AVAILABLE=true
elif check_docker; then
    echo -e "${YELLOW}⚠️${NC} WireGuard not installed, but Docker found"
    echo "   You can run WireGuard in Docker or install WireGuard manually"
    WG_MODE="docker"
else
    echo -e "${YELLOW}⚠️${NC} Neither WireGuard nor Docker found"
    echo "   Node will be configured but VPN tunnel requires WireGuard"
    echo "   Install with: sudo apt install wireguard"
    WG_MODE="none"
fi

# Generate WireGuard keys if wg is available
if [ "$WG_AVAILABLE" = true ]; then
    echo ""
    echo "🔐 Generating WireGuard keypair..."
    
    PRIVATE_KEY=$(wg genkey)
    PUBLIC_KEY=$(echo "$PRIVATE_KEY" | wg pubkey)
    
    echo "$PRIVATE_KEY" > "$PRIVATE_KEY_FILE"
    echo "$PUBLIC_KEY" > "$PUBLIC_KEY_FILE"
    chmod 600 "$PRIVATE_KEY_FILE"
    
    echo -e "${GREEN}✓${NC} Keys generated"
fi

# Get node information
NODE_ID="${NODE_ID:-$(hostname | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]'- | head -20)}"

# Get external IP
echo ""
echo "🌐 Detecting external IP..."
EXTERNAL_IP=$(curl -s -m 5 https://ipapi.co/ip 2>/dev/null || echo "unknown")
echo -e "${GREEN}✓${NC} External IP: $EXTERNAL_IP"

# Get country
COUNTRY=$(curl -s -m 5 https://ipapi.co/country 2>/dev/null || echo "XX")
CITY=$(curl -s -m 5 https://ipapi.co/city 2>/dev/null || echo "Unknown")

# Get default interface
DEFAULT_IFACE=$(ip -4 route show default 2>/dev/null | awk '{print $5}' | head -1 || echo "eth0")

# VPN config
VPN_IP="10.0.0.2/24"
LISTEN_PORT=51820

# Country names
declare -A COUNTRY_NAMES
COUNTRY_NAMES["ES"]="Spain"
COUNTRY_NAMES["GB"]="United Kingdom"
COUNTRY_NAMES["US"]="United States"
COUNTRY_NAMES["DE"]="Germany"
COUNTRY_NAMES["FR"]="France"
COUNTRY_NAMES["NL"]="Netherlands"
COUNTRY_NAMES["SE"]="Sweden"
COUNTRY_NAMES["NO"]="Norway"
COUNTRY_NAMES["FI"]="Finland"
COUNTRY_NAMES["DK"]="Denmark"
COUNTRY_NAMES["PL"]="Poland"
COUNTRY_NAMES["IT"]="Italy"
COUNTRY_NAMES["PT"]="Portugal"
COUNTRY_NAMES["IE"]="Ireland"
COUNTRY_NAMES["BE"]="Belgium"
COUNTRY_NAMES["AT"]="Austria"
COUNTRY_NAMES["CH"]="Switzerland"
COUNTRY_NAMES["AU"]="Australia"
COUNTRY_NAMES["CA"]="Canada"
COUNTRY_NAMES["JP"]="Japan"
COUNTRY_NAMES["KR"]="South Korea"
COUNTRY_NAMES["SG"]="Singapore"
COUNTRY_NAMES["IN"]="India"
COUNTRY_NAMES["BR"]="Brazil"

COUNTRY_NAME="${COUNTRY_NAMES[$COUNTRY]:-$COUNTRY}"

echo -e "${GREEN}✓${NC} Location: $CITY, $COUNTRY_NAME"

# Create registry entry
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ "$WG_AVAILABLE" = true ]; then
    cat > "$REGISTRY" << EOF
{
  "node_id": "$NODE_ID",
  "public_key": "$PUBLIC_KEY",
  "endpoint": "$EXTERNAL_IP:$LISTEN_PORT",
  "vpn_ip": "$VPN_IP",
  "country": "$COUNTRY",
  "city": "$CITY",
  "version": "0.3.0",
  "uptime": "100%",
  "updated": "$TIMESTAMP"
}
EOF

    # Create WireGuard config
    cat > "$CONFIG" << EOF
[Interface]
PrivateKey = $PRIVATE_KEY
Address = $VPN_IP
ListenPort = $LISTEN_PORT

# NAT/masquerade for forwarding peer traffic
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o $DEFAULT_IFACE -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o $DEFAULT_IFACE -j MASQUERADE
EOF

    chmod 600 "$CONFIG"
    
    echo ""
    echo -e "${GREEN}✅ VPN Mesh node '$NODE_ID' configured!${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "   🇪🇸 Country: ${CYAN}$COUNTRY_NAME${NC}"
    echo -e "   📍 City: ${CYAN}$CITY${NC}"
    echo -e "   🌐 Endpoint: ${CYAN}$EXTERNAL_IP:$LISTEN_PORT${NC}"
    echo -e "   🔑 Public Key: ${CYAN}$PUBLIC_KEY${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "${YELLOW}To start VPN interface:${NC}"
    echo "   sudo wg-quick up $CONFIG"
    echo ""
    echo -e "${YELLOW}To connect to this node, other nodes need your public key.${NC}"
    echo "   Run: vpn_mesh.py status"
    
else
    # No WireGuard - create registry without keys
    cat > "$REGISTRY" << EOF
{
  "node_id": "$NODE_ID",
  "endpoint": "$EXTERNAL_IP:$LISTEN_PORT",
  "country": "$COUNTRY",
  "city": "$CITY",
  "version": "0.3.0",
  "uptime": "100%",
  "updated": "$TIMESTAMP",
  "note": "WireGuard not installed - install with: sudo apt install wireguard"
}
EOF

    echo ""
    echo -e "${GREEN}✅ Node registered (WireGuard pending install)${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "   🇪🇸 Country: ${CYAN}$COUNTRY_NAME${NC}"
    echo -e "   📍 City: ${CYAN}$CITY${NC}"
    echo -e "   🌐 Endpoint: ${CYAN}$EXTERNAL_IP:$LISTEN_PORT${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "${RED}Next step - install WireGuard:${NC}"
    echo "   sudo apt update && sudo apt install wireguard"
    echo ""
    echo "Then run setup again: vpn_mesh.py setup"
fi

echo ""
echo -e "${CYAN}Files saved:${NC}"
echo "   Registry: $REGISTRY"
echo "   Config: $CONFIG"
echo "   Keys: $PRIVATE_KEY_FILE, $PUBLIC_KEY_FILE"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo "   1. Install WireGuard if not already: sudo apt install wireguard"
echo "   2. Start VPN: sudo wg-quick up $CONFIG"
echo "   3. Check status: python3 ~/.openclaw/skills/vpn-mesh/scripts/vpn_mesh.py status"
echo "   4. Share your public key with other node operators"