"""Unit tests for the deterministic (no-Blender, no-API, no-token) layer of
the pipeline. Heavy optional imports (torch chains, SDK) are skipped
gracefully so the light subset runs anywhere, including bare CI.

The repository root is put on sys.path so `import img2city` works from a
plain checkout without `pip install -e .`."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
