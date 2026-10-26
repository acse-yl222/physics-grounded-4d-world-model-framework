"""Scene preparation for the image-to-three.js city generator."""

import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from urban_geometry.image_to_threejs import (
    check_conflicts,
    fetch_overture,
    fetch_terrain,
    prepare_scene,
    resolve_conflicts,
    terrain,
)

SQUARE_CW = [[0, 0], [0, 10], [6, 10], [6, 0], [0, 0]]


def building(id_, ring, **props):
    return {"id": id_, "geometry": {"type": "Polygon", "rings": [ring]}, **props}


class FootprintTest(unittest.TestCase):
    def test_outer_ring_is_ccw_without_closing_vertex(self):
        polys = prepare_scene.footprint({"type": "Polygon", "rings": [SQUARE_CW]})
        self.assertEqual(len(polys[0][0]), 4)
        self.assertGreater(prepare_scene.ring_area(polys[0][0]), 0)

    def test_holes_are_clockwise_and_degenerate_rings_dropped(self):
        hole = [[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]]
        sliver = [[3, 3], [3.1, 3], [3.1, 3.01], [3, 3]]
        polys = prepare_scene.footprint(
            {"type": "Polygon", "rings": [list(reversed(SQUARE_CW)), hole, sliver]}
        )
        self.assertEqual(len(polys[0]), 2)
        self.assertLess(prepare_scene.ring_area(polys[0][1]), 0)

    def test_oriented_box_of_rotated_rectangle(self):
        ring = [[0, 0], [8, 6], [5, 10], [-3, 4]]  # 10 x 5 rectangle rotated by atan(6/8)
        _, length, width = prepare_scene.obb(ring)
        self.assertAlmostEqual(length, 10, places=6)
        self.assertAlmostEqual(width, 5, places=6)


class AttributeTest(unittest.TestCase):
    def build(self, features, parts=(), claims=None):
        return {
            b["id"]: b for b in prepare_scene.build_buildings(features, list(parts), claims or {})
        }

    def test_tagged_values_are_kept_and_estimates_flagged(self):
        out = self.build(
            [
                building("tagged", SQUARE_CW, height=21.5, num_floors=6, roof_shape="flat"),
                building("floors", SQUARE_CW, num_floors=4),
                building("unknown", SQUARE_CW, **{"class": "office"}),
            ]
        )
        self.assertEqual(out["tagged"]["h"], 21.5)
        self.assertNotIn("inferred", out["tagged"])
        self.assertAlmostEqual(out["floors"]["h"], 4 * prepare_scene.FLOOR_M + 0.8)
        self.assertIn("height_from_floors", out["floors"]["inferred"])
        self.assertIn("height_from_class", out["unknown"]["inferred"])
        lo, hi = prepare_scene.DEFAULT_HEIGHT["office"]
        self.assertTrue(lo <= out["unknown"]["h"] <= hi)

    def test_estimates_are_deterministic(self):
        a = self.build([building("x", SQUARE_CW, **{"class": "residential"})])
        b = self.build([building("x", SQUARE_CW, **{"class": "residential"})])
        self.assertEqual(a, b)

    def test_narrow_house_gets_pitched_roof_and_large_block_stays_flat(self):
        big = [[0, 0], [60, 0], [60, 40], [0, 40]]
        out = self.build(
            [
                building("house", SQUARE_CW, **{"class": "terrace"}),
                building("block", big, **{"class": "terrace"}, roof_shape="gabled"),
            ]
        )
        self.assertEqual(out["house"]["roof"], "gabled")
        self.assertGreater(out["house"]["roofH"], 0)
        self.assertEqual(out["block"]["roof"], "flat")
        self.assertIn("roof_simplified", out["block"]["inferred"])

    def test_parts_claims_and_underground(self):
        part = building("p1", SQUARE_CW, building_id="main", height=30, min_height=10)
        out = self.build(
            [
                building("main", SQUARE_CW, height=12),
                building("cellar", SQUARE_CW, is_underground=True),
            ],
            parts=[part],
            claims={"main": "some_landmark"},
        )
        self.assertNotIn("cellar", out)
        self.assertEqual(out["main"]["landmark"], "some_landmark")
        self.assertEqual(out["main"]["parts"][0]["minh"], 10)
        self.assertEqual(out["main"]["parts"][0]["h"], 30)


