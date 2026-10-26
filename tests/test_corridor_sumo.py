"""Overture -> SUMO plain XML, TfL/DfT parsing, calibration, state and export (synthetic fixtures)."""

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
from traffic.corridor_sumo import calibrate, dft, export, overture_net, periods, state, tfl

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


# ---------------------------------------------------------------- DfT counts (SYNTHETIC rows)

ORIGIN = {"longitude": -0.200473, "latitude": 51.506427}


def aadf_row(cp, year, lon, lat, amv, buses=0, **extra):
    return {
        "count_point_id": str(cp),
        "year": str(year),
        "longitude": str(lon),
        "latitude": str(lat),
        "road_name": extra.pop("road_name", "A4"),
        "road_type": extra.pop("road_type", "Major"),
        "estimation_method": extra.pop("estimation_method", "Counted"),
        "all_motor_vehicles": str(amv),
        "buses_and_coaches": str(buses),
        **extra,
    }


def raw_row(cp, direction, day, hour, amv, buses=0):
    return {
        "count_point_id": str(cp),
        "direction_of_travel": direction,
        "year": day[:4],
        "count_date": day + " 00:00:00",
        "hour": str(hour),
        "all_motor_vehicles": str(amv),
        "buses_and_coaches": str(buses),
        "cars_and_taxis": str(amv - buses),
    }


class DftCounts(unittest.TestCase):
    """DfT-shaped rows are SYNTHETIC test values, not DfT data."""

    def test_domain_bbox_matches_scene(self):
        lon0, lat0, lon1, lat1 = dft.domain_bbox(ORIGIN, 4000)
        self.assertAlmostEqual(lon0, -0.258203, places=5)
        self.assertAlmostEqual(lat0, 51.470494, places=5)
        self.assertAlmostEqual(lon1, -0.142743, places=5)
        self.assertAlmostEqual(lat1, 51.542360, places=5)

    def test_count_point_bbox_filter(self):
        bbox = dft.domain_bbox(ORIGIN, 4000)
        rows = [
            aadf_row(1, 2025, -0.2, 51.5, 1000),
            aadf_row(2, 2025, -0.26, 51.5, 1000),  # west of the domain
            aadf_row(3, 2025, -0.2, 51.55, 1000),  # north of the domain
            aadf_row(4, 2025, -0.1428, 51.4705, 1000),  # just inside the SE corner
            {**aadf_row(5, 2025, 0, 0, 1000), "longitude": ""},  # unparsable
        ]
        self.assertEqual([r["count_point_id"] for r in dft.inside(rows, bbox)], ["1", "4"])

    def test_latest_year_and_general_traffic(self):
        enu = tfl.Enu(ORIGIN["longitude"], ORIGIN["latitude"])
        rows = [aadf_row(1, 2019, -0.2, 51.5, 900, 90), aadf_row(1, 2025, -0.2, 51.5, 1100, 100)]
        point = dft.latest_points(rows, enu)["1"]
        self.assertEqual(point.year, 2025)
        self.assertEqual(dft.general(rows[1]), 1000)
        self.assertAlmostEqual(point.x, (-0.2 - ORIGIN["longitude"]) * enu.kx, places=1)

    def test_profile_from_raw_counts_and_fallback(self):
        # Point 1 direction E: weekday (2024-06-12 is a Wednesday) 07-19 counts of 60 veh/h
        # (+10 buses, excluded) against a directional general AADF of 1200 -> share 0.05.
        raw = [raw_row(1, "E", "2024-06-12", h, 70, 10) for h in dft.DFT_HOURS]
        raw += [raw_row(1, "E", "2024-06-15", h, 999) for h in dft.DFT_HOURS]  # Saturday
        raw += [raw_row(1, "W", "2024-06-12", h, 60) for h in dft.DFT_HOURS[:-1]]  # incomplete
        by_dir = {("1", 2024): {"E": 1200.0, "W": 1000.0}}
        profiles = dft.point_profiles(raw, by_dir, min_year=2015)
        self.assertEqual(set(profiles), {("1", "E")})
        own = profiles[("1", "E")]
        self.assertEqual(own["dates"], ["2024-06-12"])
        self.assertAlmostEqual(own["share"][8], 0.05)
        pooled = dft.pooled_profiles(profiles, {"1": "Major"})
        fb = dft.profile_for("1", "W", "Major", profiles, pooled)
        self.assertTrue(fb["fallback"])
        self.assertEqual(fb["source"], "pooled_major_fallback")
        minor = dft.profile_for("2", "N", "Minor", profiles, pooled)
        self.assertEqual(minor["source"], "pooled_all_fallback")
        self.assertIs(dft.profile_for("1", "E", "Major", profiles, pooled), own)

    def test_direction_split_sources(self):
        enu = tfl.Enu(ORIGIN["longitude"], ORIGIN["latitude"])
        rows = [aadf_row(cp, 2025, -0.2, 51.5, 1000) for cp in (1, 2, 3)]
        points = dft.latest_points(rows, enu)
        by_dir = {("1", 2025): {"N": 600.0, "S": 200.0}}
        dft.assign_directions(points, by_dir, {"2": {"E": 0.25, "W": 0.75}})
        self.assertEqual(points["1"].direction_source, "dft_aadf_by_direction")
        self.assertAlmostEqual(points["1"].directions["N"]["general"], 750)
        self.assertAlmostEqual(points["2"].directions["W"]["general"], 750)
        self.assertEqual(points["3"].direction_source, "unknown_split_50_50")
        self.assertEqual(set(points["3"].directions), {"C"})

    def test_periods_reject_hours_without_counts(self):
        cfg = {"warmup_s": 900, "fcd_window_s": 600, "list": [{"id": "am_peak", "hour": 8}]}
        (w,) = periods.period_windows(cfg)
        self.assertEqual((w["sim_begin_s"], w["start_s"], w["end_s"]), (27900, 28800, 32400))
        self.assertEqual(w["fcd_begin_s"], 31800)
        cfg["list"] = [{"id": "night", "hour": 22}]
        with self.assertRaises(ValueError):
            periods.period_windows(cfg)


