"""2-D shallow-water flood solver in PyTorch (NN4PDEs style: every operator is a fixed stencil on tensors, runs on GPU).

Follows the semi-implicit free-surface approach of Chen, Nadimy, Heaney et al., "Solving the discretised shallow water
equations using neural networks", Adv. Water Resour. 2025 (github.com/Amin-Nadimy/Shallow_Water_Equations_NN4PDEs):
explicit advection + implicit Manning friction in the momentum predictor, then an implicit elliptic solve for the
free-surface increment that enforces continuity, then a velocity correction with the new surface gradient.
Differences from the released Carlisle code, chosen for urban wet/dry robustness (buildings, rainfall):
  * Arakawa C grid (depth at cell centres, u/v at faces) with upwind face depths  -> mass conserving, exact lake at rest,
    no flow through dry/raised cells (buildings are raised bed + solid mask, faces touching a building are walls);
  * conjugate-gradient solve of the symmetric positive-definite surface system to a tolerance, instead of 2 Jacobi sweeps;
  * first-order upwind momentum advection instead of Petrov-Galerkin stabilisation.

Equations (depth h, surface eta = z_b + h, unit width discharge q = H_f u at faces):
  d eta/dt + d(H u)/dx + d(H v)/dy = R - D                        (continuity, R rain, D drainage/infiltration)
  du/dt + u du/dx + v du/dy = -g d eta/dx - g n^2 |U| u / H^(4/3)   (momentum, same for v)

Arrays are [ny, nx] with row 0 = south, col 0 = west; u at interior x-faces [ny, nx-1], v at [ny-1, nx].
"""
import math

import torch
import torch.nn.functional as F

G = 9.81


