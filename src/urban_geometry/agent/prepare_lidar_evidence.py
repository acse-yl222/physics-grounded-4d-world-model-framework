"""Read-only native-resolution roof evidence; never mutates authored geometry."""

from pathlib import Path as _UwmPath
import sys as _uwm_sys

_uwm_sys.path.insert(
    0, str(next(p for p in _UwmPath(__file__).resolve().parents if (p / "common").is_dir()))
)
from common.layout import repo_root, agent_src, authoring_path
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import from_bounds, transform as window_transform
from rasterio.features import geometry_mask
from pyproj.transformer import TransformerGroup
from pyproj import datadir
from shapely.geometry import Polygon, mapping
from shapely.ops import transform
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = authoring_path()
OUT = ROOT / "references/phase5_lidar"
datadir.append_data_dir(str(OUT))
g = json.loads((ROOT / "geometry.json").read_text())
ox, oy = g["origin_projected_m"]
group = TransformerGroup("EPSG:32630", "EPSG:27700", always_xy=True)
t = group.transformers[0]


def convert(x, y, z=None):
    return t.transform(np.asarray(x) + ox, np.asarray(y) + oy)


features = []
for b in g["buildings"]:
    ps = [transform(convert, Polygon(v["outer"], v.get("holes", []))) for v in b["geometry"]]
    features.append((b, ps))
selected = {
    "way-27765411",
    "way-24436446",
    "way-372860405",
    "way-27765400",
    "relation-29795",
    "way-4959880",
    "way-23734116",
}
results = []
with (
    rasterio.open(OUT / "TQ27ne_FZ_DSM_1m.tif") as dsm,
    rasterio.open(OUT / "TQ27ne_DTM_1m.tif") as dtm,
):
    assert dsm.transform == dtm.transform and dsm.crs == dtm.crs
    for b, ps in features:
        if not ps:
            results.append(
                {
                    "id": b["id"],
                    "name": b.get("name"),
                    "status": "assembly_only_no_independent_footprint",
                }
            )
            continue
        bounds = (
            min(p.bounds[0] for p in ps) - 8,
            min(p.bounds[1] for p in ps) - 8,
            max(p.bounds[2] for p in ps) + 8,
            max(p.bounds[3] for p in ps) + 8,
        )
        win = from_bounds(*bounds, transform=dsm.transform).round_offsets().round_lengths()
        a = dsm.read(1, window=win, masked=True)
        ground = dtm.read(1, window=win, masked=True)
        h = (a - ground).filled(np.nan)
        wt = window_transform(win, dsm.transform)
        inner = [p.buffer(-1.5) for p in ps if not p.buffer(-1.5).is_empty]
        mask = (
            geometry_mask([mapping(p) for p in inner], out_shape=h.shape, transform=wt, invert=True)
            if inner
            else np.zeros(h.shape, dtype=bool)
        )
        vals = h[mask & np.isfinite(h)]
        row = {
            "id": b["id"],
            "name": b.get("name"),
            "inset_m": 1.5,
            "sample_count": len(vals),
            "height_relative_to_local_DTM_m": dict(
                zip(
                    ["p10", "p25", "p50", "p75", "p90", "p95", "p99"],
                    map(float, np.percentile(vals, [10, 25, 50, 75, 90, 95, 99])),
                )
            )
            if len(vals)
            else {},
            "existing_model_height_m": b["height_m"],
            "status": "raster_statistics_only_not_geometry_accepted",
        }
        results.append(row)
        if b["id"] in selected:
            dest = OUT / b["id"]
            dest.mkdir(exist_ok=True)
            prof = dsm.profile.copy()
            prof.update(
                height=h.shape[0],
                width=h.shape[1],
                transform=wt,
                nodata=np.nan,
                dtype="float32",
                compress="deflate",
            )
            with rasterio.open(dest / "relative_height_1m.tif", "w", **prof) as dst:
                dst.write(h.astype("float32"), 1)
            fig, ax = plt.subplots(figsize=(10, 10))
            extent = [wt.c, wt.c + h.shape[1], wt.f - h.shape[0], wt.f]
            im = ax.imshow(
                h, extent=extent, vmin=0, vmax=55, cmap="terrain", interpolation="nearest"
            )
            for p in ps:
                x, y = p.exterior.xy
                ax.plot(x, y, "r-", lw=1)
                for ring in p.interiors:
                    ax.plot(*ring.xy, "r-", lw=1)
            ax.ticklabel_format(useOffset=False, style="plain")
            ax.set_title(
                f"{b.get('name', b['id'])}\nEA 2022 composite DSM minus DTM, native 1m; red = OSM footprint"
            )
            ax.set_xlabel("British National Grid easting (m)")
            ax.set_ylabel("Northing (m)")
            fig.colorbar(im, ax=ax, label="Surface height above local terrain (m)")
            fig.tight_layout()
            fig.savefig(dest / "roof_evidence.png", dpi=160)
            plt.close(fig)
            (dest / "statistics.json").write_text(json.dumps(row, indent=2) + "\n")
report = {
    "source": "EA 2022 1m first-return DSM and DTM TQ27ne",
    "transformation": t.description,
    "transformation_reported_accuracy_m": t.accuracy,
    "best_transform_available": group.best_available,
    "resolution_m": 1,
    "vertical_basis": "DSM minus DTM, both ODN; not absolute scene Z",
    "cautions": [
        "Composite acquisition dates vary; roof changes after survey unknown.",
        "DSM includes vegetation, rooftop plant and chimneys; statistics are not automatic building heights.",
        "Footprints may be offset or include multiple heights; samples inset 1.5m.",
        "Source resolution and transformation accuracy do not certify model accuracy.",
    ],
    "buildings": results,
}
(OUT / "building_height_evidence.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "buildings"}, indent=2))
print("records", len(results))
