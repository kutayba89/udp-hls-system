"""
╔══════════════════════════════════════════════════════════════╗
║           UDP → HLS Multi-Stream Transcoder Manager          ║
║                    Linux Production Version                  ║
╚══════════════════════════════════════════════════════════════╝

Manages multiple FFmpeg processes — one per UDP multicast stream.
Each stream gets:
  - Its own HLS output directory
  - Its own playlist (stream.m3u8)
  - Auto-restart on crash
  - Per-stream log file

Usage:
  python3 transcoder.py                  # Start all streams from config
  python3 transcoder.py --streams ch01 ch02  # Start specific streams only
  python3 transcoder.py --list           # List all configured streams
"""

import subprocess
import os
import sys
import signal
import time
import argparse
import threading
import logging
from datetime import datetime
from config_csv import (
    MULTICAST_GROUP,
    MULTICAST_INTERFACE,
    STREAMS,
    USE_SOURCE_FILTER,
    VIDEO_CODEC,
    AUDIO_CODEC,
    VIDEO_BITRATE,
    AUDIO_BITRATE,
    AUDIO_SAMPLE_RATE,
    HLS_BASE_DIR,
    HLS_SEGMENT_SECONDS,
    HLS_PLAYLIST_SIZE,
    HLS_SEGMENT_PATTERN,
    LOG_DIR,
    FFMPEG_RESTART_DELAY,
    MAX_RESTART_ATTEMPTS,
)


# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("transcoder")


# ─── Global process registry ──────────────────────────────────────────────────
_workers = {}       # name → WorkerThread
_shutdown = threading.Event()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def build_ffmpeg_cmd(stream: dict) -> list:
    """
    Build the FFmpeg command for a single UDP multicast → HLS stream.

    Input URL format:
      udp://@{multicast_group}:{port}?localaddr={server_ip}&fifo_size=...

    The 'localaddr' parameter tells FFmpeg which interface to join the
    multicast group on — critical on multi-homed Linux servers.
    """
    name        = stream["name"]
    port        = stream["port"]
    group       = stream.get("group") or MULTICAST_GROUP
    source_ip   = stream.get("source_ip", "")
    video_codec = stream.get("video_codec") or VIDEO_CODEC
    audio_codec = stream.get("audio_codec") or AUDIO_CODEC
    program_id  = stream.get("program_id") or stream.get("service_id") or ""
    input_type  = (stream.get("input_type") or "spts").lower()

    out_dir      = os.path.join(HLS_BASE_DIR, name)
    playlist     = os.path.join(out_dir, "stream.m3u8")
    seg_pattern  = os.path.join(out_dir, HLS_SEGMENT_PATTERN)

    ensure_dir(out_dir)

    # UDP multicast input with interface binding.
    # localaddr is the LOCAL NIC IP. sources filters by sender IP when enabled.
    udp_url = (
        f"udp://@{group}:{port}"
        f"?localaddr={MULTICAST_INTERFACE}"
        f"&overrun_nonfatal=1"
        f"&fifo_size=50000000"
        f"&buffer_size=65536"
    )
    if USE_SOURCE_FILTER and source_ip:
        udp_url += f"&sources={source_ip}"

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "warning",          # Only show warnings and errors
        "-y",

        # ── Input ──────────────────────────────────────────────────
        "-fflags",    "+genpts+discardcorrupt",
        "-re",
        "-i",         udp_url,
    ]

    # ── Stream mapping ─────────────────────────────────────────────
    # SPTS: map first video and optional first audio.
    # MPTS: map the configured DVB/MPEG-TS service/program ID.
    if input_type == "mpts" and program_id:
        cmd += ["-map", f"p:{program_id}"]
    else:
        cmd += ["-map", "0:v:0", "-map", "0:a:0?"]

    # Drop subtitles/data PIDs from HLS output.
    cmd += [
        "-sn",
        "-dn",

        # ── Video ──────────────────────────────────────────────────
        "-c:v",       video_codec,
    ]

    # Only add encoding params if we're re-encoding
    if video_codec != "copy":
        cmd += [
            "-preset",    "veryfast",
            "-tune",      "zerolatency",
            "-b:v",       VIDEO_BITRATE,
            "-maxrate",   VIDEO_BITRATE,
            "-bufsize",   "5000k",
            "-pix_fmt",   "yuv420p",
            "-g",         "60",
            "-sc_threshold", "0",
            "-force_key_frames", f"expr:gte(t,n_forced*{HLS_SEGMENT_SECONDS})",
        ]

    # ── Audio ──────────────────────────────────────────────────────
    cmd += ["-c:a", audio_codec]
    if audio_codec != "copy":
        cmd += [
            "-b:a", AUDIO_BITRATE,
            "-ar",  str(AUDIO_SAMPLE_RATE),
            "-ac",  "2",
        ]

    # ── HLS Output ─────────────────────────────────────────────────
    cmd += [
        "-f",                    "hls",
        "-hls_time",             str(HLS_SEGMENT_SECONDS),
        "-hls_list_size",        str(HLS_PLAYLIST_SIZE),
        "-hls_flags",            "delete_segments+append_list+independent_segments",
        "-hls_segment_type",     "mpegts",
        "-hls_segment_filename", seg_pattern,
        "-hls_allow_cache",      "0",
        playlist,
    ]

    return cmd


