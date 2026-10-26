"""London Underground pipeline: depth model, clipping, map matching and schedules.

All fixtures here are synthetic (made-up tracks, stations and timetables).
"""

import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from traffic.corridor_sumo.tfl import Enu
from transit.underground import build
from transit.underground import geometry as geo
from transit.underground import run as run_mod
from transit.underground.config import line_id

DEPTH = {
    "subsurface_m": 6.0,
    "deep_m": 22.0,
    "rail_tunnel_m": 12.0,
    "layer_step_m": 6.0,
    "bridge_layer_m": 6.0,
    "bridge_ramp_m": 100.0,
    "portal_ramp_m": 200.0,
    "per_line_m": {},
}


def straight_graph(spec, step=10.0):
    """Graph of consecutive ways along the x axis: spec = [(way, x0, x1, tags, lines)]."""
    g = geo.Graph()
    targets = {}
    for way, x0, x1, tags, lines in spec:
        g.add_way(way, [(x0, 0.0), (x1, 0.0)], [f"n{x0:g}", f"n{x1:g}"], step, lines)
        targets[way] = geo.depth_target(tags, lines, DEPTH)[0]
    return g, targets


def z_at(g, z, x):
    v = min(range(len(g.xy)), key=lambda k: abs(g.xy[k][0] - x) + abs(g.xy[k][1]))
    return z[v]


class DepthModelTest(unittest.TestCase):
    def test_line_kinds_and_layers(self):
        self.assertEqual(geo.depth_target({"tunnel": "yes"}, ["central"], DEPTH)[0], -22.0)
        self.assertEqual(geo.depth_target({"tunnel": "yes"}, ["district"], DEPTH)[0], -6.0)
        deep2 = geo.depth_target({"tunnel": "yes", "layer": "-2"}, ["piccadilly"], DEPTH)
        self.assertEqual(deep2[0], -28.0)
        self.assertEqual(deep2[2], "assumed_typical")
        self.assertEqual(
            geo.depth_target({"tunnel": "yes", "layer": "-3"}, ["jubilee"], DEPTH)[0], -34.0
        )
        self.assertEqual(geo.depth_target({}, ["central"], DEPTH)[:2], (0.0, "surface"))
        self.assertEqual(geo.depth_target({"bridge": "viaduct", "layer": "2"}, [], DEPTH)[0], 12.0)
        unknown = geo.depth_target({"tunnel": "yes", "railway": "subway"}, [], DEPTH)
        self.assertEqual(unknown[0], -6.0)
        self.assertEqual(unknown[2], "assumed_typical_line_unknown")
        mixed = geo.depth_target({"tunnel": "yes"}, ["district", "piccadilly"], DEPTH)
        self.assertEqual(mixed[0], -22.0)
        over = dict(DEPTH, per_line_m={"central": 25.0})
        self.assertEqual(geo.depth_target({"tunnel": "yes"}, ["central"], over)[0], -25.0)

    def test_reference_layer_sets_typical_depth_and_clamps(self):
        ways = [
            ({"tunnel": "yes", "layer": "-3"}, ["central"], 900.0),
            ({"tunnel": "yes", "layer": "-4"}, ["central"], 100.0),
            ({"tunnel": "yes", "layer": "-1"}, ["district"], 50.0),
        ]
        refs = geo.reference_layers(ways, DEPTH)
        self.assertEqual(refs, {"central": -3, "district": -1})
        z = [geo.depth_target(t, ls, DEPTH, refs)[0] for t, ls, _ in ways]
        self.assertEqual(z, [-22.0, -28.0, -6.0])
        deeper = geo.depth_target({"tunnel": "yes", "layer": "-9"}, ["central"], DEPTH, refs)
        self.assertEqual(deeper[0], -34.0)  # at most max_layer_steps (2) below typical
        shallow = geo.depth_target({"tunnel": "yes", "layer": "-1"}, ["central"], DEPTH, refs)
        self.assertEqual(shallow[0], -16.0)  # at most one step above typical
        no_layer = geo.depth_target({"tunnel": "yes"}, ["central"], DEPTH, refs)
        self.assertEqual(no_layer[0], -22.0)

    def test_portal_ramp_is_linear_over_ramp_length(self):
        g, targets = straight_graph(
            [
                (1, -500, 0, {"railway": "subway"}, ["central"]),
                (2, 0, 1000, {"railway": "subway", "tunnel": "yes"}, ["central"]),
                (3, 1000, 1500, {"railway": "subway"}, ["central"]),
            ]
        )
        z = geo.vertex_z(g, targets, DEPTH)
        self.assertAlmostEqual(z_at(g, z, -100), 0.0)
        self.assertAlmostEqual(z_at(g, z, 0), 0.0)
        self.assertAlmostEqual(z_at(g, z, 100), -11.0, places=6)
        self.assertAlmostEqual(z_at(g, z, 200), -22.0, places=6)
        self.assertAlmostEqual(z_at(g, z, 500), -22.0, places=6)
        self.assertAlmostEqual(z_at(g, z, 900), -11.0, places=6)
        self.assertAlmostEqual(z_at(g, z, 1000), 0.0)

    def test_layer_change_between_tunnels_ramps(self):
        g, targets = straight_graph(
            [
                (1, 0, 1000, {"tunnel": "yes", "layer": "-1"}, ["central"]),
                (2, 1000, 2000, {"tunnel": "yes", "layer": "-2"}, ["central"]),
            ]
        )
        z = geo.vertex_z(g, targets, DEPTH)
        self.assertAlmostEqual(z_at(g, z, 500), -22.0, places=6)
        self.assertAlmostEqual(z_at(g, z, 1000), -22.0, places=6)
        # gradient of the deeper way: 28 m / 200 m -> 6 m step within ~43 m
        self.assertGreater(z_at(g, z, 1020), -28.0)
        self.assertAlmostEqual(z_at(g, z, 1100), -28.0, places=6)
        self.assertAlmostEqual(z_at(g, z, 1500), -28.0, places=6)

    def test_bridge_height_ramps_onto_approaches(self):
        g, targets = straight_graph(
            [
                (1, -300, 0, {}, []),
                (2, 0, 40, {"bridge": "yes", "layer": "1"}, []),
                (3, 40, 300, {}, []),
            ]
        )
        z = geo.vertex_z(g, targets, DEPTH)
        self.assertAlmostEqual(z_at(g, z, 20), 6.0)
        self.assertAlmostEqual(z_at(g, z, -50), 3.0, places=6)
        self.assertAlmostEqual(z_at(g, z, -200), 0.0)


