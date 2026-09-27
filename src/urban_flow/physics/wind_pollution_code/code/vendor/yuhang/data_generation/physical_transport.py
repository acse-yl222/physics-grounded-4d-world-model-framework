from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class StepResult:
    concentration: torch.Tensor
    iterations: int
    residual: float
    outflow: torch.Tensor


def _faces(
    vel: torch.Tensor,
    solid: torch.Tensor,
    dim: int,
    low: float,
    high: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Interpolate cell velocities to open faces and mask faces touching solids."""

    v = vel.movedim(dim, -1)
    s = solid.movedim(dim, -1)
    face = 0.5 * (v[..., :-1] + v[..., 1:])
    face = face * (~(s[..., :-1] | s[..., 1:]))
    left = torch.zeros_like(v)
    right = torch.zeros_like(v)
    left[..., 1:] = face
    right[..., :-1] = face
    left[..., 0] = low
    right[..., -1] = high
    return left.movedim(-1, dim), right.movedim(-1, dim)


def _neighbours(field: torch.Tensor, dim: int) -> tuple[torch.Tensor, torch.Tensor]:
    """Build zero-padded neighbour fields on both sides of one axis."""

    value = field.movedim(dim, -1)
    left = torch.zeros_like(value)
    right = torch.zeros_like(value)
    left[..., 1:] = value[..., :-1]
    right[..., :-1] = value[..., 1:]
    return left.movedim(-1, dim), right.movedim(-1, dim)


def _coeff(left: torch.Tensor, right: torch.Tensor) -> tuple[torch.Tensor, ...]:
    """Form first-order upwind coefficients and a diagonal bound from face velocities."""

    hl = (left > 0).to(left.dtype)
    hr = (right > 0).to(right.dtype)
    prev = -hl * left
    after = (1 - hr) * right
    center = hr * right - (1 - hl) * left
    diag = torch.maximum(left.abs(), right.abs())
    return prev, after, center, diag


def _outflow(field: torch.Tensor, ub: float, vb: float) -> torch.Tensor:
    """Integrate concentration leaving the x and y boundaries under prescribed flow."""

    total = field.new_zeros(())
    if ub < 0:
        total = total - ub * field[..., 0].sum()
    elif ub > 0:
        total = total + ub * field[..., -1].sum()
    if vb < 0:
        total = total - vb * field[:, 0].sum()
    elif vb > 0:
        total = total + vb * field[:, -1].sum()
    return total


def upwind_step(
    concentration: torch.Tensor,
    u: torch.Tensor,
    v: torch.Tensor,
    w: torch.Tensor,
    solid: torch.Tensor,
    source: torch.Tensor,
    *,
    dt: float,
    ub: float,
    vb: float = 0.0,
    max_iter: int = 200,
    tol: float = 1e-10,
) -> StepResult:
    """Advance one SCALED-grid scalar step with open, non-periodic boundaries."""

    fields = (concentration, u, v, w, solid, source)
    if concentration.ndim != 3 or any(field.shape != concentration.shape for field in fields):
        raise ValueError("transport fields must be matching three-dimensional tensors")
    if dt <= 0 or max_iter < 1 or tol <= 0:
        raise ValueError("dt, max_iter, and tol must be positive")

    mask = solid.bool()
    src = source.masked_fill(mask, 0)
    ul, ur = _faces(u, mask, 2, ub, ub)
    vl, vr = _faces(v, mask, 1, vb, vb)
    wl, wr = _faces(w, mask, 0, 0.0, 0.0)
    axm, axp, acx, bx = _coeff(ul, ur)
    aym, ayp, acy, by = _coeff(vl, vr)
    azm, azp, acz, bz = _coeff(wl, wr)
    center = 1 / dt + acx + acy + acz
    diag = 1 / dt + bx + by + bz

    value = concentration.masked_fill(mask, 0).clone()
    residual = float("inf")
    for iteration in range(1, max_iter + 1):
        xm, xp = _neighbours(value, 2)
        ym, yp = _neighbours(value, 1)
        zm, zp = _neighbours(value, 0)
        rhs = (
            concentration / dt
            + src
            + (diag - center) * value
            - axm * xm
            - axp * xp
            - aym * ym
            - ayp * yp
            - azm * zm
            - azp * zp
        )
        updated = (rhs / diag).masked_fill(mask, 0)
        scale = value.abs().max().clamp_min(1e-12)
        residual = float(((updated - value).abs().max() / scale).item())
        value = updated
        if residual < tol:
            break
    else:
        raise RuntimeError(f"pollution step did not converge: residual={residual:.3e}")

    return StepResult(value, iteration, residual, _outflow(value, ub, vb))
