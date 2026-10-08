"""Run the synthetic viewer smoke test with a temporary local HTTP server."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import subprocess
import threading

ROOT = Path(__file__).resolve().parents[1]


def main():
    chrome = os.environ.get("CHROME_PATH")
    if not chrome:
        chrome = subprocess.check_output(
            [
                "node",
                "--input-type=module",
                "-e",
                "import p from 'puppeteer'; console.log(await p.executablePath());",
            ],
            cwd=ROOT,
            text=True,
        ).strip()
    if not Path(chrome).is_file():
        raise SystemExit("Chrome is missing. Run npx puppeteer browsers install chrome first.")
    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    env = {
        **os.environ,
        "CHROME_PATH": chrome,
        "UWM_VIEWER_URL": (
            f"http://127.0.0.1:{server.server_port}/src/visualization/viewer/"
            "?manifest=../../../examples/contract-v1/manifest.json"
        ),
    }
    try:
        subprocess.run(
            ["node", "tests/browser_contract.cjs"], cwd=ROOT, env=env, check=True, timeout=120
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
