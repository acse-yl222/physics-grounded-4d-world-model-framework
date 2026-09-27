"""Local-only standalone demonstration launcher; Python standard library only."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import subprocess
import threading
import webbrowser

ROOT = Path(__file__).resolve().parent
handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
server = None
for port in range(8768, 8779):
    try:
        server = ThreadingHTTPServer(('127.0.0.1', port), handler)
        break
    except OSError:
        continue
if server is None:
    raise SystemExit('No free local demo port in 8768–8778.')
url = f'http://127.0.0.1:{server.server_port}/'
print(f'FieldFleet demonstration: {url}\nKeep this terminal open. Press Ctrl+C to stop.', flush=True)


def open_browser():
    if Path('/Applications/Google Chrome.app').exists():
        subprocess.run(['open', '-a', 'Google Chrome', url], check=False)
    else:
        webbrowser.open(url)


threading.Timer(.5, open_browser).start()
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
