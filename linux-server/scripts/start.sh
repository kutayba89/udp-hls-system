"#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║     UDP → HLS Transcoder — Quick Start (no systemd)         ║
# ║     Run from the linux-server/ directory                     ║
# ╚══════════════════════════════════════════════════════════════╝
#
# Usage:
#   chmod +x scripts/start.sh
#   ./scripts/start.sh
#
# Starts both the transcoder and HTTP server in the background.
# Logs go to /tmp/udp-hls-*.log
# Run scripts/stop.sh to stop everything.

set -e

SCRIPT_DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)\"
APP_DIR=\"$(dirname \"$SCRIPT_DIR\")\"
TRANSCODER_LOG=\"/tmp/udp-hls-transcoder.log\"
SERVER_LOG=\"/tmp/udp-hls-server.log\"
PID_FILE=\"/tmp/udp-hls.pids\"

echo \"\"
echo \"╔══════════════════════════════════════════════════════════════╗\"
echo \"║         UDP → HLS Transcoder — Starting Services            ║\"
echo \"╚══════════════════════════════════════════════════════════════╝\"
echo \"\"

# Check dependencies
command -v ffmpeg  >/dev/null 2>&1 || { echo \"[ERROR] FFmpeg not found. Run: sudo apt install ffmpeg\"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo \"[ERROR] Python3 not found. Run: sudo apt install python3\"; exit 1; }

cd \"$APP_DIR\"

# Create HLS output dir
mkdir -p /var/www/hls /var/log/udp-hls 2>/dev/null || mkdir -p ./hls_output

# Kill any existing instances
if [ -f \"$PID_FILE\" ]; then
    echo \"[INFO] Stopping previous instances...\"
    while read pid; do
        kill \"$pid\" 2>/dev/null && echo \"  Killed PID $pid\" || true
    done < \"$PID_FILE\"
    rm -f \"$PID_FILE\"
    sleep 2
fi

# Start transcoder
echo \"[1/2] Starting transcoder...\"
nohup python3 transcoder.py > \"$TRANSCODER_LOG\" 2>&1 &
TRANSCODER_PID=$!
echo $TRANSCODER_PID >> \"$PID_FILE\"
echo \"  PID: $TRANSCODER_PID  |  Log: $TRANSCODER_LOG\"

sleep 2

# Start HTTP server
echo \"[2/2] Starting HTTP server...\"
nohup python3 serve_hls.py > \"$SERVER_LOG\" 2>&1 &
SERVER_PID=$!
echo $SERVER_PID >> \"$PID_FILE\"
echo \"  PID: $SERVER_PID  |  Log: $SERVER_LOG\"

sleep 2

echo \"\"
echo \"╔══════════════════════════════════════════════════════════════╗\"
echo \"║  ✅ All services started!                                   ║\"
echo \"║                                                             ║\"
echo \"║  Web Player  :  http://192.168.90.116:8080/                 ║\"
echo \"║  Streams API :  http://192.168.90.116:8080/api/streams      ║\"
echo \"║  HLS example :  http://192.168.90.116:8080/hls/ch01/stream.m3u8 ║\"
echo \"║                                                             ║\"
echo \"║  Logs:                                                      ║\"
echo \"║    tail -f $TRANSCODER_LOG  ║\"
echo \"║    tail -f $SERVER_LOG          ║\"
echo \"║                                                             ║\"
echo \"║  Stop:  ./scripts/stop.sh                                   ║\"
echo \"╚══════════════════════════════════════════════════════════════╝\"
echo \"\""