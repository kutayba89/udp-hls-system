#!/bin/bash
# ============================================================
#  UDP → HLS Transcoder — Linux Server Setup Script
#  Run as root or with sudo: sudo bash setup.sh
#  Server: 192.168.90.116
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo ""
echo "============================================================"
echo "  UDP to HLS Transcoder - Setup"
echo "============================================================"
echo ""

if [ "$EUID" -ne 0 ]; then
  error "Please run as root: sudo bash setup.sh"
fi

# 1. Install dependencies
info "Updating package lists..."
apt-get update -qq
info "Installing ffmpeg, python3..."
apt-get install -y ffmpeg python3 python3-pip curl net-tools

FFMPEG_VER=$(ffmpeg -version 2>&1 | head -1)
info "FFmpeg: $FFMPEG_VER"

# 2. Create directories
info "Creating /var/www/hls ..."
mkdir -p /var/www/hls
chmod 755 /var/www/hls

info "Creating /var/log/udp-hls ..."
mkdir -p /var/log/udp-hls
chmod 755 /var/log/udp-hls

# 3. Copy project files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="/opt/udp-hls"

info "Installing project to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/scripts/"*.sh 2>/dev/null || true

# 4. Show interfaces
echo ""
info "Network interfaces detected:"
ip link show | grep -E "^[0-9]+:" | awk '{print "  " $2}' | tr -d ':'
warn "Edit /opt/udp-hls/config.py and set MULTICAST_INTERFACE correctly!"

# 5. Test multicast
echo ""
info "Testing multicast reception for 5 seconds..."
IFACE=$(ip route | grep default | awk '{print $5}' | head -1)
info "Testing on interface: $IFACE"
timeout 5 tcpdump -i "$IFACE" -c 5 "dst 239.168.1.10" 2>/dev/null && \
  info "Multicast traffic detected!" || \
  warn "No multicast traffic seen. Check IGMP/network settings."

# 6. Install systemd services
echo ""
info "Installing systemd services..."

cat > /etc/systemd/system/udp-hls-transcoder.service << EOF
[Unit]
Description=UDP to HLS Multi-Stream Transcoder
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/transcoder.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=udp-hls-transcoder

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/udp-hls-server.service << EOF
[Unit]
Description=UDP to HLS HTTP Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/serve_hls.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=udp-hls-server

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable udp-hls-transcoder udp-hls-server
info "Systemd services installed."

# 7. Firewall
if command -v ufw &>/dev/null; then
  info "Opening port 8080 in ufw..."
  ufw allow 8080/tcp || true
fi

# Done
echo ""
echo "============================================================"
echo "  SETUP COMPLETE!"
echo "============================================================"
echo ""
echo "  1. Edit config:   nano /opt/udp-hls/config.py"
echo "  2. Start:         sudo systemctl start udp-hls-transcoder"
echo "                    sudo systemctl start udp-hls-server"
echo "  3. Watch logs:    journalctl -u udp-hls-transcoder -f"
echo "  4. Open browser:  http://192.168.90.116:8080/"
echo "============================================================""#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║         UDP → HLS Transcoder — Linux Setup Script           ║
# ║                  Run once as root/sudo                       ║
# ╚══════════════════════════════════════════════════════════════╝
#
# What this does:
#   1. Installs FFmpeg and Python3
#   2. Creates required directories with correct permissions
#   3. Installs systemd services for auto-start on boot
#   4. Enables multicast routing on the network interface
#
# Usage:
#   chmod +x setup.sh
#   sudo ./setup.sh

set -e

# ── Config ─────────────────────────────────────────────────────────
APP_DIR=\"/opt/udp-hls\"
HLS_DIR=\"/var/www/hls\"
LOG_DIR=\"/var/log/udp-hls\"
SERVICE_USER=\"udphls\"
INTERFACE=\"ens1f0\"
MULTICAST_GROUP=\"239.168.1.10\"

# ── Colors ─────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         UDP → HLS Transcoder — Setup Script                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Check root ─────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "Please run as root: sudo ./setup.sh"

