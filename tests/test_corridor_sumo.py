"""Overture -> SUMO plain XML, TfL parsing and traffic export (small synthetic fixtures)."""

import json
import math
import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from common.contract import validate
from traffic.corridor_sumo import export, overture_net, tfl

FIXTURE = ROOT / "tests/fixtures/corridor_sumo/tfl_synthetic"


def connector(cid, x, y):
    return {"id": cid, "geometry": {"type": "Point", "point": [x, y]}}


def segment(sid, cls, line, conns, **props):
    return {
        "id": sid,
        "subtype": "road",
        "class": cls,
        "geometry": {"type": "LineString", "line": line},
        "connectors": [{"connector_id": c, "at": a} for c, a in conns],
        **props,
    }


# Synthetic network: a two-way residential street A-B-C, a one-way primary C-D with a
# 20 mph limit, a bus-only link, a private service road, a footway, and a primary that
# leaves the domain (no connector at its far end).
CONNECTORS = [
    connector("A", 0, 0),
    connector("B", 100, 0),
    connector("C", 200, 0),
    connector("D", 200, 100),
    connector("E", 300, 0),
    connector("F", 200, -100),
]
SEGMENTS = [
    segment(
        "s-res",
        "residential",
        [[0, 0], [50, 0], [100, 0], [200, 0]],
        [("A", 0), ("B", 0.5), ("C", 1)],
        name="Synthetic Street",
    ),
    segment(
        "s-oneway",
        "primary",
        [[200, 0], [200, 100]],
        [("C", 0), ("D", 1)],
        access_restrictions=[{"access_type": "denied", "when": {"heading": "backward"}}],
        speed_limits=[{"max_speed": {"value": 20, "unit": "mph"}}],
    ),
    segment(
        "s-bus",
        "secondary",
        [[200, 0], [300, 0]],
        [("C", 0), ("E", 1)],
        access_restrictions=[
            {"access_type": "denied"},
            {"access_type": "allowed", "when": {"mode": ["bus"]}},
        ],
    ),
    segment(
        "s-private",
        "service",
        [[200, 0], [200, -100]],
        [("C", 0), ("F", 1)],
        access_restrictions=[{"access_type": "allowed", "when": {"recognized": ["as_private"]}}],
    ),
    segment("s-foot", "footway", [[0, 0], [0, 50]], [("A", 0)]),
    segment("s-out", "primary", [[300, 0], [400, 0]], [("E", 0)]),
    segment("s-tertiary", "tertiary", [[200, 0], [150, -60]], [("C", 0)]),
]


