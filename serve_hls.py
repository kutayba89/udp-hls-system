"""
HLS HTTP Server
===============
Serves the HLS segments and playlist over HTTP with proper CORS headers.
Also serves the web-based video player.

Endpoints:
  http://localhost:8080/            → Web player (player/index.html)
  http://localhost:8080/hls/        → HLS playlist & segments

Press Ctrl+C to stop.
"""

import http.server
import os
import sys
from functools import partial
from config import HTTP_HOST, HTTP_PORT, HLS_OUTPUT_DIR


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with CORS support and proper MIME types for HLS."""

    # Custom MIME types
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".m3u8": "application/vnd.apple.mpegurl",
        ".ts": "video/mp2t",
        ".mp4": "video/mp4",
        ".html": "text/html",
        ".js": "application/javascript",
        ".css": "text/css",
        ".json": "application/json",
    }

    def end_headers(self):
        """Add CORS and cache-control headers."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

        # Prevent caching for HLS files (important for live streams)
        if self.path.endswith((".m3u8", ".ts")):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")

        super().end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.end_headers()

    def translate_path(self, path):
        """
        Route requests:
          /hls/*  → hls_output/ directory
          /*      → player/ directory (web player)
        """
        if path.startswith("/hls/"):
            # Serve HLS files from the output directory
            relative = path[5:]  # Remove '/hls/'
            return os.path.join(os.getcwd(), HLS_OUTPUT_DIR, relative)
        elif path == "/hls" or path == "/hls/":
            return os.path.join(os.getcwd(), HLS_OUTPUT_DIR, "")
        else:
            # Serve the web player
            if path == "/" or path == "":
                path = "/index.html"
            return os.path.join(os.getcwd(), "player", path.lstrip("/"))

    def log_message(self, format, *args):
        """Custom log format."""
        # Suppress noisy .ts segment requests, show everything else
        if ".ts" not in str(args[0]):
            super().log_message(format, *args)


def main():
    # Ensure directories exist
    if not os.path.exists(HLS_OUTPUT_DIR):
        os.makedirs(HLS_OUTPUT_DIR)
        print(f"[OK] Created {HLS_OUTPUT_DIR}/ directory")

    if not os.path.exists("player"):
        print("[ERROR] player/ directory not found!")
        print("  Make sure player/index.html exists.")
        sys.exit(1)

    server_address = (HTTP_HOST, HTTP_PORT)
    httpd = http.server.HTTPServer(server_address, CORSRequestHandler)

    print("")
    print("=" * 60)
    print("  HLS HTTP SERVER")
    print("=" * 60)
    print(f"  Web Player : http://localhost:{HTTP_PORT}/")
    print(f"  HLS Stream : http://localhost:{HTTP_PORT}/hls/stream.m3u8")
    print("")
    print(f"  Serving player from  : player/")
    print(f"  Serving HLS from     : {HLS_OUTPUT_DIR}/")
    print("")
    print("  Press Ctrl+C to stop.")
    print("=" * 60)
    print("")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down HTTP server...")
        httpd.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()