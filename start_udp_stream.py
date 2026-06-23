"""
UDP Stream Generator
====================
Generates a continuous live UDP stream using FFmpeg.
Uses a test pattern with a timestamp overlay and a sine wave tone.

You can view this stream in VLC:
  Media → Open Network Stream → udp://@127.0.0.1:5000

Press Ctrl+C to stop the stream.
"""

import subprocess
import sys
import signal
import shutil
from config import (
    UDP_ADDRESS, UDP_PORT,
    VIDEO_RESOLUTION, VIDEO_FRAMERATE, VIDEO_BITRATE,
    AUDIO_BITRATE, AUDIO_SAMPLE_RATE,
)


def check_ffmpeg():
    """Verify FFmpeg is installed and accessible."""
    if shutil.which("ffmpeg") is None:
        print("=" * 60)
        print("ERROR: FFmpeg not found!")
        print("")
        print("Please install FFmpeg and add it to your PATH.")
        print("Download: https://www.gyan.dev/ffmpeg/builds/")
        print("=" * 60)
        sys.exit(1)
    print("[OK] FFmpeg found.")


def build_ffmpeg_command():
    """
    Build the FFmpeg command to generate a UDP test stream.
    
    The stream includes:
      - SMPTE color bars test pattern
      - Timestamp + frame counter overlay (so you can see it's live)
      - Sine wave audio tone (440 Hz)
      - MPEG-TS container over UDP unicast
    """
    width, height = VIDEO_RESOLUTION.split("x")

    udp_url = f"udp://{UDP_ADDRESS}:{UDP_PORT}?pkt_size=1316"

    cmd = [
        "ffmpeg",
        # ── Overwrite / no interactive prompts ──
        "-re",                          # Read input at native framerate (simulate live)
        "-y",

        # ── Video source: test pattern ──
        "-f", "lavfi",
        "-i", f"testsrc2=size={VIDEO_RESOLUTION}:rate={VIDEO_FRAMERATE}",

        # ── Audio source: sine wave tone ──
        "-f", "lavfi",
        "-i", f"sine=frequency=440:sample_rate={AUDIO_SAMPLE_RATE}",

        # ── Video encoding ──
        "-c:v", "libx264",
        "-preset", "ultrafast",         # Low latency encoding
        "-tune", "zerolatency",         # Minimize latency
        "-b:v", VIDEO_BITRATE,
        "-maxrate", VIDEO_BITRATE,
        "-bufsize", "5000k",
        "-pix_fmt", "yuv420p",
        "-g", str(VIDEO_FRAMERATE * 2), # Keyframe every 2 seconds
        "-keyint_min", str(VIDEO_FRAMERATE),

        # ── Audio encoding ──
        "-c:a", "aac",
        "-b:a", AUDIO_BITRATE,
        "-ar", str(AUDIO_SAMPLE_RATE),

        # ── Output: MPEG-TS over UDP multicast ──
        "-f", "mpegts",
        udp_url,
    ]

    return cmd


def main():
    check_ffmpeg()

    cmd = build_ffmpeg_command()

    print("")
    print("=" * 60)
    print("  UDP STREAM GENERATOR")
    print("=" * 60)
    print(f"  Stream URL : udp://@{UDP_ADDRESS}:{UDP_PORT}")
    print(f"  Resolution : {VIDEO_RESOLUTION} @ {VIDEO_FRAMERATE}fps")
    print(f"  Bitrate    : {VIDEO_BITRATE} video / {AUDIO_BITRATE} audio")
    print("")
    print("  To view in VLC:")
    print(f"    Media → Open Network Stream → udp://@{UDP_ADDRESS}:{UDP_PORT}")
    print("")
    print("  Press Ctrl+C to stop.")
    print("=" * 60)
    print("")

    # Print the command for debugging
    print(f"[CMD] {' '.join(cmd)}")
    print("")

    process = None

    def signal_handler(sig, frame):
        print("\n[INFO] Stopping UDP stream...")
        if process:
            process.terminate()
            process.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )

        # Stream FFmpeg output to console
        for line in process.stdout:
            print(line, end="")

        process.wait()
        if process.returncode != 0:
            print(f"\n[ERROR] FFmpeg exited with code {process.returncode}")
            sys.exit(process.returncode)

    except FileNotFoundError:
        print("[ERROR] FFmpeg executable not found. Please install FFmpeg.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        if process:
            process.terminate()
        sys.exit(1)


if __name__ == "__main__":
    main()