# ── Step 1: Install dependencies ───────────────────────────────────
info "Updating package list..."
apt-get update -qq

info "Installing FFmpeg and Python3..."
apt-get install -y ffmpeg python3 python3-pip net-tools iproute2 tcpdump
success "FFmpeg version: $(ffmpeg -version 2>&1 | head -1)"
success "Python version: $(python3 --version)"

# ── Step 2: Create system user ─────────────────────────────────────
if ! id -u \"$SERVICE_USER\" &>/dev/null; then
    info "Creating system user: $SERVICE_USER"
    useradd -r -s /bin/false -M \"$SERVICE_USER\"
    success "User $SERVICE_USER created"
else
    success "User $SERVICE_USER already exists"
fi

# ── Step 3: Create directories ─────────────────────────────────────
info "Creating directories..."
mkdir -p \"$APP_DIR\" \"$HLS_DIR\" \"$LOG_DIR\"
chown -R \"$SERVICE_USER:$SERVICE_USER\" \"$HLS_DIR\" \"$LOG_DIR\"
chmod -R 755 \"$HLS_DIR\"
success "Directories created"

# ── Step 4: Copy application files ─────────────────────────────────
info "Copying application files to $APP_DIR..."
SCRIPT_DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)\"
APP_SRC=\"$(dirname \"$SCRIPT_DIR\")\"   # parent of scripts/

cp -r \"$APP_SRC\"/*.py  \"$APP_DIR/\"
cp -r \"$APP_SRC/player\" \"$APP_DIR/\"
chown -R \"$SERVICE_USER:$SERVICE_USER\" \"$APP_DIR\"
success "Files copied to $APP_DIR"

# ── Step 5: Enable multicast on interface ──────────────────────────
info "Enabling multicast on interface $INTERFACE..."
ip link set \"$INTERFACE\" multicast on 2>/dev/null && success "Multicast enabled on $INTERFACE" || warn "Could not enable multicast — check interface name"

info "Adding multicast route for $MULTICAST_GROUP..."
ip route add \"${MULTICAST_GROUP}/8\" dev \"$INTERFACE\" 2>/dev/null && success "Multicast route added" || warn "Multicast route already exists or failed — check manually"

# ── Step 6: Install systemd services ───────────────────────────────
info "Installing systemd services..."

# Transcoder service
cat > /etc/systemd/system/udp-hls-transcoder.service << EOF
[Unit]
Description=UDP to HLS Multi-Stream Transcoder
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/transcoder.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=udp-hls-transcoder

[Install]
WantedBy=multi-user.target
EOF

# HTTP server service
cat > /etc/systemd/system/udp-hls-server.service << EOF
[Unit]
Description=UDP to HLS HTTP Stream Server
After=network.target udp-hls-transcoder.service
Wants=udp-hls-transcoder.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/serve_hls.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=udp-hls-server

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable udp-hls-transcoder udp-hls-server
success "Systemd services installed and enabled"

# ── Step 7: Open firewall port ─────────────────────────────────────
info "Opening firewall port 8080..."
if command -v ufw &>/dev/null; then
    ufw allow 8080/tcp && success "UFW: port 8080 opened"
elif command -v firewall-cmd &>/dev/null; then
    firewall-cmd --permanent --add-port=8080/tcp && firewall-cmd --reload && success "firewalld: port 8080 opened"
else
    warn "No firewall tool found — make sure port 8080 is accessible"
fi

# ── Done ───────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    SETUP COMPLETE!                          ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Start services:                                            ║"
echo "║    sudo systemctl start udp-hls-transcoder                  ║"
echo "║    sudo systemctl start udp-hls-server                      ║"
echo "║                                                             ║"
echo "║  Check status:                                              ║"
echo "║    sudo systemctl status udp-hls-transcoder                 ║"
echo "║    journalctl -u udp-hls-transcoder -f                      ║"
echo "║                                                             ║"
echo "║  Web Player:  http://192.168.90.116:8080/                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
"