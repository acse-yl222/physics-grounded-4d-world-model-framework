"""Namespaced access to the preserved numerical engine and energy routines."""

from uav_scheduling._vendor.src.engines.BoHan_Scheduler_Multi import (                                   # noqa: E402  正典(SHA 74fff4d7…)
    build_multi, solve_multi, measure_theta_c_multi, theta_c_scalar_multi,
    brute_force_2uav,
)
from uav_scheduling._vendor.src.validation.compute_F_energy import compute_F                                # noqa: E402  能量单一事实源

__all__ = ["build_multi", "solve_multi", "measure_theta_c_multi",
           "theta_c_scalar_multi", "brute_force_2uav", "compute_F"]