class WaysTest(unittest.TestCase):
    def test_tunnels_skipped_bridges_lifted(self):
        line = {"type": "LineString", "line": [[0, 0], [10, 0]]}
        roads, rails = prepare_scene.build_ways(
            [
                {"geometry": line, "subtype": "road", "class": "primary"},
                {
                    "geometry": line,
                    "subtype": "road",
                    "class": "primary",
                    "road_flags": [{"values": ["is_tunnel"]}],
                },
                {
                    "geometry": line,
                    "subtype": "road",
                    "class": "trunk",
                    "level_rules": [{"value": 1}],
                },
                {"geometry": line, "subtype": "rail", "class": "subway"},
            ]
        )
        self.assertEqual([r["level"] for r in roads], [0, 1])
        self.assertEqual(roads[0]["w"], prepare_scene.ROAD_WIDTH["primary"])
        self.assertEqual(rails, [])


class ProjectionTest(unittest.TestCase):
    def test_enu_round_trip_of_domain_box(self):
        enu = fetch_overture.Enu(-0.2, 51.5)
        x0, y0, x1, y1 = enu.inverse_bbox(4000)
        self.assertAlmostEqual(enu(x1, y1)[0], 4000, delta=0.01)
        self.assertAlmostEqual(enu(x0, y0)[1], -4000, delta=0.01)


class PrepareCommandTest(unittest.TestCase):
    def test_cli_writes_scene_with_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            layers = {
                "buildings": [building("b1", SQUARE_CW, num_floors=3, name="Test Hall")],
                "building_parts": [],
                "segments": [
                    {
                        "geometry": {"type": "LineString", "line": [[0, -5], [9, -5]]},
                        "subtype": "road",
                        "class": "residential",
                    }
                ],
                "land_use": [
                    {
                        "id": "g",
                        "geometry": {"type": "Polygon", "rings": [SQUARE_CW]},
                        "class": "park",
                    }
                ],
                "land": [
                    {"id": "t", "geometry": {"type": "Point", "point": [3, 12]}, "subtype": "tree"}
                ],
                "land_cover": [],
                "water": [],
                "infrastructure": [],
            }
            index = {"release": "test", "license": "test", "layers": {}}
            for name, features in layers.items():
                (tmp / f"{name}.json").write_text(json.dumps({"features": features}))
                index["layers"][name] = {"sha256": "0" * 64}
            (tmp / "index.json").write_text(json.dumps(index))
            config = tmp / "config.json"
            config.write_text(
                json.dumps(
                    {"scene_id": "t", "origin": {"longitude": 0, "latitude": 0}, "domain_m": 100}
                )
            )
            claims = tmp / "claims.json"
            claims.write_text(json.dumps([{"id": "hall", "claims": ["b1"]}]))
            out = tmp / "scene.json"
            subprocess.run(
                [
                    sys.executable,
                    ROOT / "src/urban_geometry/image_to_threejs/prepare_scene.py",
                    config,
                    tmp,
                    out,
                    "--claims",
                    claims,
                ],
                check=True,
                capture_output=True,
            )
            scene = json.loads(out.read_text())
            self.assertEqual(scene["half_m"], 50)
            self.assertEqual(scene["buildings"][0]["landmark"], "hall")
            self.assertEqual(scene["areas"][0]["kind"], "park")
            self.assertEqual(len(scene["roads"]), 1)
            self.assertEqual(scene["trees"][0][:2], [3, 12])
            self.assertIn("conflicts_resolved", scene["source"])
            self.assertEqual(scene["source"]["overture_release"], "test")


