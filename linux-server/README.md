# UDP → HLS Multi-Stream Transcoder — Linux Production Server

## Overview

This system receives **live multicast UDP streams** and converts them to **HLS** for playback in any browser or video player.

```
[Multicast Source 239.168.1.10:PORT]
          |
          ▼
[Linux Server 192.168.90.116]
    FFmpeg x N (one per stream)
          |
          ▼
[/var/www/hls/{name}/stream.m3u8]
          |
          ▼
[HTTP Server :8080]
          |
          ▼
[Browser / VLC / any HLS player]
```

## Project Structure

```
linux-server/
├── config.py          # All settings: streams, ports, interface, codecs
├── transcoder.py      # Multi-stream FFmpeg manager with auto-restart
├── serve_hls.py       # HTTP server with CORS + /api/streams endpoint
├── player/
│   └── index.html     # Web dashboard with stream selector + hls.js player
└── scripts/
    ├── setup.sh       # One-time install (deps, dirs, systemd services)
    ├── start.sh       # Start without systemd (dev/test mode)
    ├── stop.sh        # Stop all services
    └── status.sh      # Check running processes, HLS output, HTTP server
```

## Quick Start

### Step 1 — Copy files to your Linux server

```bash
# From your Windows machine:
scp -r linux-server/ root@192.168.90.116:/opt/udp-hls

# Or use rsync:
rsync -avz linux-server/ root@192.168.90.116:/opt/udp-hls/
```

### Step 2 — SSH into your server

```bash
ssh root@192.168.90.116
cd /opt/udp-hls
```

### Step 3 — Run setup (first time only)

```bash
sudo bash scripts/setup.sh
```

This will:
- Install FFmpeg and Python3
- Create `/var/www/hls/` and `/var/log/udp-hls/`
- Install systemd services
- Test multicast reception

### Step 4 — Edit config

```bash
nano /opt/udp-hls/config.py
```

Key settings to check:
```python
MULTICAST_INTERFACE = "ens1f0"      # Your interface (check with: ip addr)
SERVER_IP           = "192.168.90.116"
MULTICAST_GROUP     = "239.168.1.10"
VIDEO_CODEC         = "copy"        # Use copy for lowest CPU usage
```

### Step 5 — Start services

**Option A — systemd (production, auto-starts on boot):**
```bash
sudo systemctl start udp-hls-transcoder
sudo systemctl start udp-hls-server
```

**Option B — manual (dev/test mode):**
```bash
bash scripts/start.sh
```

## Watch Your Streams

| Player | URL |
|--------|-----|
| **Browser dashboard** | http://192.168.90.116:8080/ |
| **Direct HLS (ch01)** | http://192.168.90.116:8080/hls/ch01/stream.m3u8 |
| **VLC** | Media → Open Network → paste HLS URL |
| **ffplay** | `ffplay http://192.168.90.116:8080/hls/ch01/stream.m3u8` |
| **Streams API** | http://192.168.90.116:8080/api/streams |

## Managing Streams

### Start only specific streams:
```bash
python3 transcoder.py --streams ch01 ch05 ch10
```

### List all configured streams:
```bash
python3 transcoder.py --list
```

### Check status:
```bash
bash scripts/status.sh
```

## Useful Commands

```bash
# Watch transcoder logs live
journalctl -u udp-hls-transcoder -f

# Watch HTTP server logs
journalctl -u udp-hls-server -f

# Check HLS output
ls -lh /var/www/hls/ch01/

# Test multicast reception manually
tcpdump -i ens1f0 -c 20 dst 239.168.1.10

# Test a single stream with ffprobe
ffprobe -v error -i "udp://@239.168.1.10:7250?localaddr=ens1f0"

# Watch a stream directly with ffplay
ffplay "udp://@239.168.1.10:7250?localaddr=ens1f0"

# Restart services
sudo systemctl restart udp-hls-transcoder
sudo systemctl restart udp-hls-server

# Stop everything
bash scripts/stop.sh
```

## Troubleshooting

### No HLS segments being created
```bash
# 1. Check multicast is arriving
tcpdump -i ens1f0 -c 10 dst 239.168.1.10

# 2. Test FFmpeg can receive the stream
ffprobe -v warning -i "udp://@239.168.1.10:7250?localaddr=ens1f0" -show_format

# 3. Check transcoder logs
tail -50 /var/log/udp-hls/ch01.log
```

### Wrong network interface
```bash
# List all interfaces
ip addr show

# Find which one has multicast traffic
tcpdump -i ens1f0 dst 239.168.1.10
tcpdump -i eth0   dst 239.168.1.10
```

### Permission denied on /var/www/hls
```bash
sudo chmod 777 /var/www/hls
sudo chown -R root:root /var/www/hls
```

### Port 8080 already in use
```bash
# Find what is using it
sudo lsof -i :8080
# Change port in config.py: HTTP_PORT = 9090
```

## Adding New Streams

Edit `config.py` and add entries to the `STREAMS` list:

```python
STREAMS = [
    {"name": "ch01", "port": 7250, "label": "Channel 01"},
    {"name": "newch", "port": 9999, "label": "My New Channel"},  # <-- add here
]
```

Then restart the transcoder:
```bash
sudo systemctl restart udp-hls-transcoder
```