"""`img2city doctor` -- what is installed, present, and reachable on this machine.

Read-only.  Prints one line per item so a fresh clone can see at a glance which
stages will run: python stacks, external programs, the LLM provider/model
configuration, API keys, and the large
git-ignored assets (generated areas, learned-prior weights, DreamSim cache)
that have to be copied or produced locally.  Exit code 0 always; the report is
the product.

    img2city doctor
"""
from __future__ import annotations
import importlib
import os
import shutil
import socket
import sys

from img2city import config


def _ok(flag: bool, warn: bool = False) -> str:
    return "ok  " if flag else ("warn" if warn else "MISS")


def _pkg(name: str) -> tuple[bool, str]:
    try:
        m = importlib.import_module(name)
        return True, getattr(m, "__version__", "") or ""
    except Exception as e:                       # noqa: BLE001 -- report, never raise
        return False, type(e).__name__


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _dir_size(path) -> str:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return f"{total / 1e9:.1f} GB" if total > 1e9 else f"{total / 1e6:.0f} MB"


def report() -> list[tuple[str, str, str]]:
    """[(status, item, detail)]; status in {'ok  ', 'warn', 'MISS'}."""
    rows: list[tuple[str, str, str]] = []
    add = rows.append

    # ---- python stacks -----------------------------------------------------
    add(("ok  ", "python", f"{sys.version.split()[0]}  {sys.executable}"))
    groups = {
        "core":   ["numpy", "PIL", "shapely", "scipy", "pyproj", "requests", "matplotlib"],
        "claude-sdk": ["claude_agent_sdk", "anyio"],
        "claude-api": ["anthropic"],
        "web":    ["fastapi", "uvicorn", "multipart"],
        "ml":     ["torch", "torchvision", "transformers", "dreamsim", "peft", "deepforest"],
        "gemini": ["google.genai"],
        "dev":    ["pytest", "httpx"],
    }
    for grp, mods in groups.items():
        missing = [m for m in mods if not _pkg(m)[0]]
        detail = "all present" if not missing else "missing: " + ", ".join(missing)
        add((_ok(not missing, warn=grp in ("claude-sdk", "claude-api", "ml", "gemini")), f"deps[{grp}]", detail))

    # ---- external programs ---------------------------------------------------
    blender = config.BLENDER_BIN
    add((_ok(os.path.exists(blender) or bool(shutil.which(blender))),
         "blender (headless)", blender))
    add((_ok(_port_open(config.MCP_HOST, config.MCP_PORT), warn=True),
         "blender-mcp socket", f"{config.MCP_HOST}:{config.MCP_PORT}  "
         "(open Blender + the BlenderMCP addon for live stages)"))
    torch_py = config.TORCH_PYTHON
    add((_ok(os.path.exists(torch_py), warn=True), "torch interpreter", torch_py))
    # ---- LLM provider + models (from .env / environment) --------------------
    provider = config.LLM_PROVIDER
    codex_ok = os.path.isfile(config.CODEX_BIN) or bool(shutil.which(config.CODEX_BIN))
    claude_ok = os.path.isfile(config.CLAUDE_CLI) or bool(shutil.which(config.CLAUDE_CLI))
    ready = {"codex": codex_ok, "claude-sdk": claude_ok,
             "openai": bool(os.environ.get("OPENAI_API_KEY")),
             "claude-api": bool(os.environ.get("ANTHROPIC_API_KEY"))}
    needs = {"codex": f"codex CLI at {config.CODEX_BIN}", "claude-sdk": f"claude CLI at {config.CLAUDE_CLI}",
             "openai": "OPENAI_API_KEY", "claude-api": "ANTHROPIC_API_KEY"}
    add((_ok(ready.get(provider, False)), "llm provider",
         f"{provider} (IMG2CITY_LLM_PROVIDER); needs {needs.get(provider, '?')} "
         "-- configuration check only, authentication needs a live call"))
    add(("ok  ", "llm models",
         f"vision={config.VISION_MODEL} spec={config.SPEC_MODEL} judge={config.JUDGE_MODEL} "
         f"learning={config.LEARNING_MODEL} reasoning={config.LLM_REASONING} "
         f"timeout={config.LLM_TIMEOUT:.0f}s"))
    add(("ok  ", "llm endpoints",
         f"openai={config.OPENAI_BASE_URL} anthropic={config.ANTHROPIC_BASE_URL or 'default'}"))
    add((_ok(config.ENV_FILE.is_file(), warn=True), ".env file",
         f"{config.ENV_FILE}" + ("" if config.ENV_FILE.is_file() else
                                 "  -- copy .env.example to .env to configure keys/models")))
    add((_ok(claude_ok, warn=True), "claude CLI",
         config.CLAUDE_CLI if claude_ok else f"{config.CLAUDE_CLI} not found (needed by claude-sdk)"))
    add((_ok(codex_ok, warn=True), "codex CLI",
         config.CODEX_BIN if codex_ok else f"{config.CODEX_BIN} not found (needed by codex)"))
    add(("ok  ", "image-edit models", ", ".join(config.IMAGE_EDIT_MODELS)))

    # ---- keys ------------------------------------------------------------------
    for key, why, warn in (("GOOGLE_MAPS_API_KEY", "imagery, geocoding, Places", False),
                           ("OPENAI_API_KEY", "provider openai; openai:* image edits", True),
                           ("ANTHROPIC_API_KEY", "provider claude-api only (unset for claude-sdk)", True),
                           ("GEMINI_API_KEY", "gemini:* image edits (synth-views / facade-clean)", True)):
        add((_ok(bool(os.environ.get(key)), warn=warn), key, why))

    # ---- assets (git-ignored, must exist locally) ------------------------------
    d = config.DATA_DIR
    areas = []
    if d.is_dir():
        for p in sorted(d.iterdir()):
            if p.is_dir() and (p / "buildings.json").exists():
                blend = any(p.glob("*.blend"))
                areas.append(f"{p.name}{'' if blend else ' (no .blend)'}")
    add((_ok(bool(areas), warn=True), "areas in DATA_DIR",
         f"{d}: " + (", ".join(areas) if areas else "none (run make-city or copy one in)")))
    prior = config.PRIOR_DIR / "param_model.pt"
    add((_ok(prior.exists(), warn=True), "prior weights",
         f"{prior}" + ("" if prior.exists() else
                       "  -- photo->model needs it: `img2city prior-train` or copy from another machine")))
    ds = config.CACHE_DIR / "dreamsim"
    add((_ok(ds.is_dir() and any(ds.iterdir()), warn=True), "dreamsim cache",
         f"{ds} ({_dir_size(ds)})" if ds.is_dir() else
         f"{ds}  -- downloads (~3 GB) on first perceptual-judge call"))
    return rows


def main() -> int:
    import argparse
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    rows = report()
    w = max(len(r[1]) for r in rows)
    for status, item, detail in rows:
        print(f"[{status}] {item:<{w}}  {detail}")
    miss = sum(1 for r in rows if r[0] == "MISS")
    warn = sum(1 for r in rows if r[0] == "warn")
    print(f"\n{miss} missing, {warn} optional/absent. "
          "MISS blocks the core pipeline; warn disables one optional stage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
