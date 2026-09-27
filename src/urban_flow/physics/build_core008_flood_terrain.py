"""Build the flood terrain for the scaled_latent domain: EA 2022 LIDAR composite DTM (1 m, bare earth, ODN) resampled
onto the simulation grid, plus the core008 building block (DTM + sampled roof height) and land-cover masks.

Grid (same as output/core008/physics/scaled_latent): 1 m cells, domain x = [480, 3552), y = [640, 3456) -> [2816, 3072],
row 0 = south, col 0 = west. 4 m versions are 4x4 block aggregates -> [704, 768], identical to wind4m_*.npy.

Coordinates: grid -> domain -> region (- (2116, 2124)) -> EPSG:32630 (+ region origin) -> EPSG:27700 via pyproj
(OSTN15, 1 m accuracy) -> bilinear sample of the four tiles TQ27ne/TQ27nw/TQ28se/TQ28sw (output/core008/geometry/ea_lidar_dtm_1m).

Outputs: output/core008/physics/scaled_latent/flood/terrain/
"""
from pathlib import Path as _UwmPath
import sys as _uwm_sys
_uwm_sys.path.insert(0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / 'common').is_dir())))
from common.layout import repo_root
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image
from pyproj.transformer import TransformerGroup
from scipy import ndimage

ROOT = repo_root()
TILES = ROOT / 'output/core008/geometry/ea_lidar_dtm_1m'
GEOM_1M = ROOT / 'output/core008/geometry/south_kensington_core008_voxel_1m_domain4096'
LANDCOVER = ROOT / 'output/core008/geometry/south_kensington_core008_landcover_4m'
OUT = ROOT / 'output/core008/physics/scaled_latent/flood/terrain'
OUT.mkdir(parents=True, exist_ok=True)

X0, X1, Y0, Y1 = 480, 3552, 640, 3456            # domain metres
REGION_OFFSET = np.array([2116.0, 2124.0])        # domain = region + offset
UTM_ORIGIN = np.array([695238.304719173, 5709236.965026026])
NODATA = -3.4e38
PIT_AOD_M = -2.0                                  # DTM values below this (river bed / artefacts) are treated as holes


def log(msg):
    print(time.strftime('%H:%M:%S'), msg, flush=True)


def load_mosaic():
    """E 520000..530000, N 175000..185000 at 1 m; row 0 = north (N 184999.5), col 0 = west (E 520000.5)."""
    mosaic = np.full((10000, 10000), np.nan, np.float32)
    for name in ('TQ27ne', 'TQ27nw', 'TQ28se', 'TQ28sw'):
        tfw = [float(v) for v in (TILES / f'{name}_DTM_1m.tfw').read_text().split()]
        e0, n0 = tfw[4], tfw[5]                              # centre of the top-left pixel
        a = np.array(Image.open(TILES / f'{name}_DTM_1m.tif'), np.float32)
        a[a < -1e30] = np.nan
        r0 = int(round(184999.5 - n0)); c0 = int(round(e0 - 520000.5))
        mosaic[r0:r0 + a.shape[0], c0:c0 + a.shape[1]] = a
        log(f'{name}: {a.shape}, nodata {np.isnan(a).sum()}, range {np.nanmin(a):.2f}..{np.nanmax(a):.2f} m AOD')
    return mosaic


