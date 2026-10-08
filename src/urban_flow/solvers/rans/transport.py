"""Conservative Cartesian finite-volume operators, tensors ordered Z,Y,X.

Face arrays contain both domain boundary faces. Boundary scalar values are
specified at the face, not at an exterior cell centre. No implicit periodicity.
"""
import torch


def face_pair(q, axis, low=None, high=None):
    left = q.narrow(axis, 0, q.shape[axis]-1)
    right = q.narrow(axis, 1, q.shape[axis]-1)
    first = q.narrow(axis, 0, 1)
    last = q.narrow(axis, q.shape[axis]-1, 1)
    lo = first if low is None else torch.ones_like(first)*low
    hi = last if high is None else torch.ones_like(last)*high
    return torch.cat((lo, left, last), axis), torch.cat((first, right, hi), axis)


def divergence(fluxes, spacing_xyz):
    result = None
    for component, (flux, h) in enumerate(zip(fluxes, spacing_xyz)):
        if h <= 0:
            raise ValueError('Positive cell spacing required')
        value = torch.diff(flux, dim=2-component)/h
        result = value if result is None else result+value
    return result


def transport(q, face_velocity, diffusivity, spacing_xyz, boundaries=None):
    """Return -div(U q) + div(Gamma grad(q)), with first-order upwind advection.

    boundaries maps XYZ component to (low, high) Dirichlet face values;
    None means zero gradient. Caller supplies normal boundary velocities.
    Variable diffusivity uses arithmetic face interpolation.
    """
    if len(face_velocity) != 3 or len(spacing_xyz) != 3:
        raise ValueError('Three velocity components and spacings required')
    boundaries = boundaries or {}
    gamma = torch.ones_like(q)*diffusivity
    fluxes = []
    for component, (velocity, h) in enumerate(zip(face_velocity, spacing_xyz)):
        axis = 2-component
        expected = list(q.shape); expected[axis] += 1
        if list(velocity.shape) != expected:
            raise ValueError('Velocity must include both boundary faces')
        low, high = boundaries.get(component, (None, None))
        left, right = face_pair(q, axis, low, high)
        gl, gr = face_pair(gamma, axis)
        gradient = (right-left)/h
        # Boundary-to-centre separation is half a cell.
        if low is not None:
            gradient.narrow(axis, 0, 1).mul_(2)
        if high is not None:
            gradient.narrow(axis, q.shape[axis], 1).mul_(2)
        advected = torch.where(velocity >= 0, left, right)
        # Fixed face values apply to diffusive and incoming advective fluxes.
        fluxes.append(velocity*advected - .5*(gl+gr)*gradient)
    return -divergence(fluxes, spacing_xyz)
