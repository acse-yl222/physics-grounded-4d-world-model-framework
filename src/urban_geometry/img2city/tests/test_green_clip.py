"""Regression tests for the phantom-forest bug (2026-08-20): Overpass returns
FULL way geometry for anything touching the query bbox, so the green layer
must clip polygons/hedges to the model extent before rendering or tree
in-fill (Kensington Gardens once dragged 6,923 trees a kilometre outside)."""
import pytest

pytest.importorskip("shapely")          # used lazily inside green_to_local
sa = pytest.importorskip("img2city.scene.assets")

ANCHOR = {"lat0": 51.5, "lon0": -0.17,
          "bbox": [51.4977, -0.1736, 51.5023, -0.1664]}   # ~500 x 500 m


def _el(eid, coords, tags):
    return {"id": eid, "tags": tags,
            "geometry": [{"lat": la, "lon": lo} for la, lo in coords]}


def _bounds(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def test_oversized_park_is_clipped_to_model_extent():
    # park whose polygon extends ~1 km north of the bbox (the Kensington case)
    park = _el(1, [(51.5015, -0.1730), (51.5120, -0.1730), (51.5120, -0.1670),
                   (51.5015, -0.1670), (51.5015, -0.1730)],
               {"leisure": "park", "name": "Big Park"})
    areas, _ = sa.green_to_local([park], ANCHOR)
    assert areas, "clipped park must survive as an in-extent strip"
    x0, y0, x1, y1 = sa._bbox_ext(ANCHOR)
    for a in areas:
        bx0, by0, bx1, by1 = _bounds(a["pts"])
        assert bx0 >= x0 - 1e-6 and bx1 <= x1 + 1e-6
        assert by0 >= y0 - 1e-6 and by1 <= y1 + 1e-6


def test_inside_polygon_survives_intact():
    lawn = _el(2, [(51.4990, -0.1710), (51.4990, -0.1690), (51.5005, -0.1690),
                   (51.5005, -0.1710), (51.4990, -0.1710)],
               {"leisure": "garden"})
    areas, _ = sa.green_to_local([lawn], ANCHOR)
    assert len(areas) == 1
    assert areas[0]["kind"] == "garden"
    assert len(areas[0]["pts"]) >= 4


def test_infill_trees_stay_inside_extent():
    park = _el(3, [(51.5015, -0.1730), (51.5120, -0.1730), (51.5120, -0.1670),
                   (51.5015, -0.1670), (51.5015, -0.1730)],
               {"leisure": "park"})
    areas, _ = sa.green_to_local([park], ANCHOR)
    trees = sa.scatter_park_trees(areas, [], [])
    x0, y0, x1, y1 = sa._bbox_ext(ANCHOR)
    assert trees, "a park strip should still receive some in-fill"
    for t in trees:
        tx, ty = (t["x"], t["y"]) if isinstance(t, dict) else (t[0], t[1])
        assert x0 - 1e-6 <= tx <= x1 + 1e-6
        assert y0 - 1e-6 <= ty <= y1 + 1e-6


def test_hedge_polyline_clipped_not_dropped():
    hedge = _el(4, [(51.5000, -0.1800), (51.5000, -0.1600)],   # crosses E-W
                {"barrier": "hedge"})
    _, hedges = sa.green_to_local([hedge], ANCHOR)
    assert hedges
    x0, y0, x1, y1 = sa._bbox_ext(ANCHOR)
    for h in hedges:
        for px, py in h["pts"]:
            assert x0 - 1e-6 <= px <= x1 + 1e-6
