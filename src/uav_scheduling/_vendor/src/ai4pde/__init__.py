"""Minimal AI4PDE namespace required by the MFMU Mean-field backend."""

from .jacobi_cnn import THETA0_FRAC, THETA_MIN_FRAC, CNNJacobiField, CNNJacobiSolver
from .kernels import TravelKernel1D

__all__ = [
    "TravelKernel1D",
    "CNNJacobiField",
    "CNNJacobiSolver",
    "THETA0_FRAC",
    "THETA_MIN_FRAC",
]
