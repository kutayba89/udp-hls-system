#!/bin/bash
# Show status of all UDP-HLS services and recent HLS output

SERVER_IP="192.168.90.116"
HTTP_PORT="8080"
HLS_DIR="/var/www/hls"
PID_FILE="/tmp/udp-hls.pids"
TRANSCODER_LOG="/tmp/udp-hls-transcoder.log"
SERVER_LOG="/tmp/udp-hls-server.log"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "============================================================"
echo "  UDP-HLS STATUS CHECK"
echo "============================================================"

# Process status
echo ""
echo "--- Processes ---"
if [ -f "$PID_FILE" ]; then
    while read pid; do
        if kill -0 "$pid" 2>/dev/null; then
            CMD=$(ps -p "$pid" -o comm= 2>/dev/null)
            echo -e "  PID $pid : ${GREEN}RUNNING${NC} ($CMD)"
        else
            echo -e "  PID $pid : ${RED}DEAD${NC}"
        fi
    done < "$PID_FILE"
else
    echo "  No PID file found."
fi

# FFmpeg processes
FFMPEG_COUNT=$(pgrep -c ffmpeg 2>/dev/null || echo 0)
echo ""
echo "--- FFmpeg Processes: $FFMPEG_COUNT ---"
pgrep -a ffmpeg 2>/dev/null | while read line; do
    echo "  $line"
done

# HTTP server check
echo ""
echo "--- HTTP Server ---"
if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$HTTP_PORT/api/streams" | grep -q "200"; then
    echo -e "  http://localhost:$HTTP_PORT  ${GREEN}ONLINE${NC}"
    echo ""
    echo "  Streams:"
    curl -s "http://localhost:$HTTP_PORT/api/streams" 2>/dev/null | \
        python3 -c "
import json,sys
data=json.load(sys.stdin)
for s in data:
    status = 'LIVE' if s['ready'] else 'WAIT'
    print(f\"    [{status}]  {s['name']:<8} port={s['port']:<6} segs={s['segments']:<4} {s['label']}\")
print(f'\\n  Total: {len(data)} streams')
" 2>/dev/null
else
    echo -e "  http://localhost:$HTTP_PORT  ${RED}OFFLINE${NC}"
fi

# HLS output check
echo ""
echo "--- HLS Output ($HLS_DIR) ---"
if [ -d "$HLS_DIR" ]; then
    STREAM_COUNT=$(find "$HLS_DIR" -name "stream.m3u8" 2>/dev/null | wc -l)
    echo "  Active playlists : $STREAM_COUNT"
    find "$HLS_DIR" -name "stream.m3u8" 2>/dev/null | while read f; do
        DIR=$(dirname "$f")
        NAME=$(basename "$DIR")
        SEGS=$(find "$DIR" -name "*.ts" 2>/dev/null | wc -l)
        AGE=$(stat -c %Y "$f" 2>/dev/null)
        NOW=$(date +%s)
        DIFF=$((NOW - AGE))
        echo "    $NAME : $SEGS segments  (updated ${DIFF}s ago)"
    done
else
    echo "  $HLS_DIR not found"
fi

# Recent logs
echo ""
echo "--- Recent Transcoder Log (last 10 lines) ---"
if [ -f "$TRANSCODER_LOG" ]; then
    tail -10 "$TRANSCODER_LOG"
else
    echo "  No log file at $TRANSCODER_LOG"
fi

echo ""
echo "============================================================"