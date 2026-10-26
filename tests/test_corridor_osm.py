"""OSM planet ORC stripe search, OSM XML writer, eqc projection and OSM lanes (synthetic)."""

import bisect
import gzip
import math
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from traffic.corridor_sumo import calibrate, count_state, export, osm_extract, osm_net, state, tfl

ORIGIN = (-0.200473, 51.506427)


def synthetic_file(n_stripes=37, per_stripe=50):
    """Sorted (type_rank, id) rows split into stripes, like the planet ORC (SYNTHETIC)."""
    rows = [(0, 3 * i + 1) for i in range(n_stripes * per_stripe * 2 // 3)]
    rows += [(1, 7 * i + 2) for i in range(n_stripes * per_stripe // 4)]
    rows += [(2, i + 5) for i in range(n_stripes * per_stripe - len(rows))]
    stripes = [rows[k : k + per_stripe] for k in range(0, len(rows), per_stripe)]
    calls = []

    def first_keys(indices):
        calls.append(list(indices))
        return {i: stripes[i][0] if i < len(stripes) else (99, 0) for i in indices}

    return stripes, first_keys, calls


class StripeSearch(unittest.TestCase):
    def test_locate_assigns_each_key_to_its_stripe(self):
        stripes, first_keys, calls = synthetic_file()
        rows = [r for s in stripes for r in s]
        wanted = rows[::97] + [rows[0], rows[-1], (1, 9), (1, 10**9)]
        found = osm_extract.locate(wanted, len(stripes), first_keys)
        firsts = [s[0] for s in stripes]
        for key in set(wanted):
            stripe = bisect.bisect_right(firsts, key) - 1
            self.assertIn(key, found[stripe])
        self.assertEqual(sum(len(v) for v in found.values()), len(set(wanted)))
        # Every stripe with a wanted row is found, and only those (or absent-key holders).
        self.assertEqual(set(found), {bisect.bisect_right(firsts, k) - 1 for k in set(wanted)})
        # One batched first-key request per bisection level.
        self.assertLessEqual(len(calls), math.ceil(math.log2(len(stripes))) + 2)

    def test_keys_before_the_first_stripe_and_empty_input(self):
        stripes, first_keys, _ = synthetic_file()
        self.assertEqual(osm_extract.locate([(0, 0)], len(stripes), first_keys), {})
        self.assertEqual(osm_extract.locate([], len(stripes), first_keys), {})

    def test_sparse_keys_read_few_first_keys(self):
        stripes, first_keys, calls = synthetic_file(n_stripes=256)
        key = stripes[100][3]
        self.assertEqual(osm_extract.locate([key], len(stripes), first_keys), {100: [key]})
        self.assertLessEqual(sum(len(c) for c in calls), 10)

    def test_type_range(self):
        stripes, first_keys, _ = synthetic_file()
        types = [{r[0] for r in s} for s in stripes]
        lo, hi = osm_extract.type_range(1, len(stripes), first_keys)
        self.assertEqual(lo, min(i for i, t in enumerate(types) if 1 in t))
        self.assertEqual(hi, max(i for i, t in enumerate(types) if 1 in t))

    def test_keep_way(self):
        self.assertTrue(osm_extract.keep_way({"highway": "primary"}))
        self.assertTrue(osm_extract.keep_way({"highway": "busway"}))
        self.assertFalse(osm_extract.keep_way({"highway": "footway"}))
        self.assertFalse(osm_extract.keep_way({"highway": "service", "area": "yes"}))
        self.assertTrue(osm_extract.keep_way({"highway": "pedestrian", "bus": "designated"}))
        self.assertFalse(osm_extract.keep_way({"highway": "pedestrian"}))
        self.assertFalse(osm_extract.keep_way({"railway": "rail"}))


class OsmXml(unittest.TestCase):
    def test_writer_round_trip_and_determinism(self):
        nodes = {
            2: ["51.5000000", "-0.2000000", {}],
            1: [51.5, -0.21, {"highway": "traffic_signals", "name": 'A & "B"'}],
        }
        ways = {10: {"tags": {"highway": "primary", "ref": "A4"}, "nds": [1, 2]}}
        rels = [
            {
                "id": 5,
                "tags": {"type": "restriction", "restriction": "no_right_turn"},
                "members": [
                    {"type": "way", "ref": 10, "role": "from"},
                    {"type": "node", "ref": 2, "role": "via"},
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.osm.xml.gz", Path(tmp) / "b.osm.xml.gz"
            osm_extract.write_osm_xml(a, nodes, ways, rels, (-0.3, 51.4, -0.1, 51.6))
            osm_extract.write_osm_xml(b, nodes, ways, rels, (-0.3, 51.4, -0.1, 51.6))
            self.assertEqual(a.read_bytes(), b.read_bytes())
            root = ET.fromstring(gzip.decompress(a.read_bytes()))
        self.assertEqual(root.get("version"), "0.6")
        self.assertEqual([n.get("id") for n in root.findall("node")], ["1", "2"])
        n1 = root.find("node")
        self.assertEqual((n1.get("lat"), n1.get("lon")), ("51.5000000", "-0.2100000"))
        self.assertEqual(n1.find("tag[@k='name']").get("v"), 'A & "B"')
        way = root.find("way")
        self.assertEqual([nd.get("ref") for nd in way.findall("nd")], ["1", "2"])
        self.assertEqual(way.find("tag[@k='ref']").get("v"), "A4")
        rel = root.find("relation")
        self.assertEqual([m.get("role") for m in rel.findall("member")], ["from", "via"])
        self.assertEqual(root.find("bounds").get("minlat"), "51.4000000")


class Projection(unittest.TestCase):
    def synthetic_points(self):
        lon0, lat0 = ORIGIN
        return [
            (lon0 + dx, lat0 + dy)
            for dx in (-0.08, -0.03, 0.0, 0.011, 0.07)
            for dy in (-0.05, -0.002, 0.0, 0.04)
        ]

    def test_eqc_matches_enu(self):
        try:
            import pyproj
        except ImportError:
            self.skipTest("pyproj unavailable")
        enu = tfl.Enu(*ORIGIN)
        proj = pyproj.Proj(osm_net.proj_string(*ORIGIN))
        for lon, lat in self.synthetic_points():
            x, y = proj(lon, lat)
            ex, ey = enu(lon, lat)
            self.assertLess(max(abs(x - ex), abs(y - ey)), 0.05)

    def test_netconvert_osm_import_keeps_scene_coordinates(self):
        try:
            from traffic.corridor_sumo import sumo_env

            sumo_env.binary("netconvert")
            sumolib = sumo_env.sumolib()
        except Exception as exc:  # noqa: BLE001
            self.skipTest(f"SUMO unavailable: {exc}")
        enu = tfl.Enu(*ORIGIN)
        # SYNTHETIC grid of residential streets around the scene origin.
        lon0, lat0 = ORIGIN
        nodes, ways, nid = {}, {}, 1
        grid = {}
        for i in range(4):
            for j in range(4):
                grid[i, j] = nid
                nodes[nid] = [lat0 + 0.002 * j - 0.003, lon0 + 0.003 * i - 0.0045, {}]
                nid += 1
        wid = 100
        for i in range(4):
            ways[wid] = {"tags": {"highway": "residential"}, "nds": [grid[i, j] for j in range(4)]}
            ways[wid + 1] = {
                "tags": {"highway": "primary", "lanes": "4", "maxspeed": "30 mph", "ref": "A4"},
                "nds": [grid[j, i] for j in range(4)],
            }
            wid += 2
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            osm = tmp / "grid.osm.xml.gz"
            osm_extract.write_osm_xml(osm, nodes, ways, [], (-0.21, 51.50, -0.19, 51.51))
            net_path = tmp / "net.net.xml"
            sumo_env.run(
                [sumo_env.binary("netconvert"), "--osm-files", osm, "-o", net_path]
                + ["--proj", osm_net.proj_string(*ORIGIN)]
                + ["--offset.disable-normalization", "true", "--lefthand", "true"]
                + ["--osm.all-attributes", "true", "--osm.extra-attributes", "ref,lanes"]
                + ["--geometry.remove", "false", "--no-warnings", "true"]
            )
            net = sumolib.net.readNet(str(net_path))
            coords = {str(k): (v[1], v[0]) for k, v in nodes.items()}
            check = osm_net.check_coordinates(net, coords, enu, min_nodes=10)
            self.assertLessEqual(check["max_abs_deviation_m"], 0.05)
            self.assertEqual(check["location_offset"], [0.0, 0.0])
            primary = [e for e in net.getEdges() if osm_net.road_class(e.getType()) == "primary"]
            self.assertTrue(primary)
            e = primary[0]
            self.assertEqual(e.getParam("ref"), "A4")
            self.assertEqual(e.getLaneNumber(), 2)
            self.assertAlmostEqual(e.getSpeed(), 30 * 0.44704, places=1)
            self.assertTrue(count_state.lanes_tagged(e))
            res = [e for e in net.getEdges() if osm_net.road_class(e.getType()) == "residential"]
            self.assertFalse(count_state.lanes_tagged(res[0]))
            with self.assertRaises(RuntimeError):
                osm_net.check_coordinates(net, coords, enu, min_nodes=1000)


class FakeLane:
    def __init__(self, allow=True):
        self.allow = allow

    def allows(self, vclass):
        return self.allow


class FakeEdge:
    def __init__(self, params, lanes):
        self.params, self.lanes = params, lanes

    def getParam(self, key, default=None):
        return self.params.get(key, default)

    def getLanes(self):
        return self.lanes


class LanesSource(unittest.TestCase):
    def test_osm_lanes_win_over_minimum(self):
        self.assertEqual(count_state.choose_lanes("a_road_signalised", 1, True), (1, "osm"))
        self.assertEqual(count_state.choose_lanes("a_road_signalised", 3, True), (3, "osm"))
        self.assertEqual(count_state.choose_lanes("a_road_signalised", 1, False), (2, "assumed"))
        self.assertEqual(count_state.choose_lanes("minor", 1, False), (1, "assumed"))
        self.assertEqual(count_state.choose_lanes("motorway", 0, True), (3, "assumed"))

    def test_lanes_tagged(self):
        self.assertTrue(count_state.lanes_tagged(FakeEdge({"lanes": "2"}, [FakeLane()])))
        self.assertTrue(count_state.lanes_tagged(FakeEdge({"lanes:forward": "1"}, [FakeLane()])))
        self.assertFalse(count_state.lanes_tagged(FakeEdge({"ref": "A4"}, [FakeLane()])))

    def test_road_class(self):
        self.assertEqual(osm_net.road_class("highway.primary_link"), "primary")
        self.assertEqual(osm_net.road_class("highway.residential|railway.tram"), "residential")
        self.assertEqual(osm_net.road_class("secondary"), "secondary")
        self.assertEqual(osm_net.road_class(None), "")


class RefMatching(unittest.TestCase):
    def cand(self, eid, ref, cls="primary", name="", dist=10.0, heading=0.0):
        return {
            "id": eid,
            "name": name,
            "cls": cls,
            "ref": ref,
            "dist": dist,
            "heading": heading,
            "passenger": True,
        }

    def test_ref_match_wins_and_other_refs_are_skipped(self):
        cands = [
            self.cand("a315", "A315", dist=2.0),
            self.cand("a4", "A4;A315", dist=15.0),
            self.cand("none", "", dist=5.0),
        ]
        out = calibrate.choose_edge(cands, {"road_name": "A4", "road_type": "Major"}, "E", {})
        self.assertEqual((out["edge"], out["quality"]), ("a4", "ref+heading"))
        out = calibrate.choose_edge(
            cands[:1] + cands[2:], {"road_name": "A4", "road_type": "Major"}, "E", {}
        )
        self.assertEqual(out["edge"], "none")
        self.assertEqual(calibrate.refs_of("A4; a315"), {"A4", "A315"})

    def test_junction_ref_is_skipped(self):
        cands = [self.cand("x", "A3220", dist=1.0), self.cand("y", "", dist=8.0)]
        point = {"road_name": "U", "road_type": "Minor", "start_junction": "A3220"}
        out = calibrate.choose_edge(cands, point, "E", {})
        self.assertEqual(out["edge"], "y")


class DomainClip(unittest.TestCase):
    def test_clip_square(self):
        line = [(-10.0, 0.0), (0.0, 0.0), (10.0, 0.0), (10.0, 20.0)]
        self.assertEqual(state.clip_square(line, 5.0), [(-5.0, 0.0), (0.0, 0.0), (5.0, 0.0)])
        self.assertEqual(state.clip_square([(10.0, 10.0), (20.0, 20.0)], 5.0), [])
        self.assertEqual(state.clip_square(line, None), line)

    def test_fcd_samples_outside_domain_are_dropped(self):
        xml = (
            '<fcd-export><timestep time="1.00">'
            '<vehicle id="in" x="10" y="10" angle="90" type="car"/>'
            '<vehicle id="out" x="5000" y="0" angle="90" type="car"/>'
            '</timestep><timestep time="2.00">'
            '<vehicle id="in" x="4100" y="10" angle="90" type="car"/>'
            '<vehicle id="out" x="3990" y="0" angle="90" type="car"/>'
            "</timestep></fcd-export>"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fcd.xml"
            path.write_text(xml)
            rec = export.parse_fcd(path, 0, 10, half=4000.0)
        self.assertEqual([v["id"] for v in rec.vehicles], ["in", "out"])
        self.assertEqual([[s[0] for s in f] for f in rec.frames], [[0], [1]])


if __name__ == "__main__":
    unittest.main()
