#!/bin/sh
cd /home/yl222/workspace/UrbanWorldModel
PY=/data/yl222/workspace/UrbanWorldModel/.venv-region/bin/python
$PY input/windfarm_neural/run.py --kernel paper --seconds 300 > output/windfarm_neural/np4m_paper.log 2>&1
$PY input/windfarm_neural/run.py --kernel legacy --seconds 300 > output/windfarm_neural/np4m_legacy.log 2>&1
