"""Run the synthetic viewer smoke test through the installed framework CLI."""

from contextlib import contextmanager
import os
from pathlib import Path
from queue import Queue, Empty
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]


def chrome_path():
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
    return chrome


@contextmanager
def viewer_server(workspace, output):
    """Wait for CLI readiness, capture its log, and always stop the child process."""
    output.mkdir(parents=True, exist_ok=True)
    ready = Queue()
    env = dict(os.environ)
    for name in ("PYTHONPATH", "P4D_ROOT", "UWM_ROOT"):
        env.pop(name, None)
    with (output / "server.log").open("w") as log:
        server = subprocess.Popen(
            [sys.executable, "-m", "common.cli", "--root", str(workspace), "serve", "--port", "0"],
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )

        def read_output():
            for line in server.stdout:
                log.write(line)
                log.flush()
                if line.startswith("Viewer: "):
                    ready.put(line.removeprefix("Viewer: ").strip())
            ready.put(None)

        thread = threading.Thread(target=read_output, daemon=True)
        thread.start()
        try:
            try:
                url = ready.get(timeout=30)
            except Empty:
                raise RuntimeError(
                    f"Viewer startup timed out; see {output / 'server.log'}"
                ) from None
            if url is None:
                raise RuntimeError(f"Viewer exited before startup; see {output / 'server.log'}")
            yield url
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
            thread.join(timeout=5)
            server.stdout.close()


def main():
    output = ROOT / "cache/framework/browser"
    chrome = chrome_path()
    with tempfile.TemporaryDirectory() as workspace, viewer_server(Path(workspace), output) as url:
        env = {
            **os.environ,
            "CHROME_PATH": chrome,
            "UWM_BROWSER_OUTPUT": str(output),
            "UWM_VIEWER_URL": (
                url + "src/visualization/viewer/?manifest=/examples/contract-v1/manifest.json"
            ),
        }
        subprocess.run(
            ["node", "tests/browser_contract.cjs"], cwd=ROOT, env=env, check=True, timeout=120
        )


if __name__ == "__main__":
    main()