class OvertureToPlainXml(unittest.TestCase):
    def setUp(self):
        self.net = overture_net.build(SEGMENTS, CONNECTORS)
        self.edges = {e["id"]: e for e in self.net.edges}

    def test_split_at_connectors_and_directions(self):
        # Residential street is split at B into two pieces, each in both directions.
        res = [e for e in self.net.edges if e["overture_id"] == "s-res"]
        self.assertEqual(len(res), 4)
        a_node = next(n for n, xy in self.net.nodes.items() if xy == (0.0, 0.0))
        b_node = next(n for n, xy in self.net.nodes.items() if xy == (100.0, 0.0))
        forward = [e for e in res if e["from"] == a_node]
        self.assertEqual(forward[0]["to"], b_node)
        self.assertEqual(forward[0]["shape"], [(0, 0), (50, 0), (100, 0)])
        self.assertEqual(forward[0]["name"], "Synthetic Street")
        backward = next(e for e in res if e["to"] == a_node)
        self.assertTrue(backward["id"].startswith("-"))
        self.assertEqual(backward["shape"], [(100, 0), (50, 0), (0, 0)])

    def test_one_way_speed_and_lanes(self):
        oneway = [e for e in self.net.edges if e["overture_id"] == "s-oneway"]
        self.assertEqual(len(oneway), 1)
        self.assertTrue(oneway[0]["one_way"])
        self.assertAlmostEqual(oneway[0]["speed"], 8.94, places=2)  # 20 mph
        self.assertEqual(oneway[0]["numLanes"], 2)  # one-way primary default
        self.assertEqual(oneway[0]["shape"][0], (200, 0))

    def test_access_bus_only_private_and_classes(self):
        bus = [e for e in self.net.edges if e["overture_id"] == "s-bus"]
        self.assertEqual(len(bus), 2)
        self.assertTrue(all(e["allow"] == ["bus"] for e in bus))
        ids = {e["overture_id"] for e in self.net.edges}
        self.assertNotIn("s-private", ids)
        self.assertNotIn("s-foot", ids)
        self.assertEqual(self.net.stats["skipped_class"], 1)
        self.assertEqual(self.net.stats["skipped_access"], 1)

    def test_boundary_node_and_tls(self):
        out = [e for e in self.net.edges if e["overture_id"] == "s-out"]
        self.assertEqual(len(out), 2)
        far = [n for n, xy in self.net.nodes.items() if xy == (400.0, 0.0)]
        self.assertEqual(len(far), 1)
        # C joins primary, secondary and tertiary pieces (>= 3 major) -> signalised.
        c_node = next(n for n, xy in self.net.nodes.items() if xy == (200.0, 0.0))
        self.assertIn(c_node, self.net.tls)
        self.assertEqual(len(self.net.tls), 1)

    def test_loop_segment_gets_intermediate_node(self):
        loop = segment(
            "s-loop", "residential", [[0, 0], [10, 10], [20, 0], [0, 0]], [("A", 0), ("A", 1)]
        )
        net = overture_net.build([loop], CONNECTORS[:1])
        self.assertEqual(len(net.nodes), 2)
        self.assertEqual(len(net.edges), 4)
        self.assertTrue(all(e["from"] != e["to"] for e in net.edges))

    def test_connector_between_vertices_is_inserted(self):
        seg = segment("s-mid", "residential", [[0, 0], [100, 0]], [("A", 0), ("M", 0.3), ("B", 1)])
        net = overture_net.build([seg], [*CONNECTORS[:2], connector("M", 30, 0)])
        shapes = sorted(e["shape"] for e in net.edges if not e["id"].startswith("-"))
        self.assertEqual(shapes, [[(0, 0), (30, 0)], [(30, 0), (100, 0)]])

    def test_write_plain_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            nod, edg = Path(tmp) / "n.nod.xml", Path(tmp) / "e.edg.xml"
            overture_net.write_plain_xml(self.net, nod, edg)
            nodes = {n.get("id"): n for n in ET.parse(nod).getroot()}
            self.assertEqual(len(nodes), len(self.net.nodes))
            self.assertEqual(sum(n.get("type") == "traffic_light" for n in nodes.values()), 1)
            edges = {e.get("id"): e for e in ET.parse(edg).getroot()}
            oneway = next(e for e in self.net.edges if e["overture_id"] == "s-oneway")
            el = edges[oneway["id"]]
            self.assertEqual(el.get("spreadType"), "center")
            self.assertEqual(el.get("shape"), "200.00,0.00 200.00,100.00")
            self.assertEqual(el.find("param").get("value"), "s-oneway")
            self.assertEqual(el.get("allow"), "passenger taxi bus")

    def test_netconvert_keeps_scene_coordinates(self):
        try:
            from traffic.corridor_sumo import network, sumo_env

            sumo_env.binary("netconvert")
        except Exception as exc:  # noqa: BLE001
            self.skipTest(f"SUMO unavailable: {exc}")
        with tempfile.TemporaryDirectory() as tmp:
            nod, edg = Path(tmp) / "n.nod.xml", Path(tmp) / "e.edg.xml"
            overture_net.write_plain_xml(self.net, nod, edg)
            net_path = Path(tmp) / "net.net.xml"
            sumo_env.run(
                [
                    sumo_env.binary("netconvert"),
                    "--node-files",
                    nod,
                    "--edge-files",
                    edg,
                    "-o",
                    net_path,
                    "--offset.disable-normalization",
                    "true",
                    "--lefthand",
                    "true",
                    "--no-warnings",
                    "true",
                ]
            )
            stats = network.describe(net_path, self.net)
            self.assertEqual(stats["location_offset"], [0.0, 0.0])
            self.assertEqual(stats["coordinate_check"]["max_abs_deviation_m"], 0.0)


