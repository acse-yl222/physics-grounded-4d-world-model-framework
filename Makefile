PYTHON ?= python3

.PHONY: format format-check test test-python test-js test-browser

format:
	$(PYTHON) tools/format.py --write

format-check:
	$(PYTHON) tools/format.py --check

test: test-python test-js

test-python:
	$(PYTHON) tools/check_contract.py examples/contract-v1/manifest.json
	$(PYTHON) tools/check_contract.py examples/contract-v1.1/manifest.json
	$(PYTHON) -m unittest discover -s tests -v

test-js:
	npm test

test-browser:
	$(PYTHON) tools/check_browser.py
