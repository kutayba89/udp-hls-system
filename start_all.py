"""
Start All Services
==================
Launches all three components of the pipeline in separate processes:
  1. UDP Stream Generator
  2. HLS Transcoder
  3. HTTP Server

Press Ctrl+C to stop everything.
"""

import subprocess
import sys
import signal
import time
import os
import shutil


def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        print("=" * 60)
        print("ERROR: FFmpeg not found!")
        print("")
        print("Please install FFmpeg and add it to your PATH.")
        print("Download: https://www.gyan.dev/ffmpeg/builds/")
        print("=" * 60)
        sys.exit(1)


def main():
    check_ffmpeg()

    processes = []

    def cleanup(sig=None, frame=None):
        print("\n[INFO] Shutting down all services...")
        for name, proc in processes:
            if proc.poll() is None:
                print(f"  Stopping {name}...")
                proc.terminate()
        for name, proc in processes:
            proc.wait()
            print(f"  {name} stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("")
    print("=" * 60)
    print("  UDP → HLS TRANSCODER - STARTING ALL SERVICES")
    print("=" * 60)
    print("")

    python_exe = sys.executable

    # 1. Start UDP Stream Generator
    print("[1/3] Starting UDP Stream Generator...")
    p1 = subprocess.Popen(
        [python_exe, "start_udp_stream.py"],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
    )
    processes.append(("UDP Stream Generator", p1))
    time.sleep(3)  # Give it time to start

    # 2. Start HLS Transcoder
    print("[2/3] Starting HLS Transcoder...")
    p2 = subprocess.Popen(
        [python_exe, "start_hls_transcoder.py"],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
    )
    processes.append(("HLS Transcoder", p2))
    time.sleep(2)

    # 3. Start HTTP Server
    print("[3/3] Starting HTTP Server...")
    p3 = subprocess.Popen(
        [python_exe, "serve_hls.py"],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
    )
    processes.append(("HTTP Server", p3))
    time.sleep(1)

    print("")
    print("=" * 60)
    print("  ALL SERVICES RUNNING!")
    print("")
    print("  Web Player : http://localhost:8080/")
    print("  HLS Stream : http://localhost:8080/hls/stream.m3u8")
    print("  UDP Stream : udp://@239.0.0.1:5000 (for VLC)")
    print("")
    print("  Press Ctrl+C to stop all services.")
    print("=" * 60)
    print("")

    # Wait for any process to exit
    try:
        while True:
            for name, proc in processes:
                ret = proc.poll()
                if ret is not None:
                    print(f"\n[WARN] {name} exited with code {ret}")
                    cleanup()
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()