def scene_with(buildings=(), roads=(), water=(), trees=()):
    return {
        "buildings": list(buildings),
        "roads": list(roads),
        "water": list(water),
        "trees": list(trees),
    }


def footprint_record(id_, ring, **props):
    return {"id": id_, "c": ring[0], "polys": [[ring]], "h": 10, **props}


def road(line, w=10.0, cls="residential", **props):
    return {"line": line, "cls": cls, "w": w, "bridge": False, "level": 0, **props}


BOX = lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


class ResolveConflictsTest(unittest.TestCase):
    def test_carriageway_stops_short_of_a_building_on_one_side_only(self):
        # Road along y=0, 10 m wide; a building face 3 m north of the centreline.
        scene = scene_with(
            buildings=[footprint_record("b", BOX(0, 3, 40, 20))],
            roads=[road([[0, 0], [40, 0]])],
        )
        counts = resolve_conflicts.resolve(scene)
        r = scene["roads"][0]
        self.assertEqual(counts["roads_narrowed"], 1)
        mid = len(r["line"]) // 2
        self.assertAlmostEqual(r["wl"][mid], 3 - resolve_conflicts.CLEARANCE_M, places=2)
        self.assertEqual(r["wr"][mid], 5.0)
        self.assertLessEqual(r["pl"][mid], 3.0)
        self.assertEqual(r["pr"][mid], 5.0 + resolve_conflicts.PAVEMENT_M)
        self.assertEqual(check_conflicts.check(scene)["building_on_road"], [])

    def test_passage_under_building_and_crossing_water_are_marked(self):
        scene = scene_with(
            buildings=[footprint_record("arch", BOX(9, -6, 22, 6))],
            roads=[road([[0, 0], [40, 0]], w=4.0, cls="footway")],
            water=[{"kind": "water", "poly": [BOX(25, -20, 39, 20)]}],
        )
        resolve_conflicts.resolve(scene)
        r = scene["roads"][0]
        # Densified every 8 m: segment midpoints at x = 4, 12, 20, 28, 36.
        self.assertEqual(r["covered"], [1, 2])
        self.assertEqual(r["wet"], [3, 4])
        self.assertNotIn("wl", r)  # footways keep their width

    def test_houseboats_float_and_trees_leave_buildings_water_and_roads(self):
        scene = scene_with(
            buildings=[
                footprint_record("boat", BOX(50, 50, 70, 54), cls="houseboat"),
                footprint_record("house", BOX(100, 100, 110, 110)),
            ],
            roads=[road([[0, -50], [40, -50]])],
            water=[{"kind": "water", "poly": [BOX(40, 40, 80, 60)]}],
            trees=[[105, 105, 0.1], [45, 45, 0.2], [20, -49, 0.3], [20, -80, 0.4]],
        )
        counts = resolve_conflicts.resolve(scene)
        self.assertTrue(scene["buildings"][0]["vessel"])
        self.assertNotIn("vessel", scene["buildings"][1])
        self.assertEqual(counts["trees_dropped_in_buildings"], 1)
        self.assertEqual(counts["trees_dropped_in_water"], 1)
        self.assertEqual(counts["trees_moved_to_kerb"], 1)
        moved, kept = scene["trees"]
        self.assertGreater(moved[1], -50 + 5)
        self.assertEqual(kept, [20, -80, 0.4])


