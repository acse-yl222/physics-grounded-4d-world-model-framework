"""Scene preparation for the image-to-three.js city generator."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from urban_geometry.image_to_threejs import (
    check_conflicts,
    fetch_overture,
    prepare_scene,
    resolve_conflicts,
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


if __name__ == "__main__":
    unittest.main()
