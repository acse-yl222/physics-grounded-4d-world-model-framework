"""Steady conservative tracer on existing MAC face conventions.

Input source is mass/time/cell; concentration is mass/volume. Donor-cell advection,
constant isotropic diffusion, impermeable solids. Open west/east/top connect to
zero background; half-cell Dirichlet distance for diffusion. No chemistry.
"""
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu, spilu, LinearOperator, bicgstab


class SteadyTracer:
    def __init__(self, fluid, faces, inlet, cell_m, diffusivity, open_top=True):
        self.fluid = np.asarray(fluid, dtype=bool)
        self.h, self.k = float(cell_m), float(diffusivity)
        if self.fluid.ndim != 3 or self.h <= 0 or self.k <= 0:
            raise ValueError('Require 3-D fluid grid, positive spacing and diffusivity')
        self.ids = np.full(self.fluid.shape, -1, dtype=int)
        self.n = int(self.fluid.sum())
        if not self.n:
            raise ValueError('No fluid cells')
        self.ids[self.fluid] = np.arange(self.n)
        self.out_coeff = np.zeros(self.n)
        rows, cols, values = [], [], []
        def add(i, j, value):
            rows.append(np.asarray(i).ravel())
            cols.append(np.asarray(j).ravel())
            values.append(np.broadcast_to(value, np.shape(i)).ravel())
        for component, face in enumerate(faces):
            face = np.asarray(face, dtype=float)
            if face.shape != self.fluid.shape or not np.isfinite(face).all():
                raise ValueError('Invalid face velocities')
            axis = 2-component
            left = [slice(None)]*3; right = [slice(None)]*3
            left[axis] = slice(None, -1); right[axis] = slice(1, None)
            left, right = tuple(left), tuple(right)
            opened = self.fluid[left] & self.fluid[right]
            i, j = self.ids[left][opened], self.ids[right][opened]
            u = face[left][opened]/self.h
            a = np.maximum(u, 0) + self.k/self.h**2
            b = np.maximum(-u, 0) + self.k/self.h**2
            add(i, i, a); add(j, i, -a); add(j, j, b); add(i, j, -b)
        def boundary(sl, outward):
            valid = self.fluid[sl]; i = self.ids[sl][valid]
            u = np.broadcast_to(outward, valid.shape)[valid]
            coefficient = np.maximum(u, 0)/self.h + 2*self.k/self.h**2
            add(i, i, coefficient)
            np.add.at(self.out_coeff, i, coefficient)
        boundary((slice(None), slice(None), 0), -np.asarray(inlet))
        boundary((slice(None), slice(None), -1), np.asarray(faces[0])[:, :, -1])
        if open_top:
            boundary((-1, slice(None), slice(None)), np.asarray(faces[2])[-1])
        self.matrix = sparse.coo_matrix((np.concatenate(values), (np.concatenate(rows), np.concatenate(cols))),
                                        shape=(self.n, self.n)).tocsc()
        if self.n < 35000:
            factor = splu(self.matrix)
            self.solve_vector = factor.solve
            self.method = 'sparse_lu'
        else:
            factor = spilu(self.matrix, drop_tol=1e-3, fill_factor=8)
            preconditioner = LinearOperator(self.matrix.shape, factor.solve)
            def iterative(rhs):
                result, code = bicgstab(self.matrix, rhs, M=preconditioner, rtol=1e-9, atol=1e-13, maxiter=3000)
                if code:
                    raise RuntimeError(f'Tracer solve did not converge: {code}')
                return result
            self.solve_vector = iterative
            self.method = 'ilu_bicgstab'

    def solve(self, source_mass_per_s):
        source = np.asarray(source_mass_per_s, dtype=float)
        if source.shape != self.fluid.shape or not np.isfinite(source).all() or (source < 0).any():
            raise ValueError('Source must be finite, nonnegative and match the grid')
        if np.any(source[~self.fluid] != 0):
            raise ValueError('Source in solid cells; do not discard mass')
        rhs = source[self.fluid]/self.h**3
        c = self.solve_vector(rhs)
        residual = np.linalg.norm(self.matrix @ c-rhs)/max(np.linalg.norm(rhs), 1e-30)
        emitted = float(source.sum())
        escaped = float(np.dot(self.out_coeff, c)*self.h**3)
        balance = abs(escaped-emitted)/max(emitted, 1e-30)
        if residual > 1e-6 or balance > 1e-6 or c.min() < -1e-10*max(float(c.max()), 1):
            raise RuntimeError(f'Tracer checks failed: residual={residual}, balance={balance}, min={c.min()}')
        field = np.zeros(source.shape)
        field[self.fluid] = c
        return field, {'linear_relative_residual': float(residual), 'mass_balance_relative_error': balance,
                       'emitted_au_s': emitted, 'boundary_loss_au_s': escaped,
                       'minimum': float(c.min()), 'maximum': float(c.max()), 'linear_solver': self.method}