class CountMatching(unittest.TestCase):
    def cand(self, eid, heading_deg, dist, cls="primary", name="Cromwell Road", passenger=True):
        return {
            "id": eid,
            "name": name,
            "cls": cls,
            "dist": dist,
            "heading": math.radians(heading_deg),
            "passenger": passenger,
        }

    def test_heading_matches_direction(self):
        self.assertTrue(calibrate.heading_matches(math.radians(10), "E"))
        self.assertTrue(calibrate.heading_matches(math.radians(60), "E"))  # diagonal road
        self.assertFalse(calibrate.heading_matches(math.radians(180), "E"))
        self.assertTrue(calibrate.heading_matches(math.radians(-90), "S"))
        self.assertFalse(calibrate.heading_matches(math.radians(90), "S"))
        self.assertTrue(calibrate.heading_matches(math.radians(123), "C"))

    def test_choose_edge_by_heading_class_and_junction_names(self):
        point = {"road_name": "A4", "road_type": "Major", "start_junction": "Earl's Ct Rd"}
        cands = [
            self.cand("e1", 0, 8),
            self.cand("-e1", 180, 8),
            self.cand("side", 0, 3, cls="residential", name="Side Street"),
            self.cand("cross", 5, 2, name="Earls Court Road"),
        ]
        cfg = {"radius_m": 40, "near_m": 20}
        east = calibrate.choose_edge(cands, point, "E", cfg)
        self.assertEqual((east["edge"], east["quality"]), ("e1", "class+heading"))
        self.assertEqual(calibrate.choose_edge(cands, point, "W", cfg)["edge"], "-e1")
        miss = calibrate.choose_edge([self.cand("x", 90, 5)], point, "E", cfg)
        self.assertIsNone(miss["edge"])
        self.assertIn("heading", miss["reason"])
        self.assertIn("within", calibrate.choose_edge([], point, "E", cfg)["reason"])

    def test_street_name_match_wins(self):
        point = {"road_name": "Ladbroke Grove", "road_type": "Minor"}
        cands = [
            self.cand("near", 90, 2, cls="residential", name="Other Road"),
            self.cand("named", 80, 15, cls="tertiary", name="Ladbroke Gr"),
        ]
        choice = calibrate.choose_edge(cands, point, "N", {})
        self.assertEqual((choice["edge"], choice["quality"]), ("named", "name+heading"))
        self.assertTrue(calibrate.is_ref("A315") and calibrate.is_ref("U"))
        self.assertFalse(calibrate.is_ref("Ladbroke Grove"))

    def test_heading_at_shape(self):
        dist, heading = calibrate.heading_at([(0, 0), (10, 0), (10, 10)], 11, 5)
        self.assertAlmostEqual(dist, 1)
        self.assertAlmostEqual(heading, math.pi / 2)