class ShallowWater:
    def __init__(self, zb, solid, dx, manning, device, hmin=1e-4, cg_tol=1e-7, cg_max=400):
        self.dev = device
        self.dx = float(dx)
        self.zb = torch.as_tensor(zb, dtype=torch.float32, device=device)
        self.solid = torch.as_tensor(solid, dtype=torch.bool, device=device)
        self.ny, self.nx = self.zb.shape
        n = torch.as_tensor(manning, dtype=torch.float32, device=device)
        self.n_x = 0.5 * (n[:, :-1] + n[:, 1:]); self.n_y = 0.5 * (n[:-1] + n[1:])
        self.zfx = torch.maximum(self.zb[:, :-1], self.zb[:, 1:])        # face bottom = higher of the two cells
        self.zfy = torch.maximum(self.zb[:-1], self.zb[1:])
        self.wallx = self.solid[:, :-1] | self.solid[:, 1:]
        self.wally = self.solid[:-1] | self.solid[1:]
        self.h = torch.zeros_like(self.zb)
        self.u = torch.zeros(self.ny, self.nx - 1, device=device)
        self.v = torch.zeros(self.ny - 1, self.nx, device=device)
        self.hmin, self.cg_tol, self.cg_max = hmin, cg_tol, cg_max
        self.last_cg_iters = 0
        self.last_neg_volume = 0.0

    # ---------- helpers ----------
    @property
    def eta(self):
        return self.zb + self.h

    def face_depths(self, eta):
        eL, eR = eta[:, :-1], eta[:, 1:]
        up = torch.where(self.u > 0, eL, torch.where(self.u < 0, eR, torch.maximum(eL, eR)))
        Hx = torch.clamp(up - self.zfx, min=0.0)
        Hx = torch.where(self.wallx | (Hx < self.hmin), torch.zeros_like(Hx), Hx)
        eS, eN = eta[:-1], eta[1:]
        up = torch.where(self.v > 0, eS, torch.where(self.v < 0, eN, torch.maximum(eS, eN)))
        Hy = torch.clamp(up - self.zfy, min=0.0)
        Hy = torch.where(self.wally | (Hy < self.hmin), torch.zeros_like(Hy), Hy)
        return Hx, Hy

    def _v_at_ufaces(self):
        """v (ny-1, nx) averaged to interior x-faces (ny, nx-1)."""
        vp = F.pad(self.v, (0, 0, 1, 1))                                   # (ny+1, nx), zero at boundary faces
        vc = 0.5 * (vp[:-1] + vp[1:])                                       # cell centres (ny, nx)
        return 0.5 * (vc[:, :-1] + vc[:, 1:])

    def _u_at_vfaces(self):
        up = F.pad(self.u, (1, 1, 0, 0))                                   # (ny, nx+1)
        uc = 0.5 * (up[:, :-1] + up[:, 1:])
        return 0.5 * (uc[:-1] + uc[1:])

    @staticmethod
    def _upwind_x(f, vel):
        """upwind d f/dx (in cells) for a field f on a regular array, advecting velocity vel (same shape)."""
        fp = torch.cat([f[:, :1], f, f[:, -1:]], dim=1)
        back = fp[:, 1:-1] - fp[:, :-2]; fwd = fp[:, 2:] - fp[:, 1:-1]
        return torch.where(vel > 0, back, fwd)

    @staticmethod
    def _upwind_y(f, vel):
        fp = torch.cat([f[:1], f, f[-1:]], dim=0)
        back = fp[1:-1] - fp[:-2]; fwd = fp[2:] - fp[1:-1]
        return torch.where(vel > 0, back, fwd)

    def _div(self, Hx, Hy, u, v):
        """d(Hu)/dx + d(Hv)/dy at cell centres, divided by dx (returns per metre)."""
        qx = F.pad(Hx * u, (1, 1, 0, 0)); qy = F.pad(Hy * v, (0, 0, 1, 1))
        return (qx[:, 1:] - qx[:, :-1] + qy[1:] - qy[:-1]) / self.dx

    def _grad_x(self, f):
        return (f[:, 1:] - f[:, :-1]) / self.dx

    def _grad_y(self, f):
        return (f[1:] - f[:-1]) / self.dx

    def _apply_A(self, d, Hx, Hy, c):
        """(I - c div(H grad)) d, c = g dt^2."""
        return d - c * self._div(Hx, Hy, self._grad_x(d), self._grad_y(d))

    def _cg(self, rhs, Hx, Hy, c):
        """Jacobi-preconditioned conjugate gradient for the surface increment."""
        diag = 1.0 + c / self.dx ** 2 * (F.pad(Hx, (1, 1, 0, 0))[:, 1:] + F.pad(Hx, (1, 1, 0, 0))[:, :-1]
                                         + F.pad(Hy, (0, 0, 1, 1))[1:] + F.pad(Hy, (0, 0, 1, 1))[:-1])
        x = rhs / diag
        r = rhs - self._apply_A(x, Hx, Hy, c)
        tol = self.cg_tol * torch.linalg.vector_norm(rhs)
        self.last_cg_iters = 0
        if torch.linalg.vector_norm(r) <= tol:
            return x
        z = r / diag; p = z.clone(); rz = torch.sum(r * z)
        for k in range(1, self.cg_max + 1):
            Ap = self._apply_A(p, Hx, Hy, c)
            pAp = torch.sum(p * Ap)
            if pAp <= 0:
                break
            alpha = rz / pAp
            x = x + alpha * p; r = r - alpha * Ap
            self.last_cg_iters = k
            if torch.linalg.vector_norm(r) <= tol:
                break
            z = r / diag; rz_new = torch.sum(r * z)
            p = z + (rz_new / rz) * p; rz = rz_new
        return x

    # ---------- one time step ----------
    def step(self, dt, source=None, sink_rate=None, absorb=None):
        """Advance dt seconds. source: depth rate [m/s] added (rain incl. redistributed roof runoff); sink_rate: max depth
        removal rate [m/s] (drainage/infiltration), applied after the solve; absorb: bool mask of cells emptied each step
        (open boundary). Returns dict of volumes (m^3) moved this step."""
        dx, g = self.dx, G
        eta = self.eta
        Hx, Hy = self.face_depths(eta)
        wetx, wety = Hx > 0, Hy > 0
        # momentum predictor: upwind advection, implicit friction, explicit old surface gradient
        v_u = self._v_at_ufaces(); u_v = self._u_at_vfaces()
        adv_u = (self.u * self._upwind_x(self.u, self.u) + v_u * self._upwind_y(self.u, v_u)) / dx
        adv_v = (u_v * self._upwind_x(self.v, u_v) + self.v * self._upwind_y(self.v, self.v)) / dx
        u_hat = self.u - dt * adv_u - g * dt * self._grad_x(eta)
        v_hat = self.v - dt * adv_v - g * dt * self._grad_y(eta)
        cf_x = g * self.n_x ** 2 * torch.sqrt(self.u ** 2 + v_u ** 2) / torch.clamp(Hx, min=self.hmin) ** (4.0 / 3.0)
        cf_y = g * self.n_y ** 2 * torch.sqrt(u_v ** 2 + self.v ** 2) / torch.clamp(Hy, min=self.hmin) ** (4.0 / 3.0)
        u_hat = torch.where(wetx, u_hat / (1.0 + dt * cf_x), torch.zeros_like(u_hat))
        v_hat = torch.where(wety, v_hat / (1.0 + dt * cf_y), torch.zeros_like(v_hat))
        # implicit surface increment: (I - g dt^2 div H grad) d_eta = -dt div(H u_hat) + dt S
        rhs = -dt * self._div(Hx, Hy, u_hat, v_hat)
        if source is not None:
            rhs = rhs + dt * source
        c = g * dt * dt
        d_eta = self._cg(rhs, Hx, Hy, c)
        self.u = torch.where(wetx, u_hat - g * dt * self._grad_x(d_eta), torch.zeros_like(u_hat))
        self.v = torch.where(wety, v_hat - g * dt * self._grad_y(d_eta), torch.zeros_like(v_hat))
        h_new = self.h + d_eta
        neg = torch.clamp(-h_new, min=0.0)
        self.last_neg_volume = float(neg.sum().item()) * dx * dx
        h_new = torch.clamp(h_new, min=0.0)
        h_new = torch.where(self.solid, torch.zeros_like(h_new), h_new)
        out = {'neg_clamped': self.last_neg_volume, 'cg_iters': self.last_cg_iters}
        if sink_rate is not None:
            drained = torch.minimum(h_new, sink_rate * dt)
            h_new = h_new - drained
            out['drained'] = float(drained.sum().item()) * dx * dx
        if absorb is not None:
            out['outflow'] = float(h_new[absorb].sum().item()) * dx * dx
            h_new = torch.where(absorb, torch.zeros_like(h_new), h_new)
        if source is not None:
            out['source'] = float(source.sum().item()) * dt * dx * dx
        self.h = h_new
        return out

    def max_speed(self):
        m = 0.0
        if self.u.numel():
            m = max(m, float(self.u.abs().max().item()))
        if self.v.numel():
            m = max(m, float(self.v.abs().max().item()))
        return m

    def cell_speed(self):
        up = F.pad(self.u, (1, 1, 0, 0)); vp = F.pad(self.v, (0, 0, 1, 1))
        uc = 0.5 * (up[:, :-1] + up[:, 1:]); vc = 0.5 * (vp[:-1] + vp[1:])
        return torch.sqrt(uc ** 2 + vc ** 2), uc, vc

    def volume(self):
        return float(self.h.sum().item()) * self.dx * self.dx

    def stable_dt(self, dt_max, cfl=0.7):
        s = self.max_speed()
        return dt_max if s < 1e-6 else min(dt_max, cfl * self.dx / s)
