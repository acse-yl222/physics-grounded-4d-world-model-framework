"""Nothing secret reaches git: `.env` stays ignored, the committed template
carries no values, and no tracked text file contains a key-shaped string.
Runs in `make test` and in CI on every push."""
import re
import subprocess

import pytest

from img2city import config

ROOT = config.PROJECT_ROOT
SECRET_VARS = ("GOOGLE_MAPS_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")
# Google (AIza...), OpenAI (sk-..., sk-proj-...), Anthropic (sk-ant-...), GitHub tokens
KEY_SHAPES = re.compile(r"AIza[0-9A-Za-z_\-]{30,}|sk-(?:ant-|proj-)?[0-9A-Za-z_\-]{30,}|gh[pousr]_[0-9A-Za-z]{30,}")
TEXT_SUFFIXES = {".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".sh", ".js", ".html", ".css", ".example", ""}


def _git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("git not available")
    if r.returncode not in (0, 1):
        pytest.skip(f"not a git checkout: {r.stderr.strip()[:80]}")
    return r


def test_env_file_is_git_ignored():
    for name in (".env", ".env.local", ".env.production"):
        assert _git("check-ignore", "-q", name).returncode == 0, f"{name} must be ignored"
    assert _git("check-ignore", "-q", ".env.example").returncode == 1, ".env.example is the committed template"


def test_env_example_carries_no_secret_values():
    values = config.parse_dotenv((ROOT / ".env.example").read_text(encoding="utf-8"))
    for var in SECRET_VARS:
        assert var in values, f".env.example must list {var}"
        assert values[var] == "", f".env.example must leave {var} empty"
    assert not KEY_SHAPES.search((ROOT / ".env.example").read_text(encoding="utf-8"))


def test_no_key_shaped_strings_in_tracked_or_staged_files():
    listed = _git("ls-files", "-z", "--cached", "--others", "--exclude-standard").stdout
    offenders = []
    for rel in filter(None, listed.split("\0")):
        p = ROOT / rel
        if not p.is_file() or p.suffix not in TEXT_SUFFIXES or "vendor" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if KEY_SHAPES.search(text):
            offenders.append(rel)
    assert not offenders, f"key-shaped strings in files git would commit: {offenders}"
