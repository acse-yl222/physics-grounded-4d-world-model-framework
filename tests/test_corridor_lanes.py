"""Lane-accurate corridor traffic: road network export, lane paths, timing, chunking."""

import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from traffic.corridor_sumo import lane_routes, road_network

# Synthetic T junction: two-lane approach W->C, two-lane exit C->E, one-lane branch C->N,
# return lanes E->C and N->C; a bus-only edge C->S.
NODES = """<nodes>
  <node id="W" x="-200" y="0"/><node id="C" x="0" y="0" type="priority"/>
  <node id="E" x="200" y="0"/><node id="N" x="0" y="200"/><node id="S" x="0" y="-200"/>
</nodes>"""
EDGES = """<edges>
  <edge id="WC" from="W" to="C" numLanes="2" speed="13.9" priority="3"/>
  <edge id="CE" from="C" to="E" numLanes="2" speed="13.9" priority="3"/>
  <edge id="EC" from="E" to="C" numLanes="2" speed="13.9" priority="3"/>
  <edge id="CN" from="C" to="N" numLanes="1" speed="8.9" priority="1"/>
  <edge id="NC" from="N" to="C" numLanes="1" speed="8.9" priority="1"/>
  <edge id="CS" from="C" to="S" numLanes="1" speed="8.9" priority="1" allow="bus"/>
</edges>"""


def tiny_net(tmp: Path):
    """sumolib net (with internal lanes) of the synthetic junction, or None without SUMO."""
    try:
        from traffic.corridor_sumo import sumo_env

        netconvert = sumo_env.binary("netconvert")
        sumolib = sumo_env.sumolib()
    except Exception:  # noqa: BLE001
        return None
    (tmp / "t.nod.xml").write_text(NODES)
    (tmp / "t.edg.xml").write_text(EDGES)
    net_path = tmp / "t.net.xml"
    sumo_env.run(
        [netconvert, "--node-files", tmp / "t.nod.xml", "--edge-files", tmp / "t.edg.xml"]
        + ["-o", net_path, "--offset.disable-normalization", "true", "--lefthand", "true"]
        + ["--no-turnarounds", "true", "--no-warnings", "true"]
    )
    return sumolib.net.readNet(str(net_path), withInternal=True)


