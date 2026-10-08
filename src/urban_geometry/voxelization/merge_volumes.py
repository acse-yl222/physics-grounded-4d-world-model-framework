"""Union aligned ENU occupancy masks, retaining their distinct source semantics."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def merge(inputs, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    records = []
    result = None
    reference = None
    for folder in map(Path, inputs):
        metadata = json.loads((folder / 'metadata.json').read_text())
        grid = {key: metadata[key] for key in ('shape_zyx', 'origin_xyz_m', 'spacing_xyz_m')}
        if reference is None:
            reference = grid
        if grid != reference:
            raise ValueError('Cannot merge differently aligned occupancy grids')
        solid = np.load(folder / 'solid.npy', allow_pickle=False)
        if solid.dtype != np.bool_ or list(solid.shape) != grid['shape_zyx']:
            raise ValueError('Expected boolean ZYX occupancy')
        result = solid.copy() if result is None else result | solid
        records.append({'source': str(folder.resolve()), 'metadata': metadata,
                        'solid_sha256': hashlib.sha256((folder / 'solid.npy').read_bytes()).hexdigest(),
                        'occupied_cells': int(solid.sum())})
    if result is None or not result.any() or result[-1].any() or result[:, :, 0].any():
        raise ValueError('Empty geometry or obstructed top/inlet')
    np.save(output / 'solid.npy', result)
    levels = reference['origin_xyz_m'][2] + (np.arange(result.shape[0]) + 1) * reference['spacing_xyz_m'][2]
    np.save(output / 'height_m.npy', np.max(np.where(result, levels[:, None, None], 0), axis=0).astype('<f4'))
    metadata = dict(reference, frame='ENU', occupied_cells=int(result.sum()), sources=records,
                    method='Boolean union of separately prepared source geometry volumes',
                    limits=['Source metadata contains independent occupancy assumptions and height provenance.',
                            'Computational padding outside supplied geometry is unknown and treated as empty.',
                            'Height map is maximum occupied cell upper face, not surveyed roof height.'])
    (output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', action='append', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(merge(args.input, args.output), indent=2))