class ClipTest(unittest.TestCase):
    def test_first_point_outside_is_cut_at_boundary(self):
        pieces = geo.clip_polyline([(-5000, 0, -10), (0, 0, -20), (1000, 0, -20)], 4000)
        self.assertEqual(len(pieces), 1)
        self.assertEqual(pieces[0][0], (-4000.0, 0.0, -12.0))
        self.assertEqual(pieces[0][-1], (1000, 0, -20))

    def test_leave_and_reenter_gives_two_pieces(self):
        pts = [(0, 3900), (0, 4100), (100, 4100), (100, 3900)]
        pieces = geo.clip_polyline(pts, 4000)
        self.assertEqual(len(pieces), 2)
        self.assertEqual(pieces[0][-1], (0.0, 4000.0))
        self.assertEqual(pieces[1][0], (100.0, 4000.0))
        self.assertEqual(geo.clip_polyline([(5000, 0), (6000, 0)], 4000), [])

    def test_simplify_keeps_corners_and_drops_collinear(self):
        pts = [(0, 0, 0), (50, 0, 0), (100, 0, 0), (100, 100, 0)]
        self.assertEqual(geo.simplify3d(pts, 1.0), [(0, 0, 0), (100, 0, 0), (100, 100, 0)])
        bent = [(0, 0, 0), (50, 0, -5), (100, 0, 0)]
        self.assertEqual(len(geo.simplify3d(bent, 1.0)), 3)


