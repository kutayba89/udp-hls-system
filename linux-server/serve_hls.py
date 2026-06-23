"""
╔══════════════════════════════════════════════════════════════╗
║              HLS HTTP Server — Linux Production              ║
╚══════════════════════════════════════════════════════════════╝

Serves:
  /                         → Web player  (player/index.html)
  /hls/{name}/stream.m3u8   → HLS playlist for each stream
  /hls/{name}/seg_XXXXX.ts  → HLS segments
  /api/streams              → JSON list of all streams + status

Usage:
  python3 serve_hls.py
"""

import http.server
import os
import sys
import json
import threading
from config_csv import HTTP_HOST, HTTP_PORT, HLS_BASE_DIR, STREAMS, SERVER_IP


class HLSRequestHandler(http.server.BaseHTTPRequestHandler):

    # ── MIME types ──────────────────────────────────────────────────
    MIME = {
        ".m3u8": "application/vnd.apple.mpegurl",
        ".ts":   "video/mp2t",
        ".html": "text/html; charset=utf-8",
        ".js":   "application/javascript",
        ".css":  "text/css",
        ".json": "application/json",
        ".ico":  "image/x-icon",
    }

    def do_GET(self):
        path = self.path.split("?")[0]  # strip query string

        if path == "/" or path == "/index.html":
            self._serve_file(os.path.join(os.path.dirname(__file__), "player", "index.html"))

        elif path == "/api/streams":
            self._serve_streams_api()

        elif path.startswith("/hls/"):
            self._serve_hls(path)

        elif path.startswith("/player/"):
            self._serve_file(os.path.join(os.path.dirname(__file__), path.lstrip("/")))

        else:
            self._send_404()

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    # ── Route: HLS files ────────────────────────────────────────────
    def _serve_hls(self, path):
        # path = /hls/{name}/{filename}
        parts = path.strip("/").split("/")   # ["hls", "ch01", "stream.m3u8"]
        if len(parts) < 3:
            self._send_404()
            return

        stream_name = parts[1]
        filename    = "/".join(parts[2:])
        filepath    = os.path.join(HLS_BASE_DIR, stream_name, filename)

        self._serve_file(filepath, no_cache=True)

    # ── Route: streams API ──────────────────────────────────────────
    def _serve_streams_api(self):
        data = []
        for s in STREAMS:
            name     = s["name"]
            out_dir  = os.path.join(HLS_BASE_DIR, name)
            playlist = os.path.join(out_dir, "stream.m3u8")
            ready    = os.path.exists(playlist)

            data.append({
                "name":       name,
                "label":      s["label"],
                "source_ip":  s.get("source_ip", ""),
                "group":      s.get("group", ""),
                "port":       s["port"],
                "service_id":  s.get("service_id", ""),
                "on_id":       s.get("on_id", ""),
                "ts_id":       s.get("ts_id", ""),
                "video_codec": s.get("video_codec", ""),
                "audio_codec": s.get("audio_codec", ""),
                "ready":       ready,
                "hls_url":    f"http://{SERVER_IP}:{HTTP_PORT}/hls/{name}/stream.m3u8",
                "segments":   len([f for f in os.listdir(out_dir) if f.endswith(".ts")]) if os.path.isdir(out_dir) else 0,
            })

        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(200)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ── Serve a file from disk ───────────────────────────────────────
    def _serve_file(self, filepath, no_cache=False):
        if not os.path.isfile(filepath):
            self._send_404(filepath)
            return

        ext      = os.path.splitext(filepath)[1].lower()
        mimetype = self.MIME.get(ext, "application/octet-stream")

        try:
            with open(filepath, "rb") as f:
                data = f.read()

            self.send_response(200)
            self._cors_headers()
            self.send_header("Content-Type", mimetype)
            self.send_header("Content-Length", str(len(data)))
            if no_cache:
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(data)

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())

    def _send_404(self, path=""):
        body = f"404 Not Found: {path}".encode()
        self.send_response(404)
        self._cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def log_message(self, fmt, *args):
        # Suppress .ts segment noise, log everything else
        msg = fmt % args
        if ".ts" not in msg:
            print(f"  [HTTP] {self.address_string()} — {msg}")


def main():
    if not os.path.isdir(os.path.join(os.path.dirname(__file__), "player")):
        print("[ERROR] player/ directory not found next to serve_hls.py")
        sys.exit(1)

    os.makedirs(HLS_BASE_DIR, exist_ok=True)

    server = http.server.ThreadingHTTPServer((HTTP_HOST, HTTP_PORT), HLSRequestHandler)

    print("")
    print("=" * 60)
    print("  HLS HTTP SERVER — Linux Production")
    print("=" * 60)
    print(f"  Web Player  :  http://{SERVER_IP}:{HTTP_PORT}/")
    print(f"  Streams API :  http://{SERVER_IP}:{HTTP_PORT}/api/streams")
    print(f"  HLS example :  http://{SERVER_IP}:{HTTP_PORT}/hls/ch01/stream.m3u8")
    print(f"  Serving HLS from : {HLS_BASE_DIR}")
    print("=" * 60 + "\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] HTTP server stopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
