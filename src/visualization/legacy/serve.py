#!/usr/bin/env python3
"""Static file server with HTTP Range support for the field visualiser.

The web page reads individual frames straight out of the .npy files in
scenes/<id>/physics/ using Range requests, so no preprocessing (and no numpy)
is needed. ?scene=<id> picks the scene (scenes/index.json). Run:

    python3 serve.py                      # http://localhost:8787/viewer/3d/ (next free port if busy), opens a browser
    python3 serve.py 9000                 # custom port
    python3 serve.py 8787 --host 0.0.0.0 --no-browser   # workstation: listen on all interfaces
"""
import os
import sys
import re
import webbrowser
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


class RangeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):  # keep the terminal quiet
        if "206" not in fmt % args:
            super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        # big immutable assets may be cached by browsers; page code always revalidates
        big = self.path.endswith((".glb", ".npy", ".f32", ".jsonl", ".png", ".gif"))
        self.send_header("Cache-Control", "public, max-age=86400" if big else "no-cache")
        super().end_headers()

    def do_GET(self):
        # old links: the page lived at /web/3d/ until the 2026-09-14 restructure
        if self.path == "/" or self.path.startswith("/web/"):
            self.send_response(302); self.send_header("Location", "/viewer/3d/" + (self.path.split("?", 1)[1:] and "?" + self.path.split("?", 1)[1] or "")); self.end_headers(); return
        rng = self.headers.get("Range")
        if not rng:
            return super().do_GET()
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().do_GET()
        m = RANGE_RE.match(rng)
        if not m:
            return super().do_GET()
        size = os.path.getsize(path)
        start, end = m.group(1), m.group(2)
        if start == "":
            length = int(end)
            start, end = max(0, size - length), size - 1
        else:
            start = int(start)
            end = int(end) if end else size - 1
        end = min(end, size - 1)
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return
        length = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(1 << 20, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    port = int(args[0]) if args else 8787
    host = "127.0.0.1"
    for f in flags:
        if f.startswith("--host="):
            host = f.split("=", 1)[1]
    if "--host" in flags:
        host = args[1] if len(args) > 1 else "0.0.0.0"
    server = None
    for candidate in range(port, port + 20):
        try:
            server = ThreadingHTTPServer((host, candidate), RangeHandler)
            port = candidate
            break
        except OSError:
            continue
    if server is None:
        sys.exit(f"No free port in {port}-{port + 19}")
    url = f"http://localhost:{port}/viewer/3d/"
    print(f"Serving {ROOT} on {host}:{port}\nOpen {url}  (Ctrl+C to stop)", flush=True)
    if "--no-browser" not in flags:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