class RoadNetworkFromSumo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.net = tiny_net(Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        if self.net is None:
            self.skipTest("SUMO unavailable")

    def doc(self, half=150.0):
        return road_network.build(self.net, half, lambda xs, ys: 0.01 * np.asarray(xs), {})

    def test_lanes_internal_lanes_and_connections(self):
        doc = self.doc()
        c = doc["counts"]
        self.assertEqual(c["normal_lanes"], 9)  # 2+2+2+1+1+1
        self.assertGreater(c["internal_lanes"], 0)
        self.assertEqual(c["bus_only_lanes"], 1)
        n = len(doc["lanes"])
        for conn in doc["connections"]:
            self.assertLess(conn["from_lane"], n)
            self.assertLess(conn["to_lane"], n)
            if conn["via"] is not None:
                self.assertTrue(doc["lanes"][conn["via"]]["id"].startswith(":"))
        for lane in doc["lanes"]:
            if lane["id"].startswith(":"):
                self.assertIsNone(lane["edge"])
                self.assertEqual(doc["junctions"][lane["junction"]]["id"], "C")
            # z is the given street surface (0.01 * x), rounded to 0.1 m
            for x, _, z in lane["shape"]:
                self.assertAlmostEqual(z, 0.01 * x, delta=0.11)
        # Lanes, internal lanes and the next lanes meet end to start.
        lanes = doc["lanes"]
        for conn in doc["connections"]:
            nxt = conn["via"] if conn["via"] is not None else conn["to_lane"]
            a, b = lanes[conn["from_lane"]]["shape"][-1], lanes[nxt]["shape"][0]
            self.assertLess(np.hypot(a[0] - b[0], a[1] - b[1]), 0.2)

    def test_domain_keeps_crossing_lanes_whole(self):
        doc = self.doc(half=50.0)
        ids = {ln["id"] for ln in doc["lanes"]}
        self.assertIn("WC_0", ids)  # crosses x = -50, kept whole
        wc = next(ln for ln in doc["lanes"] if ln["id"] == "WC_0")
        self.assertLess(wc["shape"][0][0], -150)

    def test_lane_path_and_timing(self):
        doc = self.doc()
        net = lane_routes.Network(doc)
        planner = lane_routes.LanePlanner(self.net)
        veh = {
            "id": "v1",
            "type": "car",
            "depart": 100.0,
            "arrival": None,
            "edges": ["WC", "CN"],
            "exits": [120.0, None],
            "stops": [],
        }
        out = lane_routes.build_vehicle(
            veh, "car", planner, net, self.net, (100.0, 200.0), {}, [], None
        )
        lanes = [doc["lanes"][k]["id"] for k in out["path"]]
        self.assertTrue(lanes[0].startswith("WC_"))
        self.assertTrue(lanes[-1].startswith("CN_"))
        self.assertTrue(all(ln.startswith(":C_") for ln in lanes[1:-1]))
        self.assertGreaterEqual(len(lanes), 3)
        # The path follows SUMO connections: (lane, next) pairs are connection hops.
        hops = {
            (c["from_lane"], c["via"] if c["via"] is not None else c["to_lane"])
            for c in doc["connections"]
        }
        for a, b in zip(out["path"], out["path"][1:], strict=False):
            self.assertIn((a, b), hops)
        self.assertNotIn("changes", out)
        self.assertEqual(out["enter"][0], 100.0)
        self.assertEqual(out["enter"][-1], 120.0)
        self.assertEqual(out["enter"], sorted(out["enter"]))
        self.assertIsNone(out["leave"])
        # Playback stays on the lane centre lines.
        p = lane_routes.positions(out, net, np.arange(100.0, 200.0), 200.0)
        ok = p["k"] >= 0
        grid = lane_routes.SegmentGrid(net)
        self.assertLess(grid.distance(p["xy"][ok]).max(), 0.05)

    def test_left_turn_uses_kerbside_lane_and_bus_lane_needs_bus(self):
        planner = lane_routes.LanePlanner(self.net)
        lanes, steps = planner.plan("v", "passenger", ["WC", "CN"])
        # Left-hand traffic: the left turn to N leaves from the kerbside lane 0.
        self.assertEqual(lanes[0], "WC_0")
        self.assertTrue(steps[0][3])
        self.assertEqual(planner.lanes("CS", "bus"), ["CS_0"])
        _, steps = planner.plan("b", "bus", ["WC", "CS"])
        self.assertTrue(steps[0][3])  # connected

    def test_spread_over_equivalent_lanes(self):
        planner = lane_routes.LanePlanner(self.net)
        first = {planner.plan(f"v{k}", "passenger", ["WC", "CE"])[0][0] for k in range(40)}
        self.assertEqual(first, {"WC_0", "WC_1"})


class Timing(unittest.TestCase):
    def test_internal_lane_at_junction_speed_or_constant_speed(self):
        # Free flow: 100 m in 10 s, internal lane 10 m at 5 m/s -> proportional 1 s.
        self.assertEqual(lane_routes.element_times(0.0, 10.0, 90.0, [(10.0, 5.0)]), [0.0, 9.0])
        # Queued: 100 s on the edge -> junction crossed in 10 m / 5 m/s = 2 s.
        self.assertEqual(lane_routes.element_times(0.0, 100.0, 90.0, [(10.0, 5.0)]), [0.0, 98.0])
        # Two internal lanes split by length; none after a teleport.
        t = lane_routes.element_times(0.0, 100.0, 90.0, [(6.0, 5.0), (4.0, 5.0)])
        self.assertEqual([round(v, 6) for v in t], [0.0, 98.0, 99.2])
        self.assertEqual(
            lane_routes.element_times(0.0, 50.0, 90.0, [(10.0, 5.0)], teleport=True), [0.0, 50.0]
        )
        self.assertEqual(lane_routes.element_times(0.0, None, 90.0, [(10.0, 5.0)]), [0.0, None])

    def test_positions_with_stop_jump_and_open_end(self):
        doc = {
            "lanes": [
                {"id": "a", "speed": 10.0, "length": 100.0, "shape": [[0, 0, 0], [100, 0, 0]]},
                {"id": "b", "speed": 10.0, "length": 100.0, "shape": [[100, 0, 0], [200, 0, 0]]},
                {"id": "c", "speed": 10.0, "length": 100.0, "shape": [[300, 0, 0], [400, 0, 0]]},
            ]
        }
        net = lane_routes.Network(doc)
        veh = {
            "id": "bus1",
            "path": [0, 1, 2],
            "enter": [0.0, 40.0, 60.0],
            "leave": None,
            "stops": [{"path_index": 0, "pos_m": 50.0, "arrive": 10.0, "depart": 30.0}],
            "jumps": [[2, 50.0]],
            "end_pos": 40.0,
        }
        p = lane_routes.positions(
            veh, net, np.array([5.0, 20.0, 35.0, 45.0, 55.0, 80.0, 100.0]), 100.0
        )
        np.testing.assert_allclose(p["xy"][:, 0][[0, 1, 2, 3]], [25.0, 50.0, 75.0, 150.0])
        self.assertEqual(p["k"][4], -1)  # between the jump time and the next entry
        np.testing.assert_allclose(p["xy"][[5, 6], 0], [320.0, 340.0])


class Chunking(unittest.TestCase):
    def test_road_network_chunks_round_trip(self):
        lanes = [
            {
                "id": f"e{k}_0",
                "edge": k,
                "index": 0,
                "width": 3.2,
                "speed": 13.9,
                "length": 10.0,
                "shape": [[k, 0.0, 1.0], [k + 10.0, 0.0, 1.0]],
            }
            for k in range(300)
        ]
        doc = {
            "schema": road_network.SCHEMA,
            "lefthand": True,
            "coordinate_frame": "ENU",
            "units": "m",
            "edges": [{"id": f"e{k}", "lanes": [k]} for k in range(300)],
            "lanes": lanes,
            "connections": [
                {"from_lane": k, "to_lane": k + 1, "via": None, "dir": "s"} for k in range(299)
            ],
            "junctions": [{"id": f"j{k}", "type": "priority", "shape": []} for k in range(301)],
            "counts": {"lanes": 300},
            "lane_index": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            names = road_network.write(doc, tmp, {"note": "synthetic"}, max_bytes=20_000)
            self.assertGreater(len(names), 2)
            self.assertEqual(names[0], "road_network.json")
            index = json.loads((tmp / names[0]).read_text())
            self.assertEqual(index["schema"], road_network.INDEX_SCHEMA)
            for name in names[1:]:
                self.assertLessEqual((tmp / name).stat().st_size, 20_000)
            back = road_network.load(tmp)
            for key in ("edges", "lanes", "connections", "junctions"):
                self.assertEqual(back[key], doc[key])
            # Small documents stay whole.
            names = road_network.write(doc, tmp, {}, max_bytes=10**8)
            self.assertEqual(names, ["road_network.json"])
            self.assertEqual(road_network.load(tmp)["lanes"], lanes)

    def test_routes_chunks_round_trip(self):
        vehicles = [
            {"id": f"v{k}", "type": "car", "path": [k, k + 1], "enter": [1.0, 2.0], "leave": 3.0}
            for k in range(500)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "traffic_routes_am.json"
            names = lane_routes.write(
                vehicles, path, {"period": "am", "t0": 0.0, "t1": 9.0}, max_bytes=8_000
            )
            self.assertGreater(len(names), 2)
            for name in names[1:]:
                self.assertLessEqual((Path(tmp) / name).stat().st_size, 8_000)
            back = lane_routes.load(path)
            self.assertEqual(back["vehicles"], vehicles)
            self.assertEqual(back["t1"], 9.0)


class SumoOutputs(unittest.TestCase):
    def test_vehroutes_exit_times_stops_and_teleports(self):
        xml = """<routes>
  <vehicle id="a" type="car" depart="10.00" arrival="40.00">
    <route edges="e1 e2" exitTimes="20.00 40.00"/></vehicle>
  <vehicle id="b" type="bus" depart="15.00">
    <route edges="e1 e2 e3" exitTimes="25.00 -1 -1"/>
    <stop busStop="S1" duration="20.00" started="30.00" ended="50.00"/></vehicle>
  <vehicle id="c" type="car" depart="1.00" arrival="5.00">
    <route edges="e1" exitTimes="5.00"/></vehicle>
</routes>"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vr.xml.gz"
            with gzip.open(path, "wt") as f:
                f.write(xml)
            got = {v["id"]: v for v in lane_routes.read_vehroutes(path, 8.0, 60.0)}
            log = Path(tmp) / "w.log"
            log.write_text(
                "Warning: Teleporting vehicle 'b'; waited too long, from edge 'e2', time=60.00.\n"
            )
            tele = lane_routes.read_teleports(log)
        self.assertEqual(set(got), {"a", "b"})  # c arrived before the window
        self.assertEqual(got["b"]["exits"], [25.0, None, None])
        self.assertEqual(got["b"]["stops"][0]["busStop"], "S1")
        self.assertEqual(tele["b"], [("e2", 60.0)])


class Decks(unittest.TestCase):
    def test_deck_ramps_and_continuity(self):
        s = np.arange(0.0, 401.0, 10.0)
        raw = np.where((s >= 100) & (s <= 300), 1, 0)
        road = np.full(len(s), 5.0)
        road[(s > 150) & (s < 250)] = -1.0  # river / cutting under the bridge
        z, off = road_network.deck_offsets(s, raw, road, 0.0, 0.0)
        self.assertEqual(z[0], 5.0)
        self.assertEqual(z[-1], 5.0)
        self.assertAlmostEqual(z[20], 5.0 + road_network.DECK_M)  # mid-span, base not dipped
        self.assertLessEqual(np.abs(np.diff(off) / 10.0).max(), road_network.RAMP_GRADE + 1e-9)
        # Raised node at the lane start: the deck starts at the node's height.
        raw2 = np.where(s <= 200, 1, 0)
        _, off2 = road_network.deck_offsets(s, raw2, road * 0, road_network.DECK_M, 0.0)
        self.assertAlmostEqual(off2[0], road_network.DECK_M)

    def test_on_way_and_level(self):
        line = np.array([[0.0, 0.0], [100.0, 0.0]])
        pts = np.array([[50.0, 4.0], [101.0, 3.0], [110.0, 0.0], [50.0, 30.0]])
        self.assertEqual(road_network.on_way(pts, line).tolist(), [True, True, False, False])
        self.assertEqual(road_network._level({"bridge": "yes"}), (1, "bridge"))
        self.assertEqual(road_network._level({"bridge": "yes", "layer": "2"}), (2, "bridge"))
        self.assertEqual(road_network._level({"tunnel": "yes", "layer": "-1"}), (0, "tunnel"))
        self.assertEqual(road_network._level({"highway": "primary"}), (0, None))

    def test_touches_square(self):
        self.assertTrue(road_network.touches_square([(-10, 0), (10, 0)], 5))
        self.assertTrue(road_network.touches_square([(-10, 0), (10, 1)], 5))  # crosses only
        self.assertFalse(road_network.touches_square([(-10, 8), (10, 8)], 5))


if __name__ == "__main__":
    unittest.main()
