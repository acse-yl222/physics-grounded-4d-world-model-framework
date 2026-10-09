"""Conservative 2-D passive tracer driven by a recorded horizontal wind slice.

This controlled planar experiment has arbitrary concentration units. It is not
a 3-D pollution forecast, emissions inventory, or health exposure prediction.
"""
import numpy as np


class PlanarTracer:
    def __init__(self, uv, invalid, cell_m, diffusion=1.0):
        self.invalid = np.asarray(invalid, bool)
        self.dx = float(cell_m)
        self.diffusion = float(diffusion)
        if self.dx <= 0 or self.diffusion < 0:
            raise ValueError('Invalid spacing or diffusion')
        uv = np.asarray(uv, dtype=np.float64)
        if uv.shape != (2, *self.invalid.shape) or not np.isfinite(uv).all():
            raise ValueError('Expected finite horizontal ENU wind')
        ny, nx = self.invalid.shape
        self.u = np.zeros((ny, nx + 1))
        self.v = np.zeros((ny + 1, nx))
        self.u[:, 1:-1] = (uv[0, :, :-1] + uv[0, :, 1:]) / 2
        self.v[1:-1] = (uv[1, :-1] + uv[1, 1:]) / 2
        self.u[:, 0], self.u[:, -1] = uv[0, :, 0], uv[0, :, -1]
        self.v[0], self.v[-1] = uv[1, 0], uv[1, -1]
        self.open_x = np.ones_like(self.u, bool)
        self.open_y = np.ones_like(self.v, bool)
        self.open_x[:, :-1] &= ~self.invalid
        self.open_x[:, 1:] &= ~self.invalid
        self.open_y[:-1] &= ~self.invalid
        self.open_y[1:] &= ~self.invalid
        self.u *= self.open_x
        self.v *= self.open_y
        outgoing = (np.maximum(self.u[:, 1:], 0) + np.maximum(-self.u[:, :-1], 0)
                    + np.maximum(self.v[1:], 0) + np.maximum(-self.v[:-1], 0)) / self.dx
        self.dt_max = .9 / max(float(outgoing.max()) + 4 * self.diffusion / self.dx**2, 1e-12)
        self.c = np.zeros(self.invalid.shape, dtype=np.float64)

    def step(self, dt, source):
        if not 0 < dt <= self.dt_max * (1 + 1e-10):
            raise ValueError('Time step exceeds positivity CFL')
        source = np.asarray(source, dtype=np.float64)
        if source.shape != self.c.shape or not np.isfinite(source).all() or (source < 0).any() or source[self.invalid].any():
            raise ValueError('Expected nonnegative source only in valid cells')
        # Zero external concentration for advective inflow; zero-gradient diffusion
        # at the outer boundary. Interior building faces are impermeable.
        x = np.pad(self.c, ((0, 0), (1, 1)))
        y = np.pad(self.c, ((1, 1), (0, 0)))
        fx = self.u * np.where(self.u >= 0, x[:, :-1], x[:, 1:])
        fy = self.v * np.where(self.v >= 0, y[:-1], y[1:])
        fx[:, 1:-1] -= self.diffusion * np.diff(self.c, axis=1) / self.dx * self.open_x[:, 1:-1]
        fy[1:-1] -= self.diffusion * np.diff(self.c, axis=0) / self.dx * self.open_y[1:-1]
        before = float(self.c.sum()) * self.dx**2
        self.c += dt * (source - (np.diff(fx, axis=1) + np.diff(fy, axis=0)) / self.dx)
        if not np.isfinite(self.c).all() or self.c.min() < -1e-12 or self.c[self.invalid].any():
            raise RuntimeError('Tracer positivity/solid/finite check failed')
        emitted = dt * float(source.sum()) * self.dx**2
        outflow = dt * float(fx[:, -1].sum() - fx[:, 0].sum() + fy[-1].sum() - fy[0].sum()) * self.dx
        mass = float(self.c.sum()) * self.dx**2
        return {'mass': mass, 'emitted': emitted, 'outflow': outflow,
                'balance_error': mass - before - emitted + outflow}
