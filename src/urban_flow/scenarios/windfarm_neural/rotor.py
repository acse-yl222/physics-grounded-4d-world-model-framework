"""Compatibility import; implementation moved to src/urban_flow/solvers/rotor.py."""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
from pathlib import Path
import sys
sys.path.insert(0, str(repo_root() / 'src'))
from urban_flow.solvers.rotor import WeightedRotor
