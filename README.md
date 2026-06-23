# UDP → HLS Stream Transcoder

A complete pipeline to receive **live UDP/multicast streams** and serve them as **HLS** to any browser or video player.

This repo contains **two systems**:

| System | Folder | Purpose |
|--------|--------|---------|
| **Windows Dev** | `/` (root) | Local test stream generator + HLS server |
| **Linux Production** | `linux-server/` | Real multicast UDP → HLS for live TV/broadcast |

---

## 🪟 Windows — Local Test System

Generates a fake UDP test stream (color bars) and converts it to HLS.
Great for testing and development without a real source.

### Requirements
- Python 3.7+
- FFmpeg in PATH → https://www.gyan.dev/ffmpeg/builds/

### Run
```powershell
# Terminal 1 — Generate test UDP stream
python start_udp_stream.py

# Terminal 2 — Transcode UDP to HLS
python start_hls_transcoder.py

# Terminal 3 — Serve HLS over HTTP
python serve_hls.py
```

Open: **http://localhost:8080/**

Or start everything at once:
```powershell
python start_all.py
```

---

## 🐧 Linux Production — Multi-Stream Transcoder

Receives real **multicast UDP streams** and converts all of them to HLS simultaneously.

### Architecture
```
[Multicast Source 239.168.1.10:PORT x N]
              |
              ▼
   [Linux Server 192.168.90.116]
    FFmpeg worker per stream + auto-restart
              |
              ▼
   [/var/www/hls/{channel}/stream.m3u8]
              |
              ▼
   [HTTP Server :8080]
              |
              ▼
   [Browser / VLC / any HLS player]
```

### Quick Deploy

```bash
# 1. Copy to your Linux server
scp -r linux-server/ root@192.168.90.116:/opt/udp-hls

# 2. SSH in and run setup
ssh root@192.168.90.116
cd /opt/udp-hls
sudo bash scripts/setup.sh

# 3. Edit config
nano config.py

# 4. Start services
sudo systemctl start udp-hls-transcoder
sudo systemctl start udp-hls-server
```

Open: **http://192.168.90.116:8080/**

---

## 📁 Full Project Structure

```
udp-hls-system/
│
├── 🪟 WINDOWS TEST SYSTEM
├── config.py                  # UDP address, HLS params
├── start_udp_stream.py        # Generates live test UDP stream
├── start_hls_transcoder.py    # UDP → HLS transcoder
├── serve_hls.py               # HTTP server
├── start_all.py               # Launch everything at once
├── player/index.html          # Web player (hls.js)
│
└── 🐧 LINUX PRODUCTION SYSTEM
    └── linux-server/
        ├── config.py          # Streams list, interface, codec settings
        ├── transcoder.py      # Multi-stream FFmpeg manager + auto-restart
        ├── serve_hls.py       # HTTP server + /api/streams JSON endpoint
        ├── player/index.html  # Multi-stream dashboard with sidebar
        └── scripts/
            ├── setup.sh       # One-time install (ffmpeg, dirs, systemd)
            ├── start.sh       # Start without systemd
            ├── stop.sh        # Stop all services
            └── status.sh      # Check processes + HLS output
```

---

## 🔧 Key Config (linux-server/config.py)

```python
SERVER_IP           = "192.168.90.116"
MULTICAST_INTERFACE = "ens1f0"        # find with: ip addr
MULTICAST_GROUP     = "239.168.1.10"

STREAMS = [
    {"name": "ch01", "port": 7250, "label": "Channel 01"},
    {"name": "ch02", "port": 7260, "label": "Channel 02"},
]

VIDEO_CODEC = "copy"   # lowest CPU — just remux
AUDIO_CODEC = "aac"
```

---

## 🚀 Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: UDP to HLS transcoder"
git remote add origin https://github.com/YOUR_USERNAME/udp-hls-system.git
git push -u origin main
```