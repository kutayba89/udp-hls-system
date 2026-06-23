#!/bin/bash
# Stop all UDP-HLS services

PID_FILE="/tmp/udp-hls.pids"

echo ""
echo "[INFO] Stopping UDP-HLS services..."

# Stop via PID file
if [ -f "$PID_FILE" ]; then
    while read pid; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            echo "  Stopped PID $pid"
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
else
    echo "  No PID file found — killing by name..."
fi

# Also kill any remaining ffmpeg/python processes for this project
pkill -f "transcoder.py" 2>/dev/null && echo "  Stopped transcoder.py" || true
pkill -f "serve_hls.py"   2>/dev/null && echo "  Stopped serve_hls.py"  || true

# Kill all child ffmpeg processes
pkill -f ffmpeg 2>/dev/null && echo "  Stopped ffmpeg processes" || true

echo ""
echo "[INFO] All services stopped."
echo ""