# ─── Worker Thread ────────────────────────────────────────────────────────────

class StreamWorker(threading.Thread):
    """
    Runs FFmpeg for one stream in a dedicated thread.
    Automatically restarts if FFmpeg crashes.
    """

    def __init__(self, stream: dict):
        super().__init__(daemon=True)
        self.stream   = stream
        self.name     = stream["name"]
        self.label    = stream["label"]
        self.port     = stream["port"]
        self.process  = None
        self.restarts = 0
        self.running  = True
        self.status   = "starting"

        # Per-stream log file
        ensure_dir(LOG_DIR)
        log_path = os.path.join(LOG_DIR, f"{self.name}.log")
        self.logfile = open(log_path, "a", buffering=1)
        self.logfile.write(
            f"\n{'='*60}\n"
            f"  Stream: {self.label}  |  Port: {self.port}\n"
            f"  Started: {datetime.now().isoformat()}\n"
            f"{'='*60}\n"
        )

    def run(self):
        while self.running and not _shutdown.is_set():
            if MAX_RESTART_ATTEMPTS > 0 and self.restarts >= MAX_RESTART_ATTEMPTS:
                log.error(f"[{self.name}] Reached max restart attempts ({MAX_RESTART_ATTEMPTS}). Giving up.")
                self.status = "failed"
                return

            cmd = build_ffmpeg_cmd(self.stream)

            if self.restarts == 0:
                log.info(f"[{self.name}] ▶  Starting  port={self.port}  ({self.label})")
            else:
                log.warning(f"[{self.name}] ↻  Restart #{self.restarts}  port={self.port}")

            self.logfile.write(f"[{datetime.now().isoformat()}] CMD: {' '.join(cmd)}\n")
            self.logfile.flush()

            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=self.logfile,
                    stderr=self.logfile,
                )
                self.status = "running"
                self.process.wait()
                ret = self.process.returncode

            except FileNotFoundError:
                log.error("FFmpeg not found! Install with: sudo apt install ffmpeg")
                self.status = "failed"
                return
            except Exception as e:
                log.error(f"[{self.name}] Exception: {e}")
                ret = -1

            if _shutdown.is_set() or not self.running:
                break

            log.warning(f"[{self.name}] FFmpeg exited (code={ret}). Restarting in {FFMPEG_RESTART_DELAY}s...")
            self.status = "restarting"
            self.restarts += 1
            time.sleep(FFMPEG_RESTART_DELAY)

        self.status = "stopped"
        self.logfile.close()

    def stop(self):
        self.running = False
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