class TerrainSourceTest(unittest.TestCase):
    def test_terrarium_decoding_matches_the_documented_example(self):
        # docs/formats.md: 2523.266 m encodes as rgb(137, 219, 68) -> 2523.265625.
        rgb = np.array([[[137, 219, 68], [128, 0, 0]]], dtype=np.uint8)
        h = fetch_terrain.decode_terrarium(rgb)
        self.assertAlmostEqual(float(h[0, 0]), 2523.265625, places=4)
        self.assertEqual(float(h[0, 1]), 0.0)

    def test_tiles_cover_the_domain_and_resampling_follows_web_mercator(self):
        enu = fetch_overture.Enu(-0.200473, 51.506427)
        z = 15
        xr, yr = fetch_terrain.tile_range(enu, 4110, z)
        self.assertEqual((len(xr), len(yr)), (12, 12))  # ~3 m pixels, 8.2 km square
        # A mosaic whose value is the pixel-centre x coordinate within the mosaic.
        cols = np.arange(len(xr) * fetch_terrain.TILE) + 0.5
        mosaic = np.tile(cols, (len(yr) * fetch_terrain.TILE, 1)).astype(np.float64)
        xs = np.array([-4100.0, 0.0, 2500.0])
        ys = np.array([-4100.0, 3000.0])
        out = fetch_terrain.resample(mosaic, xr[0], yr[0], enu, xs, ys, z)
        self.assertEqual(out.shape, (2, 3))
        for i, x in enumerate(xs):
            lon = enu.lon0 + x / enu.kx
            px, _ = fetch_terrain.mercator_px(lon, enu.lat0, z)
            local = float(px) - xr[0] * fetch_terrain.TILE
            self.assertAlmostEqual(float(out[0, i]), local, delta=0.01)
        # Rows run south to north: pixel y grows southwards.
        rows = np.arange(len(yr) * fetch_terrain.TILE) + 0.5
        mosaic_y = np.tile(rows[:, None], (1, len(xr) * fetch_terrain.TILE))
        out_y = fetch_terrain.resample(mosaic_y, xr[0], yr[0], enu, xs, ys, z)
        self.assertGreater(out_y[0, 0], out_y[1, 0])


def plane(x, y):
    return 12.0 + 0.03 * np.asarray(x) - 0.01 * np.asarray(y)


def dem_fixture(half=120.0, dx=5.0):
    xs = fetch_terrain.grid_axis(half, dx)
    xx, yy = np.meshgrid(xs, xs)
    index = {"x0": float(xs[0]), "y0": float(xs[0]), "dx": dx}
    return plane(xx, yy).astype(np.float32), index


