"""
╔══════════════════════════════════════════════════════════════╗
║         UDP → HLS TRANSCODER  —  Linux Production Config     ║
╚══════════════════════════════════════════════════════════════╝

Edit this file to define your multicast streams and server settings.
Each stream in STREAMS list will get its own HLS output and playlist.
"""

# ─── Network Interface ────────────────────────────────────────────────────────
# The Linux network interface that receives multicast traffic
# Run `ip addr` on your server to find the correct one
MULTICAST_INTERFACE = "ens1f0"          # Change to your interface (e.g. eth0, ens3)
SERVER_IP           = "192.168.90.116"  # Your Linux server IP

# ─── Multicast Group ──────────────────────────────────────────────────────────
MULTICAST_GROUP = "239.168.1.10"        # Multicast group from your tcpdump

# ─── Stream Definitions ───────────────────────────────────────────────────────
# Add/remove streams here. Each entry:
#   "name"  : short slug used for folder name and playlist URL
#   "port"  : UDP port from your tcpdump
#   "label" : human-readable name shown in the web player
#
STREAMS = [
    {"name": "ch01", "port": 7250,  "label": "Channel 01 - 7250"},
    {"name": "ch02", "port": 7260,  "label": "Channel 02 - 7260"},
    {"name": "ch03", "port": 7270,  "label": "Channel 03 - 7270"},
    {"name": "ch04", "port": 7280,  "label": "Channel 04 - 7280"},
    {"name": "ch05", "port": 7290,  "label": "Channel 05 - 7290"},
    {"name": "ch06", "port": 7350,  "label": "Channel 06 - 7350"},
    {"name": "ch07", "port": 7360,  "label": "Channel 07 - 7360"},
    {"name": "ch08", "port": 7370,  "label": "Channel 08 - 7370"},
    {"name": "ch09", "port": 7380,  "label": "Channel 09 - 7380"},
    {"name": "ch10", "port": 7410,  "label": "Channel 10 - 7410"},
    {"name": "ch11", "port": 7420,  "label": "Channel 11 - 7420"},
    {"name": "ch12", "port": 7430,  "label": "Channel 12 - 7430"},
    {"name": "ch13", "port": 7440,  "label": "Channel 13 - 7440"},
    {"name": "ch14", "port": 7450,  "label": "Channel 14 - 7450"},
    {"name": "ch15", "port": 7460,  "label": "Channel 15 - 7460"},
    {"name": "ch16", "port": 7470,  "label": "Channel 16 - 7470"},
    {"name": "ch17", "port": 7480,  "label": "Channel 17 - 7480"},
    {"name": "ch18", "port": 7550,  "label": "Channel 18 - 7550"},
    {"name": "ch19", "port": 7560,  "label": "Channel 19 - 7560"},
    {"name": "ch20", "port": 7570,  "label": "Channel 20 - 7570"},
    {"name": "ch21", "port": 7580,  "label": "Channel 21 - 7580"},
    {"name": "ch22", "port": 7610,  "label": "Channel 22 - 7610"},
    {"name": "ch23", "port": 7830,  "label": "Channel 23 - 7830"},
    {"name": "ch24", "port": 7840,  "label": "Channel 24 - 7840"},
    {"name": "ch25", "port": 10444, "label": "Channel 25 - 10444"},
    {"name": "ch26", "port": 10555, "label": "Channel 26 - 10555"},
]

# ─── FFmpeg Transcoding Settings ──────────────────────────────────────────────
# Use "copy" to just remux without re-encoding (fastest, lowest CPU)
# Use "libx264" to re-encode (more CPU but lets you change bitrate/resolution)
VIDEO_CODEC         = "copy"       # "copy" or "libx264"
AUDIO_CODEC         = "aac"        # "copy" or "aac"
VIDEO_BITRATE       = "2500k"      # Only used when VIDEO_CODEC = "libx264"
AUDIO_BITRATE       = "128k"       # Only used when AUDIO_CODEC = "aac"
AUDIO_SAMPLE_RATE   = 48000        # 48000 for broadcast, 44100 for general

# ─── HLS Output Settings ──────────────────────────────────────────────────────
HLS_BASE_DIR        = "/var/www/hls"   # Root dir for all HLS output on Linux
HLS_SEGMENT_SECONDS = 4                # Segment duration in seconds
HLS_PLAYLIST_SIZE   = 5                # Segments kept in playlist (sliding window)
HLS_SEGMENT_PATTERN = "seg_%05d.ts"    # Segment filename pattern

# ─── HTTP Server Settings ─────────────────────────────────────────────────────
HTTP_HOST           = "0.0.0.0"
HTTP_PORT           = 8080

# ─── Process Settings ─────────────────────────────────────────────────────────
LOG_DIR             = "/var/log/udp-hls"   # Where per-stream logs are written
FFMPEG_RESTART_DELAY = 5                   # Seconds before restarting crashed stream
MAX_RESTART_ATTEMPTS = 10                  # 0 = unlimited restarts
EOF