def main():
    t0 = time.time()
    mosaic = load_mosaic()
    ny, nx = Y1 - Y0, X1 - X0
    xs = X0 + np.arange(nx) + 0.5; ys = Y0 + np.arange(ny) + 0.5
    gx, gy = np.meshgrid(xs, ys)                                        # domain cell centres, row 0 = south
    group = TransformerGroup('EPSG:32630', 'EPSG:27700', always_xy=True)
    tr = group.transformers[0]
    log(f'transform: {tr.description} (accuracy {tr.accuracy} m)')
    E, N = tr.transform((gx - REGION_OFFSET[0] + UTM_ORIGIN[0]).ravel(), (gy - REGION_OFFSET[1] + UTM_ORIGIN[1]).ravel())
    col = np.asarray(E) - 520000.5; row = 184999.5 - np.asarray(N)   # fractional pixel coords in the mosaic
    log(f'BNG extent E {E.min():.1f}..{E.max():.1f}, N {N.min():.1f}..{N.max():.1f}')
    # bilinear sample (NaN-aware: any NaN corner -> NaN)
    c0 = np.floor(col).astype(np.int64); r0 = np.floor(row).astype(np.int64)
    fc = (col - c0).astype(np.float32); fr = (row - r0).astype(np.float32)
    v00 = mosaic[r0, c0]; v01 = mosaic[r0, c0 + 1]; v10 = mosaic[r0 + 1, c0]; v11 = mosaic[r0 + 1, c0 + 1]
    dtm = ((1 - fr) * ((1 - fc) * v00 + fc * v01) + fr * ((1 - fc) * v10 + fc * v11)).reshape(ny, nx).astype(np.float32)
    del E, N, col, row, c0, r0, fc, fr, v00, v01, v10, v11
    holes = ~np.isfinite(dtm) | (dtm < PIT_AOD_M)
    n_holes = int(holes.sum())
    if n_holes:
        idx = ndimage.distance_transform_edt(holes, return_distances=False, return_indices=True)
        dtm = dtm[idx[0], idx[1]]
    log(f'DTM on grid {dtm.shape}: {dtm.min():.2f}..{dtm.max():.2f} m AOD, mean {dtm.mean():.2f}; filled holes {n_holes}')

    # core008 buildings (1 m voxel height map, same domain; rows/cols are domain metres)
    h1 = np.asarray(np.load(GEOM_1M / 'height_m.npy', mmap_mode='r')[Y0:Y1, X0:X1], np.float32)
    footprint = h1 > 0
    block = dtm + np.where(footprint, np.maximum(h1, 3.0), 0.0).astype(np.float32)   # building block >= 3 m above ground
    log(f'buildings: {footprint.mean() * 100:.2f} % of cells, height max {h1.max():.1f} m')

    # 4 m aggregates (block mean for terrain, majority for masks), [704, 768]
    def pool_mean(a): return a.reshape(ny // 4, 4, nx // 4, 4).mean(axis=(1, 3)).astype(np.float32)
    def pool_frac(m): return m.reshape(ny // 4, 4, nx // 4, 4).mean(axis=(1, 3))
    frac = pool_frac(footprint)
    footprint4 = frac >= 0.5
    dtm4 = pool_mean(dtm)
    # ground-only mean where the cell is mostly ground (avoid pulling in basements under buildings? DTM is bare earth anyway)
    bh4 = np.zeros_like(dtm4)
    hb = np.where(footprint, h1, np.nan).reshape(ny // 4, 4, nx // 4, 4)
    with np.errstate(all='ignore'):
        bh4 = np.nan_to_num(np.nanmean(hb, axis=(1, 3)), nan=0.0).astype(np.float32)
    block4 = dtm4 + np.where(footprint4, np.maximum(bh4, 3.0), 0.0).astype(np.float32)
    oy, ox = Y0 // 4, X0 // 4
    grass4 = np.load(LANDCOVER / 'grass_4m_yx.npy')[oy:oy + ny // 4, ox:ox + nx // 4]
    veg4 = np.load(LANDCOVER / 'vegetation_4m_yx.npy')[oy:oy + ny // 4, ox:ox + nx // 4]
    grass4 = grass4 & ~footprint4; veg4 = veg4 & ~footprint4
    # 1 m land cover = nearest 4 m class
    grass1 = np.repeat(np.repeat(grass4, 4, 0), 4, 1) & ~footprint
    veg1 = np.repeat(np.repeat(veg4, 4, 0), 4, 1) & ~footprint

    np.save(OUT / 'dtm_1m_yx.npy', dtm); np.save(OUT / 'bed_block_1m_yx.npy', block)
    np.save(OUT / 'footprint_1m_yx.npy', footprint); np.save(OUT / 'grass_1m_yx.npy', grass1); np.save(OUT / 'vegetation_1m_yx.npy', veg1)
    np.save(OUT / 'dtm_4m_yx.npy', dtm4); np.save(OUT / 'bed_block_4m_yx.npy', block4)
    np.save(OUT / 'footprint_4m_yx.npy', footprint4); np.save(OUT / 'building_fraction_4m_yx.npy', frac.astype(np.float32))
    np.save(OUT / 'grass_4m_yx.npy', grass4); np.save(OUT / 'vegetation_4m_yx.npy', veg4)

    # preview: DTM shaded + buildings, north up
    def to_img(a, lo, hi):
        t = np.clip((a - lo) / (hi - lo), 0, 1)
        # terrain-like ramp: green -> yellow -> brown -> white
        stops = np.array([[30, 110, 50], [180, 200, 80], [170, 120, 60], [245, 245, 245]], np.float32)
        pos = np.array([0, 0.35, 0.7, 1.0])
        rgb = np.stack([np.interp(t, pos, stops[:, k]) for k in range(3)], -1)
        return rgb
    rgb = to_img(dtm4, np.percentile(dtm4, 1), np.percentile(dtm4, 99))
    rgb[footprint4] = [60, 60, 60]; rgb[grass4] = rgb[grass4] * 0.6 + np.array([0, 90, 0]) * 0.4
    Image.fromarray(rgb[::-1].astype(np.uint8)).save(OUT / 'preview_terrain_4m.png')

    meta = {
        'date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'dtm_source': 'Environment Agency LIDAR Composite DTM 2022, 1 m, tiles TQ27ne TQ27nw TQ28se TQ28sw (environment.data.gov.uk), vertical datum ODN (m AOD)',
        'tiles_dir': str(TILES.relative_to(ROOT)),
        'transform': tr.description, 'transform_accuracy_m': tr.accuracy,
        'grid_1m': {'shape_yx': [ny, nx], 'domain_lower_xy_m': [X0, Y0], 'domain_upper_xy_m': [X1, Y1], 'row0': 'south', 'col0': 'west'},
        'grid_4m': {'shape_yx': [ny // 4, nx // 4], 'cell_m': 4, 'aggregation': 'mean DTM / building fraction >= 0.5 / mean roof height of building cells'},
        'dtm_stats_m_aod': {'min': float(dtm.min()), 'max': float(dtm.max()), 'mean': float(dtm.mean()),
                            'p1': float(np.percentile(dtm, 1)), 'p99': float(np.percentile(dtm, 99))},
        'holes_filled_1m_cells': n_holes, 'hole_rule': f'nodata or < {PIT_AOD_M} m AOD -> nearest valid cell',
        'buildings': {'source': str(GEOM_1M.relative_to(ROOT)) + '/height_m.npy', 'fraction_1m': float(footprint.mean()),
                      'block_rule': 'bed = DTM + max(roof height, 3 m) on building cells (building-block method; roofs are not flow paths)'},
        'landcover': 'grass / vegetation from ' + str(LANDCOVER.relative_to(ROOT)) + ' (4 m, core008.glb materials), nearest-4m on the 1 m grid',
        'files': sorted(p.name for p in OUT.iterdir()),
        'seconds': time.time() - t0,
    }
    (OUT / 'metadata.json').write_text(json.dumps(meta, indent=2))
    log(f'done in {time.time() - t0:.0f} s -> {OUT}')


if __name__ == '__main__':
    main()
