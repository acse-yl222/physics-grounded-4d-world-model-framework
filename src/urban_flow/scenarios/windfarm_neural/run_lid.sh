#!/bin/sh
cd /home/yl222/workspace/UrbanWorldModel
PY=/data/yl222/workspace/UrbanWorldModel/.venv-region/bin/python
G=output/windfarm_neural/geometry_4m_lid
$PY input/windfarm_neural/run.py --kernel paper --geometry $G --tag np4m_paper_lid --seconds 300 > output/windfarm_neural/np4m_paper_lid.log 2>&1
$PY input/windfarm_neural/run.py --kernel legacy --geometry $G --tag np4m_legacy_lid --seconds 300 > output/windfarm_neural/np4m_legacy_lid.log 2>&1