class SceneTerrainTest(unittest.TestCase):
    def test_encoding_round_trip_and_size(self):
        dem, index = dem_fixture()
        x0, y0, dx, values = terrain.scene_grid(dem, index, 10.0, 100.0)
        self.assertEqual((x0, dx, values.shape), (-100.0, 10.0, (21, 21)))
        rec = terrain.encode(values, x0, y0, dx)
        self.assertEqual(rec["encoding"], "int16le-base64")
        self.assertEqual(len(rec["z"]), 4 * math.ceil(2 * 21 * 21 / 3))
        back = terrain.decode(rec)
        self.assertLessEqual(float(np.abs(back - values).max()), 0.005 + 1e-9)
        # The [1, 2, 1] filter and decimation keep a plane (inside the edge nodes).
        xs = x0 + dx * np.arange(21)
        xx, yy = np.meshgrid(xs, xs)
        self.assertLess(float(np.abs(back - plane(xx, yy))[1:-1, 1:-1].max()), 0.006)
        sample = terrain.Sampler(rec)
        self.assertAlmostEqual(float(sample(3.3, -7.7)), float(plane(3.3, -7.7)), delta=0.006)

    def test_ground_levels_of_buildings_water_and_vessels(self):
        dem, index = dem_fixture()
        rec = terrain.encode(*terrain.scene_grid(dem, index, 10.0, 100.0)[3:], -100.0, -100.0, 10.0)
        scene = {
            "buildings": [
                footprint_record("b", BOX(0, 0, 40, 20)),
                {**footprint_record("boat", BOX(-60, -60, -50, -56)), "vessel": True},
                footprint_record("terrace", BOX(-90, 10, 90, 18)),
            ],
            "water": [
                {"kind": "river", "poly": [BOX(-80, -80, -40, -40)]},
                {"kind": "river", "poly": [BOX(-40, -80, 0, -40)]},  # shares an edge
                {"kind": "pond", "poly": [BOX(50, 50, 70, 70)]},
            ],
        }
        stats = terrain.apply_terrain(scene, rec)
        b, boat, row = scene["buildings"]
        # A 180 m terrace on the 3 % slope follows a plane nowhere above the terrain.
        self.assertNotIn("ground_plane", b)  # 1.4 m of ground spread stays level
        z0, gx, gy = row["ground_plane"]
        self.assertAlmostEqual(gx, 0.03, delta=0.002)
        self.assertAlmostEqual(gy, -0.01, delta=0.002)
        self.assertAlmostEqual(z0, float(plane(*row["c"])), delta=0.05)
        self.assertLessEqual(z0, float(plane(*row["c"])) + 0.01)
        self.assertAlmostEqual(b["ground_z"], float(plane(0, 20)), delta=0.02)
        self.assertAlmostEqual(b["ground_max"], float(plane(40, 0)), delta=0.02)
        self.assertNotIn("ground_z", scene["water"][0])
        river, river2, pond = (w["level"] for w in scene["water"])
        self.assertEqual(river, river2)
        self.assertLess(river, float(plane(-40, -60)))  # low percentile of the surface
        self.assertGreater(pond, float(plane(50, 70)) - 0.01)
        self.assertEqual(boat["ground_z"], river)
        self.assertEqual(stats["water_levels"], 3)
        self.assertEqual(stats["sloped_buildings"], 1)
        self.assertIn("terrain", scene)

    def test_prepare_cli_adds_terrain_only_when_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            layers = {
                "buildings": [building("b1", SQUARE_CW, num_floors=3)],
                "building_parts": [],
                "segments": [],
                "land_use": [],
                "land": [],
                "land_cover": [],
                "water": [],
                "infrastructure": [],
            }
            index = {"release": "test", "license": "test", "layers": {}}
            for name, features in layers.items():
                (tmp / f"{name}.json").write_text(json.dumps({"features": features}))
                index["layers"][name] = {"sha256": "0" * 64}
            (tmp / "index.json").write_text(json.dumps(index))
            config = tmp / "config.json"
            cfg = {"scene_id": "t", "origin": {"longitude": 0, "latitude": 0}, "domain_m": 200}
            cfg["terrain"] = {"scene_grid_m": 10.0, "half_m": 110}
            config.write_text(json.dumps(cfg))
            dem, grid = dem_fixture()
            np.save(tmp / "dem.npy", dem)
            src = {"name": "fixture", "zoom": 15, "imagery_sources": ["uk_lidar"]}
            src |= {"attribution": ["fixture"], "license": "fixture"}
            dem_index = {**grid, "file": "dem.npy", "shape": list(dem.shape), "sha256": "1" * 64}
            dem_index |= {"vertical_datum": "fixture", "source": src}
            (tmp / "dem.json").write_text(json.dumps(dem_index))
            script = ROOT / "src/urban_geometry/image_to_threejs/prepare_scene.py"
            for extra, name in (([], "flat.json"), (["--terrain", tmp / "dem.json"], "hill.json")):
                subprocess.run(
                    [sys.executable, script, config, tmp, tmp / name, *extra],
                    check=True,
                    capture_output=True,
                )
            flat = json.loads((tmp / "flat.json").read_text())
            hill = json.loads((tmp / "hill.json").read_text())
            self.assertNotIn("terrain", flat)
            self.assertNotIn("ground_z", flat["buildings"][0])
            self.assertEqual(hill["terrain"]["nx"], 23)
            self.assertEqual(hill["source"]["terrain"]["grid"], [23, 23])
            self.assertAlmostEqual(
                hill["buildings"][0]["ground_z"], float(plane(0, 10)), delta=0.02
            )
            # Apart from terrain fields the scenes agree.
            for key in ("terrain",):
                hill.pop(key)
            hill["source"].pop("terrain")
            for b in hill["buildings"]:
                b.pop("ground_z")
                b.pop("ground_max")
                b.pop("ground_plane", None)
            self.assertEqual(hill, flat)


if __name__ == "__main__":
    unittest.main()
