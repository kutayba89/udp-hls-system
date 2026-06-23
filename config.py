"""
Shared configuration for the UDP-HLS transcoder pipeline.
Edit these values to customize the stream settings.
"""

# ─── UDP Stream Settings ───────────────────────────────────────────────────────
UDP_ADDRESS = "127.0.0.1"           # Localhost (unicast - reliable on Windows)
UDP_PORT = 5000                     # UDP port
UDP_URL = f"udp://{UDP_ADDRESS}:{UDP_PORT}?pkt_size=1316"

# ─── Video Source Settings ─────────────────────────────────────────────────────
# These control the generated test stream
VIDEO_RESOLUTION = "1280x720"       # 720p
VIDEO_FRAMERATE = 30                # FPS
VIDEO_BITRATE = "2500k"             # Video bitrate
AUDIO_BITRATE = "128k"             # Audio bitrate
AUDIO_SAMPLE_RATE = 44100          # Audio sample rate

# ─── HLS Output Settings ──────────────────────────────────────────────────────
HLS_OUTPUT_DIR = "hls_output"       # Directory for HLS segments
HLS_SEGMENT_DURATION = 4           # Seconds per segment
HLS_PLAYLIST_SIZE = 5              # Number of segments to keep in playlist
HLS_SEGMENT_FILENAME = "segment_%03d.ts"
HLS_PLAYLIST_FILENAME = "stream.m3u8"

# ─── HTTP Server Settings ─────────────────────────────────────────────────────
HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8080