class MatchTest(unittest.TestCase):
    """Two lines: A runs along y = 0 with a curve; B runs along y = 40 (parallel)."""

    def setUp(self):
        g = geo.Graph()
        a = [(0, 0), (400, 0), (600, 150), (800, 0), (1200, 0)]
        b = [(0, 40), (1200, 40)]
        g.add_way("a", a, ["a0", "a1", "a2", "a3", "a4"], 20.0, ["central"])
        g.add_way("b", b, ["b0", "b1"], 20.0, ["district"])
        self.g = g
        self.grid = geo.Grid(g.xy, 50.0)

    def test_restricted_path_follows_line_track(self):
        stations = [(0, 0), (1200, 0)]
        m = geo.match_sequence(self.g, stations, 60.0, lambda w: w == "a", grid=self.grid)
        self.assertEqual(m["pairs"][0]["method"], "track")
        length = geo.polyline_length(m["path"])
        expected = 400 + 2 * math.hypot(200, 150) + 400
        self.assertAlmostEqual(length, expected, places=3)
        self.assertAlmostEqual(m["pairs"][0]["ratio"], expected / 1200, places=3)
        # the line-B track (straight, shorter) is not used
        self.assertTrue(any(abs(p[1] - 150) < 1e-6 for p in m["path"]))

    def test_unrestricted_takes_other_track_and_missing_track_falls_back(self):
        m = geo.match_sequence(self.g, [(0, 40), (1200, 40)], 30.0, None, grid=self.grid)
        self.assertAlmostEqual(geo.polyline_length(m["path"]), 1200.0, places=3)
        none = geo.match_sequence(
            self.g, [(0, 500), (1200, 500)], 30.0, lambda w: w == "a", grid=self.grid
        )
        self.assertEqual(none["pairs"][0]["method"], "straight_fallback")

    def test_fallback_list_reports_method(self):
        net = type("N", (), {})()
        net.graph, net.grid = self.g, self.grid
        m = build.match_with_fallback(
            net,
            [(0, 40), (600, 40), (1200, 40)],
            30.0,
            [("line", lambda w: w == "a"), ("any_rail", None)],
        )
        self.assertEqual([p["method"] for p in m["pairs"]], ["track_any_rail"] * 2)
        self.assertEqual(len(m["station_index"]), 3)
        self.assertEqual(m["station_index"][0], 0)


class ScheduleTest(unittest.TestCase):
    def test_headway_and_trains_per_hour(self):
        deps = [8 * 3600 + 60 * m for m in range(0, 60, 4)]
        h = build.headway_stats(deps)
        self.assertEqual(h["trains_per_hour"], 15)
        self.assertEqual(h["mean_headway_min"], 4.0)
        self.assertEqual(h["headway_from_tph_min"], 4.0)
        irregular = build.headway_stats([0, 120, 600, 660])
        self.assertEqual(irregular["max_gap_min"], 8.0)
        self.assertEqual(irregular["mean_headway_min"], 3.67)

    def test_position_interpolation_and_inverse(self):
        offsets = [0.0, 1000.0, 2500.0]
        times = [[100, 120], [220, 250], [400, 400]]
        self.assertIsNone(build.position(offsets, times, 99))
        self.assertEqual(build.position(offsets, times, 110), 0.0)
        self.assertEqual(build.position(offsets, times, 170), 500.0)
        self.assertEqual(build.position(offsets, times, 240), 1000.0)
        self.assertEqual(build.position(offsets, times, 325), 1750.0)
        self.assertIsNone(build.position(offsets, times, 401))
        for t in (130, 170, 210, 260, 390):
            s = build.position(offsets, times, t)
            self.assertAlmostEqual(build.time_at(offsets, times, s), t, places=6)

    def test_sampled_frames_follow_path_and_stay_in_domain(self):
        path = [(-5000.0, 0.0, -22.0), (0.0, 0.0, -22.0), (3000.0, 0.0, -22.0)]
        sampler = build.PathSampler(path)
        pattern = {
            "_full_offsets": [0.0, 5000.0, 8000.0],
            "_s_in": 1000.0,
            "_s_out": 8000.0,
            "_sampler": sampler,
        }
        trip = {"id": "t1", "pattern": "p", "times": [[0, 0], [500, 530], [830, 830]]}
        frames = build.sample_frames({"p": pattern}, [trip], 0, 900, 10, 4000.0)
        self.assertEqual(len(frames), 91)
        self.assertEqual(frames[0]["ids"], [])  # outside the domain at x = -5000
        at = {k * 10: f for k, f in enumerate(frames)}
        self.assertEqual(at[100]["positions"], [[-4000.0, 0.0, -22.0]])
        self.assertEqual(at[510]["positions"], [[0.0, 0.0, -22.0]])  # dwelling
        self.assertEqual(at[680]["positions"], [[1500.0, 0.0, -22.0]])
        self.assertEqual(at[900]["ids"], [])
        xs = [f["positions"][0][0] for f in frames if f["ids"]]
        self.assertEqual(xs, sorted(xs))
        self.assertTrue(all(abs(x) <= 4000 for x in xs))

    def test_domain_span_keeps_outside_neighbours(self):
        stops = {"A": {"x": -5000, "y": 0}, "B": {"x": -3000, "y": 0}, "C": {"x": 0, "y": 0}}
        stops |= {"D": {"x": 5000, "y": 0}, "E": {"x": 7000, "y": 0}}
        calls = [{"station": s} for s in "ABCDE"]
        self.assertEqual(build.domain_span(calls, stops=stops, half=4000), (0, 3))
        self.assertIsNone(build.domain_span(calls[3:], stops=stops, half=4000))


