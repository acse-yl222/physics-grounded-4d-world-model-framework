"""Central configuration: every machine-specific path, every external service
endpoint and every model/provider choice the pipeline touches, resolved once
from the environment with sensible defaults.

Resolution order (highest first):

1. variables already present in the process environment (shell exports,
   CI secrets);
2. the repository's ``.env`` file (``IMG2CITY_ENV_FILE`` overrides the path),
   loaded by this module on import -- ``.env`` is git-ignored, copy
   ``.env.example`` to start;
3. the defaults in this file.

Nothing else in the package hard-codes a path, an endpoint or a model name:
switching the AI model or provider is a change to ``.env``, not to the code.
The model transports read API keys from ``os.environ`` at call time and
never store them.

Model strings may carry an explicit provider prefix, ``<provider>:<model>``
(for example ``claude-api:claude-sonnet-5``); a bare model name uses
``IMG2CITY_LLM_PROVIDER``.  See :mod:`img2city.agent.llm`.
"""
from __future__ import annotations
import os
import shutil
import sys
from pathlib import Path

# repository root = parent of the `img2city` package directory
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent


# ---- .env loading -----------------------------------------------------------
def parse_dotenv(text: str) -> dict[str, str]:
    """Parse ``KEY=value`` lines (``export KEY=value`` accepted; ``#``
    comments; single or double quotes stripped; blank lines ignored).
    Kept dependency-free on purpose: this file is imported by every stage
    subprocess."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if not key or not key.replace("_", "").isalnum():
            continue
        if val[:1] in ("\"", "'"):            # quoted: up to the closing quote
            end = val.find(val[0], 1)
            val = val[1:end] if end > 0 else val[1:]
        elif " #" in val:                      # trailing comment on an unquoted value
            val = val.split(" #", 1)[0].rstrip()
        values[key] = val
    return values


def load_dotenv(path: str | os.PathLike | None = None, *, override: bool = False) -> dict[str, str]:
    """Load ``path`` (default ``IMG2CITY_ENV_FILE`` or ``<repo>/.env``) into
    ``os.environ``.  Variables already set in the process win unless
    ``override``; empty values (``KEY=``) are skipped so an unset key never
    shadows a CLI login.  Returns the variables that were applied; a missing
    file is not an error (an empty dict)."""
    p = Path(path or os.environ.get("IMG2CITY_ENV_FILE") or PROJECT_ROOT / ".env").expanduser()
    if not p.is_file():
        return {}
    applied = {}
    for key, val in parse_dotenv(p.read_text(encoding="utf-8")).items():
        if val == "":                          # `KEY=` in .env means "not configured"
            continue
        if override or not os.environ.get(key):
            os.environ[key] = val
            applied[key] = val
    return applied


ENV_FILE = Path(os.environ.get("IMG2CITY_ENV_FILE") or PROJECT_ROOT / ".env").expanduser()
load_dotenv(ENV_FILE)


def _env(*names: str, default: str | None = None) -> str | None:
    """First non-empty environment variable among ``names`` (later names are
    deprecated spellings kept for compatibility), else ``default``."""
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return default


def _env_list(name: str, default: str) -> list[str]:
    return [s.strip() for s in (_env(name, default=default) or "").split(",") if s.strip()]


def _env_bool(name: str, default: bool = False) -> bool:
    v = _env(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


# ---- where generated areas / runs / model weights live ----------------------
DATA_DIR = Path(_env("IMG2CITY_DATA_DIR", default=str(PROJECT_ROOT / "data"))).expanduser()
RUNS_DIR = Path(_env("IMG2CITY_RUNS_DIR", default=str(PROJECT_ROOT / "runs"))).expanduser()
CACHE_DIR = Path(_env("IMG2CITY_CACHE_DIR", default=str(PROJECT_ROOT / ".cache"))).expanduser()
# learned prior: synthetic dataset + trained weights (large; git-ignored)
PRIOR_DIR = Path(_env("IMG2CITY_PRIOR_DIR", default=str(DATA_DIR / "prior"))).expanduser()
# one JSON receipt per model call (prompt, output, usage, image hashes)
MODEL_LOG_DIR = Path(_env("IMG2CITY_MODEL_LOG_DIR", default=str(RUNS_DIR / "model_calls"))).expanduser()

# ---- external programs -----------------------------------------------------
_DEFAULT_BLENDER = (
    "/Applications/Blender.app/Contents/MacOS/Blender" if sys.platform == "darwin"
    else (shutil.which("blender") or "blender"))
BLENDER_BIN = _env("IMG2CITY_BLENDER", default=_DEFAULT_BLENDER)

# python interpreter that has torch/transformers/deepforest (vehicle + tree
# detection).  Defaults to the current interpreter; point it at a separate
# conda env when the heavy ML stack lives elsewhere.
TORCH_PYTHON = _env("IMG2CITY_TORCH_PYTHON", default=sys.executable)

# BlenderMCP addon socket (live Blender)
MCP_HOST = _env("IMG2CITY_MCP_HOST", default="localhost")
MCP_PORT = int(_env("IMG2CITY_MCP_PORT", default="9876"))

# ---- LLM agents: provider + one model per role -------------------------------
# provider = how a model is reached (see img2city.agent.llm):
#   codex       OpenAI models through the local Codex CLI (ChatGPT subscription)
#   openai      OpenAI Responses API (OPENAI_API_KEY, pay-as-you-go)
#   claude-sdk  Claude through the Claude Agent SDK / Claude Code CLI login
#   claude-api  Anthropic Messages API (ANTHROPIC_API_KEY, pay-as-you-go)
LLM_PROVIDERS = ("codex", "openai", "claude-sdk", "claude-api")
LLM_PROVIDER = _env("IMG2CITY_LLM_PROVIDER", "IMG2CITY_ASTRA_BACKEND", default="codex")
DEFAULT_MODEL = _env("IMG2CITY_MODEL", default="gpt-6-astra")
VISION_MODEL = _env("IMG2CITY_VISION_MODEL", default=DEFAULT_MODEL)       # look at photos, pick views/cards
SPEC_MODEL = _env("IMG2CITY_SPEC_MODEL", default=DEFAULT_MODEL)           # write / repair / refine specs
JUDGE_MODEL = _env("IMG2CITY_JUDGE_MODEL", default=DEFAULT_MODEL)         # checklist + pairwise judging
LEARNING_MODEL = _env("IMG2CITY_LEARNING_MODEL", default=DEFAULT_MODEL)   # author new kit parts
PHOTO_CARD_MODEL = _env("IMG2CITY_PHOTO_CARD_MODEL", "PHOTO_CARD_MODEL", default=VISION_MODEL)
PHOTO_SPEC_MODEL = _env("IMG2CITY_PHOTO_SPEC_MODEL", "PHOTO_SPEC_MODEL", default=SPEC_MODEL)
LLM_REASONING = _env("IMG2CITY_LLM_REASONING", "IMG2CITY_ASTRA_REASONING", default="high")
LLM_TIMEOUT = float(_env("IMG2CITY_LLM_TIMEOUT", "IMG2CITY_ASTRA_TIMEOUT", default="600"))

# provider endpoints / binaries (keys: OPENAI_API_KEY, ANTHROPIC_API_KEY,
# GEMINI_API_KEY, GOOGLE_MAPS_API_KEY -- read from os.environ at call time)
OPENAI_BASE_URL = (_env("OPENAI_BASE_URL", default="https://api.openai.com/v1") or "").rstrip("/")
ANTHROPIC_BASE_URL = _env("ANTHROPIC_BASE_URL")          # None = the SDK's default endpoint
CODEX_BIN = _env("IMG2CITY_CODEX", default=shutil.which("codex") or (
    "/Applications/Codex.app/Contents/Resources/codex" if sys.platform == "darwin" else "codex"))
CLAUDE_CLI = _env("IMG2CITY_CLAUDE_CLI", default=shutil.which("claude") or "claude")

# image-editing models for facade cleaning / synthetic views, tried in order.
# Each entry is <provider>:<model> with provider in {openai, gemini}.
IMAGE_EDIT_MODELS = _env_list(
    "IMG2CITY_IMAGE_EDIT_MODELS",
    "openai:gpt-image-2,gemini:gemini-3.1-flash-image,gemini:gemini-2.5-flash-image")

# ---- external data services ------------------------------------------------
OVERPASS_URLS = _env_list(
    "IMG2CITY_OVERPASS_URLS",
    "https://overpass-api.de/api/interpreter,https://overpass.kumi.systems/api/interpreter")

# ---- experiment switches -----------------------------------------------------
# inject a typology exemplar into the one-shot spec prompt (08-12 A/B: no gain)
ONESHOT_EXEMPLAR = _env_bool("IMG2CITY_ONESHOT_EXEMPLAR") or bool(_env("ONESHOT_EXEMPLAR"))


def module_cmd(module: str, *args: str, python: str | None = None) -> list[str]:
    """Command line that runs an img2city module as a stage subprocess
    (``python -m img2city.<module> ...``).  Every orchestrator (make_city,
    the web app, batch drivers) goes through this so the package never has
    to be on the cwd path."""
    return [python or sys.executable, "-m", f"img2city.{module}", *args]


def subprocess_env(extra: dict | None = None) -> dict:
    """Environment for stage subprocesses: PROJECT_ROOT on PYTHONPATH so the
    package resolves even when it is not pip-installed.  Values loaded from
    ``.env`` are already in ``os.environ`` and therefore inherited."""
    env = dict(os.environ)
    pp = env.get("PYTHONPATH", "")
    root = str(PROJECT_ROOT)
    if root not in pp.split(os.pathsep):
        env["PYTHONPATH"] = root + (os.pathsep + pp if pp else "")
    if extra:
        env.update(extra)
    return env