class CalibrationFit(unittest.TestCase):
    def test_geh(self):
        self.assertAlmostEqual(calibrate.geh(150, 100), math.sqrt(2 * 50**2 / 250))
        self.assertEqual(calibrate.geh(0, 0), 0.0)
        self.assertLess(calibrate.geh(1050, 1000), 5)
        self.assertGreater(calibrate.geh(500, 1000), 10)

    def test_fit_summary_and_r2(self):
        fit = calibrate.fit_summary([(100, 100), (1000, 1050), (500, 300)])
        self.assertEqual(fit["n"], 3)
        self.assertAlmostEqual(fit["geh_lt_5_pct"], 66.7)
        self.assertEqual(calibrate.r_squared([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertIsNone(calibrate.r_squared([5, 5], [4, 6]))

    def test_edgedata_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.xml"
            calibrate.write_edgedata(
                [{"id": "am", "begin": 28800, "end": 32400, "counts": {"e1": 812.6}}], path
            )
            el = ET.parse(path).getroot().find("interval/edge")
            self.assertEqual((el.get("id"), el.get("entered")), ("e1", "813"))


class CapacityScreening(unittest.TestCase):
    def test_overloaded_uncounted_edge_is_relieved(self):
        vehicles = "".join(
            f'<vehicle id="v{i}" depart="{i}"><route edges="{"a b" if i < 6 else "a"}"/></vehicle>'
            for i in range(10)
        )
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / "in.rou.xml", Path(tmp) / "out.rou.xml"
            src.write_text(f"<routes>{vehicles}</routes>")
            # b (uncounted) carries 4 veh/h; a is counted at 10 veh/h despite capacity 2.
            res = calibrate.screen_capacity(
                src, out, {"a": 2, "b": 4}, {"a": 10}, [(0, 3600)], seed=1
            )
            self.assertEqual((res["vehicles_dropped"], res["edges_over_capacity_before"]), (2, 1))
            counts = calibrate.sampled_counts(out, 0, 3600)
            self.assertEqual(counts, {"a": 8, "b": 4})


class LevelOfService(unittest.TestCase):
    def test_speed_ratio_classes(self):
        self.assertEqual(state.classify(0.9, 20), "free")
        self.assertEqual(state.classify(0.7, 20), "moderate")
        self.assertEqual(state.classify(0.5, 20), "heavy")
        self.assertEqual(state.classify(0.3, 20), "congested")

    def test_density_modifiers(self):
        self.assertEqual(state.classify(0.9, 45), "heavy")  # dense despite speed
        self.assertEqual(state.classify(0.9, 80), "congested")
        self.assertEqual(state.classify(0.2, 3), "moderate")  # few vehicles at a signal

    def test_edge_state_from_meandata(self):
        attrs = {"sampledSeconds": 500.0, "entered": 50.0, "speed": 6.0, "density": 20.0}
        s = state.edge_state(attrs, 300, 12.0, 2)
        self.assertEqual((s["q"], s["k_lane"], s["ratio"], s["los"]), (600, 10.0, 0.5, "heavy"))
        self.assertIsNone(state.edge_state({"sampledSeconds": 0}, 300, 12.0, 1))

    def test_simplify_and_shares(self):
        line = [(0, 0), (5, 0.5), (10, 0), (10, 10)]
        self.assertEqual(state.simplify(line, 2.0), [(0, 0), (10, 0), (10, 10)])
        shares = state.los_shares(
            {"a": {"los": "free"}, "b": {"los": "congested"}}, {"a": 300.0, "b": 100.0}
        )
        self.assertEqual(shares["free"], 0.75)
        self.assertEqual(shares["congested"], 0.25)


class SumoCountMatching(unittest.TestCase):
    """Matching and routeSampler on a tiny netconvert network (skipped without SUMO)."""

    def test_match_and_route_sampler(self):
        try:
            from traffic.corridor_sumo import sumo_env

            sumo_env.binary("netconvert")
            sumolib = sumo_env.sumolib()
        except Exception as exc:  # noqa: BLE001
            self.skipTest(f"SUMO unavailable: {exc}")
        net = overture_net.build(SEGMENTS, CONNECTORS)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            nod, edg, net_path = tmp / "n.nod.xml", tmp / "e.edg.xml", tmp / "net.net.xml"
            overture_net.write_plain_xml(net, nod, edg)
            sumo_env.run(
                [sumo_env.binary("netconvert"), "--node-files", nod, "--edge-files", edg]
                + ["-o", net_path, "--offset.disable-normalization", "true", "--lefthand"]
                + ["true", "--no-warnings", "true"]
            )
            snet = sumolib.net.readNet(str(net_path))
            cands = calibrate.edge_candidates(snet, 150, 3, 40)
            point = {"road_name": "U", "road_type": "Minor"}
            east = calibrate.choose_edge(cands, point, "E", {})
            west = calibrate.choose_edge(cands, point, "W", {})
            self.assertNotEqual(east["edge"], west["edge"])
            e = snet.getEdge(east["edge"])
            self.assertGreater(e.getToNode().getCoord()[0], e.getFromNode().getCoord()[0])
            self.assertEqual(periods.opposite_edge(e).getID(), west["edge"])
            # routeSampler reproduces a single count exactly from one candidate route.
            cand = tmp / "cand.rou.xml"
            cand.write_text(f'<routes><route id="r0" edges="{east["edge"]}"/></routes>')
            counts = tmp / "counts.xml"
            calibrate.write_edgedata(
                [{"id": "h", "begin": 0, "end": 3600, "counts": {east["edge"]: 120}}], counts
            )
            out = tmp / "out.rou.xml"
            calibrate.route_sampler(
                cand, counts, out, prefix="t_", vtype="car", seed=1, log=tmp / "rs.log"
            )
            self.assertEqual(calibrate.sampled_counts(out, 0, 3600), {east["edge"]: 120})


if __name__ == "__main__":
    unittest.main()
