"""
UDP → HLS Transcoder — Linux Production Config
Loads stream definitions from streams.csv.
"""

import csv
from pathlib import Path

# ─── Network Settings ─────────────────────────────────────────────────────────
# FFmpeg localaddr expects the LOCAL IP address of the multicast NIC, not interface name.
# Your multicast NIC ens1f0 = 192.168.2.117
MULTICAST_INTERFACE = "192.168.2.117"
SERVER_IP = "192.168.90.116"
MULTICAST_GROUP = "239.168.1.10"  # fallback only

# If True, FFmpeg will accept packets only from each stream's source_ip.
# If any stream fails, set this False and restart.
USE_SOURCE_FILTER = True

# ─── FFmpeg Transcoding Settings ──────────────────────────────────────────────
VIDEO_CODEC = "copy"       # fastest: remux only
AUDIO_CODEC = "aac"        # use "copy" if source audio is already HLS-compatible
VIDEO_BITRATE = "2500k"
AUDIO_BITRATE = "128k"
AUDIO_SAMPLE_RATE = 48000

# ─── HLS Output Settings ──────────────────────────────────────────────────────
HLS_BASE_DIR = "/var/www/hls"
HLS_SEGMENT_SECONDS = 4
HLS_PLAYLIST_SIZE = 5
HLS_SEGMENT_PATTERN = "seg_%05d.ts"

# ─── HTTP Server Settings ─────────────────────────────────────────────────────
HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8090

# ─── Process Settings ─────────────────────────────────────────────────────────
LOG_DIR = "/var/log/udp-hls"
FFMPEG_RESTART_DELAY = 5
MAX_RESTART_ATTEMPTS = 10  # 0 = unlimited


def load_streams():
    csv_path = Path(__file__).with_name("streams.csv")
    streams = []
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["port"] = int(row["port"])
            # Per-stream codec overrides. Blank values fall back to global defaults.
            row["video_codec"] = row.get("video_codec") or VIDEO_CODEC
            row["audio_codec"] = row.get("audio_codec") or AUDIO_CODEC
            streams.append(row)
    return streams


STREAMS = load_streams()