class TflParsing(unittest.TestCase):
    """Parsing of TfL-shaped responses using a SYNTHETIC fixture (not TfL data)."""

    def setUp(self):
        self.sequence = json.loads((FIXTURE / "route_sequence/syn1_outbound.json").read_text())

    def test_fixture_is_marked_synthetic(self):
        for path in FIXTURE.rglob("*.json"):
            self.assertIn("SYNTHETIC", json.loads(path.read_text())["_synthetic"], path)

    def test_route_sequence(self):
        variants = tfl.parse_route_sequence(self.sequence)
        self.assertEqual([v["service_type"] for v in variants], ["Regular", "Night"])
        main = variants[0]
        self.assertEqual(main["line"], "syn1")
        self.assertEqual([s["id"] for s in main["stops"]], ["SYNTH0001", "SYNTH0002", "SYNTH0003"])
        self.assertEqual(len(main["polyline"]), 14)  # the lineString near the stops
        self.assertEqual(tfl.first_stop(self.sequence), "SYNTH0001")

    def test_line_strings(self):
        lines = tfl.parse_line_strings(self.sequence)
        self.assertEqual([len(line) for line in lines], [2, 14])
        self.assertEqual(lines[0][0], (0.0, 51.0))

    def test_headway(self):
        timetable = json.loads((FIXTURE / "timetable/syn1_outbound.json").read_text())
        result = tfl.parse_headway(timetable, "Monday to Friday", 8)
        self.assertEqual(result["headway_s"], 600)
        self.assertEqual(result["schedule"], "Monday to Friday")
        freq = json.loads((FIXTURE / "timetable/frequency_only.json").read_text())
        self.assertEqual(tfl.parse_headway(freq, "Monday to Friday", 8)["headway_s"], 480)
        self.assertIsNone(tfl.parse_headway(freq, "Monday to Friday", 12)["headway_s"])
        self.assertIsNone(tfl.parse_headway({}, "Monday to Friday", 8)["headway_s"])

    def test_projection_and_stop_grid(self):
        enu = tfl.Enu(-0.200473, 51.506427)
        lon, lat = enu.inverse(1234.5, -678.9)
        x, y = enu(lon, lat)
        self.assertAlmostEqual(x, 1234.5, places=6)
        self.assertAlmostEqual(y, -678.9, places=6)
        centres = tfl.stop_grid(4000, 1000)
        for corner in [(-4000, -4000), (4000, 4000), (-4000, 4000), (0, 0)]:
            self.assertTrue(any(math.dist(corner, c) <= 1000 for c in centres))

    def test_missing_cache_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(tfl.load_cache(Path(tmp) / "tfl"))


FCD = """<fcd-export>
  <timestep time="299.00"><vehicle id="car_0" x="1" y="1" angle="90" type="car" speed="5"/></timestep>
  <timestep time="300.00">
    <vehicle id="car_0" x="10.0" y="0.0" angle="90.00" type="car" speed="10"/>
    <vehicle id="bus_syn00.0" x="0.0" y="50.0" angle="0.00" type="bus" speed="8"/>
  </timestep>
  <timestep time="301.00">
    <vehicle id="car_0" x="20.0" y="0.0" angle="90.00" type="car" speed="10"/>
    <vehicle id="bus_syn00.0" x="0.0" y="58.0" angle="0.00" type="bus" speed="8"/>
    <vehicle id="taxi_3" x="-5.0" y="-5.0" angle="225.00" type="taxi" speed="3"/>
  </timestep>
  <timestep time="302.00">
    <vehicle id="taxi_3" x="-7.0" y="-7.0" angle="225.00" type="taxi" speed="3"/>
  </timestep>
</fcd-export>
"""


class TrafficExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "fcd.xml").write_text(FCD)
        self.rec = export.parse_fcd(self.dir / "fcd.xml", 300, 302)

    def tearDown(self):
        self.tmp.cleanup()

    def test_heading_convention(self):
        self.assertAlmostEqual(export.heading_from_sumo_angle(90), 0.0)  # east
        self.assertAlmostEqual(export.heading_from_sumo_angle(0), math.pi / 2)  # north
        self.assertAlmostEqual(export.heading_from_sumo_angle(180), -math.pi / 2)  # south
        self.assertAlmostEqual(abs(export.heading_from_sumo_angle(270)), math.pi)  # west
        self.assertAlmostEqual(export.heading_from_sumo_angle(225), -3 * math.pi / 4)

    def test_parse_window_and_types(self):
        self.assertEqual(self.rec.times, [300.0, 301.0, 302.0])
        self.assertEqual(
            self.rec.vehicles,
            [
                {"id": "car_0", "type": "car"},
                {"id": "bus_syn00.0", "type": "bus"},
                {"id": "taxi_3", "type": "taxi"},
            ],
        )
        self.assertEqual([len(f) for f in self.rec.frames], [2, 3, 1])
        check = export.heading_check(self.rec, min_step_m=1.0)
        self.assertEqual(check["samples"], 3)
        self.assertLess(check["median_deg"], 1e-6)

    def test_binary_round_trip(self):
        path = self.dir / "traffic.bin"
        size = export.write_binary(self.rec, path)
        self.assertEqual(size, 4 * 3 + 16 * 6)
        self.assertEqual(size, export.bin_size(self.rec))
        raw = path.read_bytes()
        self.assertEqual(struct.unpack_from("<I", raw, 0)[0], 2)
        self.assertEqual(struct.unpack_from("<Ifff", raw, 4), (0, 10.0, 0.0, 0.0))
        frames = export.read_binary(path, 3)
        self.assertEqual(frames[1]["i"].tolist(), [0, 1, 2])
        self.assertEqual(frames[1]["y"].tolist(), [0.0, 58.0, -5.0])
        self.assertAlmostEqual(float(frames[1]["h"][1]), math.pi / 2, places=6)
        with self.assertRaises(ValueError):
            export.read_binary(path, 2)

    def test_traffic_json(self):
        path = self.dir / "traffic.bin"
        export.write_binary(self.rec, path)
        doc = export.write_traffic_json(
            self.rec, self.dir / "traffic.json", path, True, {"synthetic": True}
        )
        self.assertEqual(doc["schema"], "corridor-traffic-v1")
        self.assertEqual((doc["t0"], doc["dt"], doc["frames"]), (300.0, 1.0, 3))
        self.assertTrue(doc["synthetic"])
        self.assertEqual(doc["binary"]["bytes"], path.stat().st_size)
        self.assertEqual({v["type"] for v in doc["vehicles"]}, {"car", "taxi", "bus"})

    def test_selection_keeps_whole_trajectories(self):
        kept = export.select(self.rec, max_records=3)
        ids = [v["id"] for v in kept.vehicles]
        self.assertIn("bus_syn00.0", ids)  # buses first
        self.assertLessEqual(sum(len(f) for f in kept.frames), 3)
        for vehicle in range(len(kept.vehicles)):
            original = next(i for i, v in enumerate(self.rec.vehicles) if v["id"] == ids[vehicle])
            count = sum(any(r[0] == original for r in f) for f in self.rec.frames)
            self.assertEqual(sum(any(r[0] == vehicle for r in f) for f in kept.frames), count)
        capped = export.select(self.rec, max_records=100, max_concurrent=2)
        self.assertLessEqual(max(map(len, capped.frames)), 2)

    def test_protocol_trajectory_frames_validate(self):
        data = self.dir / "run/data"
        data.mkdir(parents=True)
        export.write_trajectory_frames(self.rec, data / "trajectories.json")
        manifest = {
            "schema_version": "1.1.0",
            "scene_id": "imperial_corridor",
            "simulation": "traffic_sumo",
            "run_id": "synthetic_fixture",
            "status": "complete",
            "created_at": "2026-10-26T00:00:00Z",
            "provenance": {
                "code_revision": "test",
                "dirty": False,
                "parameters": {"synthetic": True},
                "inputs": [],
            },
            "spatial": {
                "frame": "ENU",
                "units": "m",
                "origin": {
                    "longitude": -0.200473,
                    "latitude": 51.506427,
                    "height_m": 0,
                    "vertical_datum": "flat",
                },
                "bounds_m": {"min": [-4000, -4000, 0], "max": [4000, 4000, 5]},
            },
            "time": {"unit": "s", "samples": self.rec.times},
            "layers": [
                {
                    "id": "traffic",
                    "kind": "trajectories",
                    "format": "trajectory_frames",
                    "asset": "data/trajectories.json",
                    "sampling": "linear",
                    "display": {"widget": "trajectories", "capabilities": ["pick"]},
                }
            ],
        }
        path = self.dir / "run/manifest.json"
        path.write_text(json.dumps(manifest))
        self.assertEqual(validate(path), 1)
        frames = json.loads((data / "trajectories.json").read_text())["frames"]
        self.assertEqual(frames[2], {"ids": ["taxi_3"], "positions": [[-7.0, -7.0, 0.0]]})


if __name__ == "__main__":
    unittest.main()
