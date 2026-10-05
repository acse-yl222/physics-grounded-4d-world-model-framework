# Img2City — working notes for Claude Code

Agentic pipeline: OSM footprints + satellite / Street View in, editable
parametric Blender city out. `README.md` is the user-facing entry;
`docs/architecture.md` explains the package map and the three coupling
mechanisms (bare imports, subprocess stages, Blender-injected source).

## Hard rules

- **The old thesis repo is read-only.** `~/irp-xm525` (remote
  `github.com/ese-ada-lovelace-2025/irp-xm525`) is the finished, graded IRP
  submission. Copy files *out* of it when useful; never edit, commit, or push
  anything into it. All git work happens here, remote `MIAO121131/Img2City`.
- **Blender-side code never imports `img2city`.** `img2city/kit/*.py`,
  `prior/headless_gen.py`, `webapp/export_glb.py`, `webapp/rebuild_bpy.py`
  run inside Blender via source injection / `blender --python`; they must stay
  self-contained (see `kit.load_kit_src()`).
- **Stages are modules, never loose scripts.** Spawn them through
  `config.module_cmd("city.height_check", ...)`; the CLI table lives in
  `img2city/cli.py`.
- **Unit tests need no Blender, no keys, no tokens.** Anything that talks to
  Claude, Google, or Blender belongs behind `importorskip` / the live-server
  skip in `tests/test_site_integration.py`.

## Environment on this machine

- Python: conda env `mpm2025` (3.13). `anthropic` is not installed, so the
  `claude-api` provider is unavailable until `pip install anthropic`;
  `codex` / `claude-sdk` work through the local CLI logins.
- Blender 4.5 LTS with BlenderMCP on `localhost:9876`.
- The old repo's webapp may still be running on port **8000**; start this one
  with `img2city webapp --port 8001` (or `make webapp PORT=8001`) and run the
  site tests with `IMG2CITY_TEST_BASE=http://localhost:8001`.
- Large assets are git-ignored and must be present locally
  (`img2city doctor` lists them): `data/<area>/`, `data/prior/param_model.pt`,
  `.cache/dreamsim/`.

## Commands

```bash
make test                 # unit layer (fast, offline)
make site-test PORT=8001  # against a live webapp with real areas on disk
make webapp PORT=8001
make doctor               # what is installed / present / reachable
make lib-audit            # regenerates docs/parts_library.md (git-ignored)
```

## Conventions

- Configuration is `.env` / environment only (`img2city/config.py` loads
  `.env` on import); never hard-code paths, endpoints or model names.
- Every model call goes through `img2city.agent.llm.vision_call`; the
  provider (`IMG2CITY_LLM_PROVIDER`) and the per-role models come from `.env`,
  `<provider>:<model>` pins a provider per call. Transports live in
  `agent/openai_backend.py` and `agent/claude_backend.py`; callers never
  import an SDK directly.
- `make lint` (ruff, config in `pyproject.toml`) and `make test` must pass;
  CI runs both.
- Keep `docs/parts_library.md` out of git; it is a generated manifest.
- `requirements-lock.txt` is the reproducible pin set; `pyproject.toml` keeps
  the permissive ranges. Update the lock deliberately, not as a side effect.
- Generated areas, runs, weights, `.blend`/`.glb` files stay out of git.
