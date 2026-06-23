"""
UDP → HLS Transcoder
====================
Reads a live UDP stream and transcodes it into HLS segments + playlist.

Prerequisites:
  - The UDP stream must be running (start_udp_stream.py)
  - FFmpeg must be installed

The HLS output is written to the hls_output/ directory:
  - stream.m3u8   (playlist)
  - segment_XXX.ts (video segments)

Press Ctrl+C to stop.
"""

import subprocess
import sys
import os
import signal
import shutil
import time
from config import (
    UDP_ADDRESS, UDP_PORT, UDP_URL,
    VIDEO_BITRATE, AUDIO_BITRATE, AUDIO_SAMPLE_RATE,
    VIDEO_FRAMERATE,
    HLS_OUTPUT_DIR, HLS_SEGMENT_DURATION, HLS_PLAYLIST_SIZE,
    HLS_SEGMENT_FILENAME, HLS_PLAYLIST_FILENAME,
)


def check_ffmpeg():
    """Verify FFmpeg is installed and accessible."""
    if shutil.which("ffmpeg") is None:
        print("=" * 60)
        print("ERROR: FFmpeg not found!")
        print("Please install FFmpeg and add it to your PATH.")
        print("=" * 60)
        sys.exit(1)
    print("[OK] FFmpeg found.")


def prepare_output_dir():
    """Create or clean the HLS output directory."""
    if os.path.exists(HLS_OUTPUT_DIR):
        # Clean old segments
        for f in os.listdir(HLS_OUTPUT_DIR):
            fp = os.path.join(HLS_OUTPUT_DIR, f)
            if os.path.isfile(fp):
                os.remove(fp)
        print(f"[OK] Cleaned existing output directory: {HLS_OUTPUT_DIR}/")
    else:
        os.makedirs(HLS_OUTPUT_DIR)
        print(f"[OK] Created output directory: {HLS_OUTPUT_DIR}/")


def build_ffmpeg_command():
    """
    Build the FFmpeg command to transcode UDP → HLS.
    
    This command:
      1. Receives the UDP multicast stream
      2. Re-encodes video with x264 (can also copy if same codec)
      3. Outputs HLS segments with a sliding window playlist
    """
    playlist_path = os.path.join(HLS_OUTPUT_DIR, HLS_PLAYLIST_FILENAME)
    segment_path = os.path.join(HLS_OUTPUT_DIR, HLS_SEGMENT_FILENAME)

    udp_input = f"udp://{UDP_ADDRESS}:{UDP_PORT}?overrun_nonfatal=1&fifo_size=50000000"

    cmd = [
        "ffmpeg",
        "-y",

        # ── Input: UDP stream ──
        "-fflags", "+genpts+discardcorrupt",
        "-i", udp_input,

        # ── Video encoding ──
        # Using copy to reduce CPU usage (stream is already h264)
        # Change to re-encode if you need different settings:
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",
        "-b:v", VIDEO_BITRATE,
        "-maxrate", VIDEO_BITRATE,
        "-bufsize", "5000k",
        "-pix_fmt", "yuv420p",
        "-g", str(VIDEO_FRAMERATE * 2),    # GOP = 2 seconds
        "-sc_threshold", "0",              # Disable scene-change keyframes

        # ── Audio encoding ──
        "-c:a", "aac",
        "-b:a", AUDIO_BITRATE,
        "-ar", str(AUDIO_SAMPLE_RATE),
        "-ac", "2",

        # ── HLS output ──
        "-f", "hls",
        "-hls_time", str(HLS_SEGMENT_DURATION),
        "-hls_list_size", str(HLS_PLAYLIST_SIZE),
        "-hls_flags", "delete_segments+append_list",
        "-hls_segment_type", "mpegts",
        "-hls_segment_filename", segment_path,
        "-hls_allow_cache", "0",

        playlist_path,
    ]

    return cmd


def main():
    check_ffmpeg()
    prepare_output_dir()

    cmd = build_ffmpeg_command()

    playlist_url = f"http://localhost:8080/hls/{HLS_PLAYLIST_FILENAME}"

    print("")
    print("=" * 60)
    print("  UDP → HLS TRANSCODER")
    print("=" * 60)
    print(f"  Input      : udp://@{UDP_ADDRESS}:{UDP_PORT}")
    print(f"  Output dir : {HLS_OUTPUT_DIR}/")
    print(f"  Playlist   : {HLS_OUTPUT_DIR}/{HLS_PLAYLIST_FILENAME}")
    print(f"  Segment len: {HLS_SEGMENT_DURATION}s")
    print(f"  Window size: {HLS_PLAYLIST_SIZE} segments")
    print("")
    print(f"  After starting the HTTP server, play at:")
    print(f"    {playlist_url}")
    print("")
    print("  Press Ctrl+C to stop.")
    print("=" * 60)
    print("")

    print(f"[CMD] {' '.join(cmd)}")
    print("")
    print("[INFO] Waiting for UDP stream... Make sure start_udp_stream.py is running!")
    print("")

    process = None

    def signal_handler(sig, frame):
        print("\n[INFO] Stopping HLS transcoder...")
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

        for line in process.stdout:
            print(line, end="")

        process.wait()
        if process.returncode != 0:
            print(f"\n[ERROR] FFmpeg exited with code {process.returncode}")
            sys.exit(process.returncode)

    except FileNotFoundError:
        print("[ERROR] FFmpeg executable not found.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        if process:
            process.terminate()
        sys.exit(1)


if __name__ == "__main__":
    main()