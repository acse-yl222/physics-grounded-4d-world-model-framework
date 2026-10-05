# Task entry points. Every target is a thin wrapper over `python -m img2city ...`
# (see README "Usage"); nothing here is required, it just saves typing.

PY   ?= python
PORT ?= 8000

.PHONY: help env install install-lock lint test site-test webapp doctor lib-audit demo clean

help:
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

env:            ## create .env from .env.example (keeps an existing .env)
	@test -f .env && echo ".env exists" || (cp .env.example .env && echo "created .env -- fill in your keys / provider")

install:        ## core + web app + tests (permissive ranges)
	$(PY) -m pip install -e ".[web,dev]"

install-lock:   ## reproduce the reference environment exactly
	$(PY) -m pip install -r requirements-lock.txt && $(PY) -m pip install -e . --no-deps

lint:           ## ruff (pyflakes + real pycodestyle errors; config in pyproject.toml)
	$(PY) -m ruff check .

test:           ## unit layer: no Blender, no keys, no tokens
	$(PY) -m pytest tests -q --ignore=tests/test_site_integration.py

site-test:      ## against a live webapp on $(PORT) with real areas on disk
	IMG2CITY_TEST_BASE=http://localhost:$(PORT) $(PY) -m pytest tests/test_site_integration.py -v

webapp:         ## local demo web app on $(PORT)
	$(PY) -m img2city webapp --port $(PORT)

doctor:         ## what is installed, present, and reachable on this machine
	$(PY) -m img2city doctor

lib-audit:      ## regenerate docs/parts_library.md (git-ignored)
	$(PY) -m img2city lib-audit

demo:           ## offline render -> evaluate -> refine loop
	$(PY) -m img2city demo --max-iters 40

clean:          ## caches and build artefacts (keeps data/ and .cache/dreamsim)
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