class TimetableTest(unittest.TestCase):
    def test_long_outside_excursion_splits_runs(self):
        xs = {"A": -5000, "B": -1000, "C": 4500, "D": 6000, "E": 4600, "F": 0, "G": 5000}
        stops = {k: {"x": x, "y": 0} for k, x in xs.items()}
        calls = [{"station": s} for s in "ABCDEFG"]
        self.assertEqual(build.domain_runs(calls, 4000, stops), [(0, 2), (4, 6)])
        self.assertEqual(build.domain_runs(calls[:4], 4000, stops), [(0, 2)])

    def test_missing_parent_is_derived_from_naptan_code(self):
        enu = Enu(-0.2, 51.5)
        stops = {}
        for sid, x in (("9400ZZLUQWY1", 0.0), ("9400ZZLUQWY2", 10.0)):
            lon, lat = enu.inverse(x, 0.0)
            stops[sid] = {"stop_id": sid, "stop_name": "Queensway Station", "stop_lat": str(lat),
                          "stop_lon": str(lon), "parent_station": "", "location_type": "0"}  # fmt: skip
        sub = {"index": {}, "stops": stops, "routes": {}, "trips": {}, "times": {}}
        tt = build.Timetable(sub, enu)
        self.assertEqual(tt.derived_parents, ["940GZZLUQWY"])
        self.assertEqual(tt.parent("9400ZZLUQWY2"), "940GZZLUQWY")
        self.assertAlmostEqual(tt.stops["940GZZLUQWY"]["x"], 5.0, places=6)
        self.assertEqual(tt.station_name("940GZZLUQWY"), "Queensway")


class SyntheticNetworkTest(unittest.TestCase):
    """Network + timetable + patterns on a made-up two-station line."""

    def test_end_to_end_pattern(self):
        enu = Enu(-0.2, 51.5)
        nodes, nds = {}, []
        for k, x in enumerate(range(-6000, 6001, 500)):
            lon, lat = enu.inverse(float(x), 0.0)
            nodes[str(k + 1)] = [f"{lat:.7f}", f"{lon:.7f}", {}]
            nds.append(k + 1)
        mid = len(nds) // 2
        osm = {
            "nodes": nodes,
            "features": {},
            "ways": {
                "10": {"tags": {"railway": "subway"}, "nds": nds[: mid - 2]},
                "11": {"tags": {"railway": "subway", "tunnel": "yes"}, "nds": nds[mid - 3 :]},
            },
            "routes": [
                {
                    "id": 1,
                    "tags": {"type": "route", "route": "subway", "name": "Central line: X → Y"},
                    "members": [
                        {"type": "way", "ref": 10, "role": ""},
                        {"type": "way", "ref": 11, "role": ""},
                    ],
                }
            ],
            "stop_areas": [],
        }
        cfg = {"depth": DEPTH, "graph_step_m": 20.0, "simplify_m": 1.0, "station_match_m": 250.0}
        net = build.Network(osm, enu, 4000.0, 1500.0, cfg)
        tracks = net.tracks()
        self.assertTrue(all(abs(p[0]) <= 4000 for t in tracks for p in t["shape"]))
        self.assertEqual({t["lines"][0] for t in tracks}, {"central"})
        self.assertTrue(any(t["tunnel"] for t in tracks))
        stops = {}
        for sid, x in (("P", -4500.0), ("Q", -1000.0), ("R", 2000.0), ("S", 5000.0)):
            lon, lat = enu.inverse(x, 0.0)
            stops[sid] = {"stop_id": sid, "stop_name": f"{sid} Underground Station",
                          "stop_lat": str(lat), "stop_lon": str(lon), "parent_station": ""}  # fmt: skip
        times = [
            {"stop_id": s, "arrival_time": t, "departure_time": t, "stop_sequence": str(i)}
            for i, (s, t) in enumerate(
                [("P", "08:00:00"), ("Q", "08:05:00"), ("R", "08:10:00"), ("S", "08:15:00")]
            )
        ]
        sub = {
            "index": {},
            "stops": stops,
            "routes": {"r": {"route_id": "r", "route_short_name": "Central"}},
            "trips": {"t": {"trip_id": "t", "route_id": "r", "direction_id": "0"}},
            "times": {"t": times},
        }
        tt = build.Timetable(sub, enu)
        patterns, assign = build.build_patterns(net, tt, cfg)
        self.assertEqual(len(patterns), 1)
        pat = next(iter(patterns.values()))
        self.assertEqual(pat["stations"], ["P", "Q", "R", "S"])
        self.assertEqual(pat["stations_inside"], [False, True, True, False])
        self.assertEqual(pat["match"]["methods"], {"track": 3})
        self.assertAlmostEqual(pat["match"]["path_over_straight"], 1.0, places=3)
        self.assertAlmostEqual(pat["inside_length_m"], 8000.0, delta=1.0)
        self.assertAlmostEqual(pat["station_offsets_m"][1], 3000.0, delta=1.0)
        self.assertLess(pat["station_offsets_m"][0], 0)
        self.assertLess(min(p[2] for p in pat["path"]), -21.9)
        res = build.period_trains(patterns, assign, tt, (7 * 3600 + 3000, 9 * 3600), 4000.0)
        self.assertEqual(len(res["trips"]), 1)
        self.assertAlmostEqual(res["trips"][0]["domain_enter_s"], 8 * 3600 + 300 * 500 / 3500, 0)
        st = build.status(patterns, assign, tt, {"am_peak": [8, 9]}, 4000.0, [
            {"id": "Q", "name": "Q", "timetable": True},
            {"id": "R", "name": "R", "timetable": True},
        ])  # fmt: skip
        line = st["lines"]["central|0"]["periods"]["am_peak"]
        self.assertEqual(line["trains_per_hour"], 1)
        self.assertEqual(line["full_crossings"], 1)
        # enters 500 m after P (3500 m in 300 s), leaves 2000 m after R (3000 m in 300 s)
        run_s = (300 - 300 * 500 / 3500) + 300 + 300 * 2000 / 3000
        self.assertAlmostEqual(line["domain_run_time_min"], run_s / 60, 2)
        self.assertAlmostEqual(line["domain_avg_speed_kmh"], 8000 / run_s * 3.6, 1)
        self.assertEqual(st["stations"]["Q"]["lines"]["central"]["first_train"], "08:05:00")

    def test_line_names(self):
        self.assertEqual(line_id("Hammersmith & City"), "hammersmith-city")
        self.assertEqual(line_id("Waterloo & City"), "waterloo-city")
        self.assertEqual(
            geo.relation_line({"route": "train", "name": "Elizabeth line: Paddington → X"}),
            "elizabeth",
        )
        self.assertEqual(
            geo.relation_line({"route": "train", "name": "Mildmay Line: A → B"}), "overground"
        )
        self.assertIsNone(
            geo.relation_line({"route": "train", "name": "Southern: London Victoria → B"})
        )
        self.assertEqual(
            geo.relation_line(
                {"route": "subway", "network": "London Underground", "name": "District line: A → B"}
            ),
            "district",
        )


