#!/bin/sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR/../../../.." || exit 1
PY=/data/yl222/workspace/UrbanWorldModel/.venv-region/bin/python
$PY input/windfarm_neural/run.py --kernel paper --open-top --seconds 300 > output/windfarm_neural/np4m_paper_opentop.log 2>&1
$PY input/windfarm_neural/run.py --kernel legacy --open-top --seconds 300 > output/windfarm_neural/np4m_legacy_opentop.log 2>&1
