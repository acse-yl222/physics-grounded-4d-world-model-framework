"""img2city/imagery/batch_campus.py -- run the auto-fetch + agent-judge pipeline over a whole list
of buildings (one South Kensington campus pass).

Reads a building list (one building per line; '#' comments skipped) and runs
imagery.acquire_view for each, saving into data/<slug>/. Continues past failures and
prints a summary at the end.

  python -m img2city.imagery.batch_campus
  python -m img2city.imagery.batch_campus --list examples/buildings_south_kensington.txt --n 6

Heavy: each building does a satellite + a ring of street-view candidates + a
vision judge per candidate. Start with the short curated list, review, then add more.
"""
from __future__ import annotations
import argparse
import os
import re
import subprocess

from img2city import config
from img2city.agent import llm

DEFAULT_LIST = str(config.PROJECT_ROOT / "examples" / "buildings_south_kensington.txt")


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s[:40] or "building"


def main():
    ap = argparse.ArgumentParser(description="Batch-run acquire_view over a building list")
    ap.add_argument("--list", default=DEFAULT_LIST)
    ap.add_argument("--backend", choices=llm.BACKEND_CHOICES, default=None,
                    help="override IMG2CITY_LLM_PROVIDER (.env) for this run")
    ap.add_argument("--n", type=int, default=6, help="ring sample points per building (lower = cheaper)")
    ap.add_argument("--out-root", default=str(config.DATA_DIR))
    a = ap.parse_args()

    with open(a.list) as f:
        names = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
    print(f"{len(names)} buildings to process (provider={a.backend or config.LLM_PROVIDER}, n={a.n})\n")

    summary = []
    for i, name in enumerate(names, 1):
        out = os.path.join(a.out_root, slug(name))
        print(f"[{i}/{len(names)}] {name} -> {out}")
        try:
            r = subprocess.run(
                config.module_cmd("imagery.acquire_view",
                                  "--query", name, *(["--backend", a.backend] if a.backend else []),
                                  "--n", str(a.n), "--out", out),
                cwd=str(config.PROJECT_ROOT), env=config.subprocess_env(), timeout=1200)
            ok = (r.returncode == 0) and os.path.exists(os.path.join(out, "streetview.png"))
        except Exception as e:
            print("  error:", e)
            ok = False
        summary.append((name, "ok" if ok else "no-good-view", out))

    print("\n=== summary ===")
    for name, status, out in summary:
        print(f"  {status:13} {name}  ({out})")
    ok_n = sum(1 for _, s, _ in summary if s == "ok")
    print(f"\n{ok_n}/{len(summary)} got a usable street view; "
          "the rest have satellite + candidates/ (use your own photo or raise --n/--radius).")


if __name__ == "__main__":
    main()
