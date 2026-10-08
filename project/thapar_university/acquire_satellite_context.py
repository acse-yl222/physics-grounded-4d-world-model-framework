"""Retain one native-resolution Sentinel crop; never infer facade detail from it."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--item', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    catalog = json.loads(args.catalog.read_text())
    item = next(feature for feature in catalog['features'] if feature['id'] == args.item)
    bbox = json.loads((root / 'geometry/reconstruction_v2/region.json').read_text())['bbox_wgs84']
    output = root / 'input/reconstruction_v2/satellite' / args.item
    output.mkdir(parents=True, exist_ok=False)
    href = item['assets']['visual']['href']
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', GDAL_HTTP_TIMEOUT='30', GDAL_HTTP_MAX_RETRY='0'):
        with rasterio.open(href) as source:
            projected = transform_bounds('EPSG:4326', source.crs, *bbox)
            window = from_bounds(*projected, transform=source.transform).round_offsets().round_lengths()
            pixels = source.read(window=window)
            valid = source.dataset_mask(window=window)
            profile = source.profile.copy()
            profile.update(width=pixels.shape[2], height=pixels.shape[1], transform=source.window_transform(window))
            with rasterio.open(output / 'true_color.tif', 'w', **profile) as target:
                target.write(pixels)
                target.write_mask(valid)
            spacing = list(source.res)
    Image.fromarray(np.moveaxis(pixels, 0, -1)).save(output / 'true_color.png')
    (output / 'stac_item.json').write_text(json.dumps(item, indent=2))
    report = {
        'item': item['id'], 'source_url': href,
        'capture_date': item['properties']['datetime'], 'bbox_wgs84': bbox,
        'native_pixel_spacing_m': spacing, 'shape': list(pixels.shape),
        'valid_fraction': float(np.count_nonzero(valid) / valid.size),
        'attribution': 'Contains modified Copernicus Sentinel data (2025); COG supplied through Earth Search / Element 84.',
        'license_url': 'https://dataspace.copernicus.eu/terms-and-conditions',
        'processing': 'Native-resolution AOI window only; no super-resolution, enhancement or invented detail.',
        'limitations': 'Regional land-cover context only. Cannot resolve facade windows, individual trees, roof equipment or building heights.',
        'actually_inspected': False,
        'sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in output.iterdir() if path.is_file()},
    }
    (output / 'provenance.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
