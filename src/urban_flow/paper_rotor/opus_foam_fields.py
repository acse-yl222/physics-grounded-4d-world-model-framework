"""Read-only access to reconstructed ASCII OpenFOAM fields on the uniform B.2 block mesh.

Single-block blockMesh cells are ordered i + nx*(j + ny*k) (x fastest). The
mapping is verified against a written cell-centre field before any analysis;
nothing in the source case is modified. Parsed arrays may be cached as .npy in a
caller-provided scratch directory.
"""
import hashlib
import json
from pathlib import Path
import re

import numpy as np


def read_internal(path):
    """Return internalField as (N,) or (N,3) float array; reject uniform fields."""
    raw = Path(path).read_bytes()
    match = re.search(rb'internalField\s+nonuniform\s+List<(scalar|vector)>\s*\n?(\d+)\s*\n?\(', raw)
    if not match:
        raise ValueError(f'No nonuniform internalField in {path}')
    kind, count = match.group(1), int(match.group(2))
    start = match.end()
    end = raw.index(b'\n)', start)
    body = raw[start:end]
    if kind == b'vector':
        body = body.replace(b'(', b' ').replace(b')', b' ')
    values = np.array(body.split(), dtype=float)
    width = 3 if kind == b'vector' else 1
    if values.size != count*width:
        raise ValueError(f'{path}: expected {count*width} values, parsed {values.size}')
    return values.reshape(count, 3) if width == 3 else values


class Grid:
    """Uniform structured grid reconstructed from configuration and verified against C."""

    def __init__(self, config):
        self.n = tuple(config['grid_cells_xyz'])
        self.length = tuple(config['domain_xyz_m'])
        self.h = tuple(L/n for L, n in zip(self.length, self.n))
        self.axes = [(np.arange(n)+0.5)*h for n, h in zip(self.n, self.h)]
        self.volume = float(np.prod(self.h))

    def cube(self, flat):
        nx, ny, nz = self.n
        a = np.asarray(flat)
        return a.reshape((nz, ny, nx) + a.shape[1:]).transpose((2, 1, 0) + tuple(range(3, a.ndim+2)))

    def verify(self, centres):
        nx, ny, nz = self.n
        if centres.shape != (nx*ny*nz, 3):
            raise ValueError('Cell count mismatch')
        c = self.cube(centres)
        X, Y, Z = np.meshgrid(*self.axes, indexing='ij')
        err = max(float(np.abs(c[..., 0]-X).max()), float(np.abs(c[..., 1]-Y).max()), float(np.abs(c[..., 2]-Z).max()))
        return err


def cached(path, scratch):
    """Parse once; key the .npy cache by the source file's SHA-256 to avoid stale reuse."""
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    target = Path(scratch)/f'{digest[:24]}.npy'
    if target.exists():
        return np.load(target), digest
    array = read_internal(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    np.save(target, array)
    return array, digest


def load_case(case, iteration, names, scratch):
    case = Path(case)
    fields, digests = {}, {}
    for name in names:
        fields[name], digests[name] = cached(case/str(iteration)/name, scratch)
    return fields, digests


def write_progress(path, stage, payload):
    path = Path(path)
    record = json.loads(path.read_text()) if path.exists() else {'stages': {}}
    record['stages'][stage] = payload
    path.write_text(json.dumps(record, indent=1))
