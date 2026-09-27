"""冻结层桥接:新框架访问 src/engines、src/validation(只读科学基准)的唯一入口。

正典引擎与校验工具保持脚本式(无 __init__.py、靠 sys.path bootstrap),本模块把它们
以受控方式引进包世界。新代码【只能】通过这里 import 冻结层符号,不得直接改 sys.path。
"""
import os
import sys

_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # src/
for _sub in ("engines", "validation"):
    _p = os.path.join(_SRC, _sub)
    _p in sys.path or sys.path.insert(0, _p)

from BoHan_Scheduler_Multi import (                                   # noqa: E402  正典(SHA 74fff4d7…)
    build_multi, solve_multi, measure_theta_c_multi, theta_c_scalar_multi,
    brute_force_2uav,
)
from compute_F_energy import compute_F                                # noqa: E402  能量单一事实源

__all__ = ["build_multi", "solve_multi", "measure_theta_c_multi",
           "theta_c_scalar_multi", "brute_force_2uav", "compute_F"]