if __name__ == "__main__":
    unittest.main()


class TerrainPlacementTest(unittest.TestCase):
    """Heights on the scene DEM: river filled from the banks, tunnels below a low-pass."""

    def setUp(self):
        from urban_geometry.image_to_threejs import terrain

        # 10 m grid: banks at 5 m, a 100 m river at -1.5 m, a 30 m hill to the east.
        dem = np.full((41, 61), 5.0, dtype=np.float32)
        dem[:, 20:30] = -1.5
        dem[:, 45:] = 30.0
        index = {"x0": 0.0, "y0": 0.0, "dx": 10.0, "vertical_datum": "test datum"}
        self.terrain = terrain
        self.surface = terrain.DemSurface(dem, index, smooth_m=30.0)

    def test_river_is_filled_from_the_banks(self):
        self.assertAlmostEqual(float(self.surface.ground(250, 200)), -1.5, places=3)
        self.assertGreater(float(self.surface.road(250, 200)), 4.0)
        self.assertAlmostEqual(float(self.surface.road(100, 200)), 5.0, places=3)

    def test_tunnels_hang_from_the_low_pass_and_blend_at_portals(self):
        tz = run_mod.terrain_z
        x, y = 100, 200  # flat bank: low-pass == surface
        self.assertAlmostEqual(tz(self.surface, x, y, 0.0), 5.0, places=3)
        self.assertAlmostEqual(tz(self.surface, x, y, -22.0), -17.0, places=3)
        # At the foot of the hill the low-pass lies between bank and hill.
        z = tz(self.surface, 440, 200, -22.0)
        self.assertTrue(5.0 - 22.0 < z < 30.0 - 22.0)
        # Above ground (bridge decks) the street surface is used as is.
        self.assertAlmostEqual(
            tz(self.surface, 250, 200, 6.5), float(self.surface.road(250, 200)) + 6.5
        )

    def test_datum_text(self):
        self.assertEqual(self.terrain.vertical_datum_text(None), self.terrain.FLAT_DATUM)
        self.assertTrue(self.terrain.vertical_datum_text({"vertical_datum": "X"}).endswith("X"))