# ─── Status Monitor ───────────────────────────────────────────────────────────

def status_monitor():
    """Prints a status table every 30 seconds."""
    while not _shutdown.is_set():
        time.sleep(30)
        if _shutdown.is_set():
            break

        print("\n" + "─" * 60)
        print(f"  STREAM STATUS  —  {datetime.now().strftime('%H:%M:%S')}")
        print("─" * 60)
        print(f"  {'NAME':<8} {'PORT':<7} {'STATUS':<12} {'RESTARTS':<10} LABEL")
        print("─" * 60)
        for name, worker in sorted(_workers.items()):
            status_icon = {
                "running":    "✅",
                "restarting": "⚠️ ",
                "failed":     "❌",
                "stopped":    "⏹ ",
                "starting":   "⏳",
            }.get(worker.status, "?")
            print(f"  {name:<8} {worker.port:<7} {status_icon} {worker.status:<10} {worker.restarts:<8} {worker.label}")
        print("─" * 60 + "\n")


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="UDP → HLS Multi-Stream Transcoder"
    )
    parser.add_argument(
        "--streams", nargs="+", metavar="NAME",
        help="Only start specific streams by name (e.g. --streams ch01 ch02)"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all configured streams and exit"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # ── List mode ──────────────────────────────────────────────────
    if args.list:
        print(f"\n{'NAME':<8} {'PORT':<7} LABEL")
        print("─" * 50)
        for s in STREAMS:
            print(f"{s['name']:<8} {s['port']:<7} {s['label']}")
        print(f"\nTotal: {len(STREAMS)} streams")
        return

    # ── Filter streams ─────────────────────────────────────────────
    streams_to_run = STREAMS
    if args.streams:
        names = set(args.streams)
        streams_to_run = [s for s in STREAMS if s["name"] in names]
        if not streams_to_run:
            log.error(f"No matching streams found for: {args.streams}")
            sys.exit(1)

    # ── Startup banner ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  UDP → HLS MULTI-STREAM TRANSCODER")
    print("  Linux Production Server")
    print("=" * 60)
    print(f"  Default group    : {MULTICAST_GROUP}")
    print(f"  Interface        : {MULTICAST_INTERFACE}")
    print(f"  HLS output dir   : {HLS_BASE_DIR}")
    print(f"  Streams to start : {len(streams_to_run)}")
    print(f"  Video codec      : {VIDEO_CODEC}")
    print(f"  Audio codec      : {AUDIO_CODEC}")
    print(f"  Segment length   : {HLS_SEGMENT_SECONDS}s")
    print(f"  Playlist window  : {HLS_PLAYLIST_SIZE} segments")
    print("=" * 60 + "\n")

    # ── Signal handling ────────────────────────────────────────────
    def shutdown(sig, frame):
        print("\n\n[INFO] Shutdown signal received. Stopping all streams...")
        _shutdown.set()
        for worker in _workers.values():
            worker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── Ensure base dirs exist ─────────────────────────────────────
    ensure_dir(HLS_BASE_DIR)
    ensure_dir(LOG_DIR)

    # ── Launch workers ─────────────────────────────────────────────
    for stream in streams_to_run:
        worker = StreamWorker(stream)
        _workers[stream["name"]] = worker
        worker.start()
        time.sleep(0.3)   # Small stagger to avoid thundering herd

    log.info(f"All {len(_workers)} stream workers launched.")
    log.info(f"HLS streams available at: http://192.168.90.116:8090/hls/{{name}}/stream.m3u8")
    log.info(f"Web player at:            http://192.168.90.116:8090/")
    log.info("Press Ctrl+C to stop all streams.\n")

    # ── Start status monitor ───────────────────────────────────────
    monitor = threading.Thread(target=status_monitor, daemon=True)
    monitor.start()

    # ── Keep main thread alive ─────────────────────────────────────
    try:
        while not _shutdown.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
