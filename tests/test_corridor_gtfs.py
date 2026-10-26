"""BODS GTFS subset, schedule metrics, SUMO matching and bus status (synthetic fixtures)."""

import json
import math
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from traffic.corridor_sumo import bus_status, gtfs_bus
from traffic.corridor_sumo.tfl import Enu

FIXTURE = ROOT / "tests/fixtures/corridor_sumo/gtfs_synthetic"
ENU = Enu(-0.200473, 51.506427)
HALF = 4000.0


def stop_row(sid, x, y, location_type="0", parent=""):
    lon, lat = ENU.inverse(x, y)
    return {
        "stop_id": sid,
        "stop_code": sid.lower(),
        "stop_name": f"Synthetic {sid}",
        "stop_lat": f"{lat:.7f}",
        "stop_lon": f"{lon:.7f}",
        "location_type": location_type,
        "parent_station": parent,
    }


def trip(start, stops, gaps, key="S1|0", tid=None):
    """Synthetic trip calling at ``stops`` with ``gaps`` seconds between calls."""
    calls, t = [], start
    for i, s in enumerate(stops):
        if i:
            t += gaps[i - 1]
        calls.append({"stop": s, "arr": t, "dep": t})
    return {"trip_id": tid or f"T{start}", "key": key, "stops": calls}


class SubsetFilters(unittest.TestCase):
    def test_bbox_filter_and_parents(self):
        rows = [
            stop_row("IN", 100, -200),
            stop_row("EDGE", 3999, 3999),
            stop_row("OUT", 4100, 0),
            stop_row("ENTRANCE", 10, 10, location_type="2"),
            stop_row("CHILD", -3990, 0, parent="PARENT"),
            stop_row("PARENT", -4050, 0, location_type="1"),
            stop_row("STATION_OUT", 0, 5000, location_type="1"),
            {**stop_row("BLANK", 0, 0), "location_type": ""},
        ]
        kept = gtfs_bus.domain_stops(rows, ENU, HALF)
        self.assertEqual(set(kept), {"IN", "EDGE", "CHILD", "PARENT", "BLANK"})
        self.assertAlmostEqual(kept["IN"]["x"], 100, delta=0.01)
        self.assertAlmostEqual(kept["IN"]["y"], -200, delta=0.01)

    def test_bus_route_types(self):
        self.assertTrue(gtfs_bus.is_bus_route_type("3"))
        self.assertTrue(gtfs_bus.is_bus_route_type("704"))
        for t in ("0", "1", "2", "4", "200", "800", "", None):
            self.assertFalse(gtfs_bus.is_bus_route_type(t), t)

    def test_clip_span(self):
        inside = {"b", "c", "e"}.__contains__
        self.assertEqual(gtfs_bus.clip_span(list("abcdef"), inside), (1, 4))
        self.assertIsNone(gtfs_bus.clip_span(list("ad"), inside))

    def test_parse_time_over_midnight(self):
        self.assertEqual(gtfs_bus.parse_time("25:01:30"), 90090)
        self.assertEqual(gtfs_bus.fmt_time(90090), "25:01:30")


CAL = [
    {"service_id": "WK", "monday": "1", "tuesday": "1", "wednesday": "1", "thursday": "1",
     "friday": "1", "saturday": "0", "sunday": "0", "start_date": "20260601",
     "end_date": "20260731"},
    {"service_id": "SAT", "monday": "0", "tuesday": "0", "wednesday": "0", "thursday": "0",
     "friday": "0", "saturday": "1", "sunday": "0", "start_date": "20260601",
     "end_date": "20260731"},
]  # fmt: skip
EXC = [
    {"service_id": "WK", "date": "20260610", "exception_type": "2"},
    {"service_id": "EXTRA", "date": "20260611", "exception_type": "1"},
    {"service_id": "EXTRA", "date": "20260616", "exception_type": "1"},
]


class ServiceDay(unittest.TestCase):
    def test_active_services(self):
        self.assertEqual(gtfs_bus.active_services("20260609", CAL, EXC), {"WK"})
        self.assertEqual(gtfs_bus.active_services("20260610", CAL, EXC), set())
        self.assertEqual(gtfs_bus.active_services("20260611", CAL, EXC), {"WK", "EXTRA"})
        self.assertEqual(gtfs_bus.active_services("20260613", CAL, EXC), {"SAT"})
        self.assertEqual(gtfs_bus.active_services("20260801", CAL, EXC), set())

    def test_choose_service_date(self):
        counts = Counter({"WK": 100, "SAT": 500, "EXTRA": 5})
        day, scores = gtfs_bus.choose_service_date(
            CAL, EXC, counts, "20260601", "20260731", horizon_days=20
        )
        # Tue-Thu only, the 10th lost its weekday service, the 11th and 16th have extras:
        # the earliest of the tied maxima wins.
        self.assertEqual(day, "20260611")
        self.assertTrue(all(s["weekday"] in ("Tuesday", "Wednesday", "Thursday") for s in scores))
        self.assertEqual(next(s for s in scores if s["date"] == "20260610")["trips"], 0)

    def test_bank_holiday_excluded(self):
        counts = Counter({"WK": 1})
        _, scores = gtfs_bus.choose_service_date(
            CAL, [], counts, "20260601", "20260731", holidays={"20260602"}
        )
        self.assertNotIn("20260602", [s["date"] for s in scores])


class ScheduleMetrics(unittest.TestCase):
    def setUp(self):
        # Every 10 min 08:00-08:50 then every 20 min, A-B-C with 5 + 5 min running time;
        # a short working (A-B only) at 08:05:30 adds one call at A and B.
        starts = [28800 + 600 * i for i in range(6)] + [32400 + 1200 * i for i in range(3)]
        self.trips = [trip(s, ["A", "B", "C"], [300, 300]) for s in starts]
        self.trips.append(trip(28800 + 330, ["A", "B"], [240], tid="short"))
        self.wins = gtfs_bus.windows({"am": [8, 9], "late": [9, 10]}, [8, 10])

    def test_headway_and_trips_per_hour(self):
        out = gtfs_bus.schedule_metrics(self.trips, self.wins)
        self.assertEqual(out["busiest_stop"], "B")  # A and B tie on 10 calls; ties -> max id
        am = out["windows"]["am"]
        self.assertEqual(am["trips_per_h"], 7.0)
        self.assertAlmostEqual(am["headway_min"], 60 / 7, places=2)
        late = out["windows"]["late"]
        self.assertEqual(late["trips_per_h"], 3.0)
        self.assertEqual(late["headway_min"], 20.0)
        self.assertEqual(late["headway_busiest_stop_min"], 20.0)
        self.assertEqual(out["windows"]["h08"]["trips_per_h"], 7.0)

    def test_runtime_and_speed(self):
        out = gtfs_bus.schedule_metrics(self.trips, self.wins, lambda t: 500.0 * len(t["stops"]))
        am = out["windows"]["am"]
        self.assertEqual(am["runtime_min"], 10.0)  # median of six 10 min + one 4 min trip
        self.assertEqual(am["speed_kmh"], round(1500 / 600 * 3.6, 2))
        self.assertEqual(out["windows"]["late"]["runtime_min"], 10.0)

    def test_partial_distance_tuple(self):
        # (metres, seconds) measured between matched stops only: 1000 m in 200 s.
        out = gtfs_bus.schedule_metrics(self.trips, self.wins, lambda t: (1000.0, 200))
        self.assertEqual(out["windows"]["am"]["speed_kmh"], 18.0)
        self.assertEqual(out["windows"]["am"]["distance_km"], 1.0)

    def test_scheduled_trips_longest_inside_run(self):
        stops = {
            sid: {"location_type": "0", "x": 0.0, "y": 0.0} for sid in ("A", "B", "C", "D", "E")
        }
        times = [
            ("A", "08:00:00"), ("OUT1", "08:02:00"), ("B", "08:04:00"), ("C", "08:06:00"),
            ("D", "08:08:00"), ("OUT2", "08:10:00"), ("E", "08:12:00"),
        ]  # fmt: skip
        sub = {
            "stops": stops,
            "routes": {"R": {"route_id": "R", "route_short_name": "9"}},
            "trips": {"T": {"trip_id": "T", "route_id": "R", "direction_id": "1"}},
            "times": {
                "T": [
                    {"stop_id": s, "arrival_time": t, "departure_time": t, "stop_sequence": i}
                    for i, (s, t) in enumerate(times)
                ]
            },
        }
        (t,) = gtfs_bus.scheduled_trips(sub)["9|1"]
        self.assertEqual([c["stop"] for c in t["stops"]], ["B", "C", "D"])
        self.assertEqual(t["domain_runs"], 3)
        self.assertEqual(gtfs_bus.runtime(t), 240)

    def test_empty_window(self):
        wins = gtfs_bus.windows({"night": [2, 3]}, [2, 3])
        out = gtfs_bus.schedule_metrics(self.trips, wins)
        self.assertEqual(out["windows"]["night"], {"trips_per_h": 0.0, "trips_in_domain": 0})

    def test_stop_buses_per_hour(self):
        out = gtfs_bus.stop_buses_per_hour({"S1|0": self.trips}, self.wins)
        self.assertEqual(out["A"]["am"], 7.0)
        self.assertEqual(out["B"]["am"], 7.0)
        self.assertEqual(out["C"]["am"], 5.0)  # the 08:50 trip reaches C at 09:00

    def test_projection_and_simplify(self):
        line = [(0, 0), (100, 0), (100, 100), (0, 100)]
        proj = gtfs_bus.project_monotone(line, [(50, 5), (95, 50), (10, 95)])
        self.assertEqual([round(o) for o, _ in proj], [50, 150, 290])
        self.assertTrue(all(d <= 5.0 for _, d in proj))
        # A target near an earlier part of the line is not projected backwards.
        back = gtfs_bus.project_monotone(line, [(10, 95), (50, 0)])
        self.assertGreaterEqual(back[1][0], back[0][0])
        pts = [(x, 0.01 * (x % 2)) for x in range(100)] + [(100, 50)]
        self.assertEqual(gtfs_bus.simplify(pts, 1.0), [(0, 0.0), (99, 0.01), (100, 50)])


class BusStatusMetrics(unittest.TestCase):
    def setUp(self):
        self.schedule = json.loads((FIXTURE / "schedule.json").read_text())
        self.trips = json.loads((FIXTURE / "trips.json").read_text())
        self.stops = json.loads((FIXTURE / "stops.json").read_text())

    def test_fixture_is_marked_synthetic(self):
        for path in FIXTURE.iterdir():
            self.assertIn("SYNTHETIC", path.read_text(), path)

    def test_parse_stopinfos(self):
        obs = bus_status.parse_stopinfos(FIXTURE / "stopinfos.xml")
        self.assertEqual(sorted(obs), ["v1", "v2", "v3", "v4"])
        self.assertEqual([c["bus_stop"] for c in obs["v3"]], ["SYN_A", "SYN_B", "SYN_C"])
        self.assertEqual(obs["v2"][1]["started"], 29760.0)
        self.assertEqual(obs["v2"][1]["ended"], 29780.0)

    def test_match_calls_sequential(self):
        observed = [
            {"bus_stop": "X", "started": 10.0, "ended": 15.0},
            {"bus_stop": "Y", "started": 20.0, "ended": 25.0},
            {"bus_stop": "X", "started": 30.0, "ended": 35.0},
        ]
        calls = bus_status.match_calls(
            [["a", "X", 0, 0], ["b", "Y", 0, 0], ["a", "X", 0, 0], ["c", "Z", 0, 0]], observed
        )
        self.assertEqual([c.get("obs_arr") for c in calls], [10.0, 20.0, 30.0, None])

    def test_classify_thresholds(self):
        c = bus_status.classify
        self.assertEqual(c(60, 200), "on time")
        self.assertEqual(c(150, 200), "minor delay")  # mean 2.5 min
        self.assertEqual(c(60, 420), "minor delay")  # p90 7 min
        self.assertEqual(c(400, 500), "major delay")
        self.assertEqual(c(60, 1300), "severe")  # p90 > 20 min
        self.assertEqual(c(0, 0, unreached_share=0.3), "severe")

    def test_regularity_and_bunching(self):
        out = bus_status.regularity([0, 600, 1200, 1300], 600, 0.5)
        self.assertEqual(out["headways"], 3)
        self.assertAlmostEqual(out["bunching_share"], 1 / 3, places=3)
        gaps = [600, 600, 100]
        mean = sum(gaps) / 3
        cv = math.sqrt(sum((g - mean) ** 2 for g in gaps) / 3) / mean
        self.assertAlmostEqual(out["headway_cv"], round(cv, 3))
        self.assertEqual(bus_status.percentile([0, 10, 20, 30, 40], 90), 36.0)

    def test_compute_against_fixture(self):
        runs = {
            "am_peak": {"trips": self.trips, "stopinfos": FIXTURE / "stopinfos.xml"},
            "inter_peak": {"trips": {}, "stopinfos": None},
        }
        out = bus_status.compute(self.schedule, self.stops, runs)
        (route,) = out["routes"]
        sim = route["simulated"]["am_peak"]
        self.assertEqual(sim["calls_scheduled"], 12)
        self.assertEqual(sim["calls_reached"], 11)
        self.assertAlmostEqual(sim["unreached_share"], 0.083, places=3)
        self.assertEqual(sim["mean_delay_min"], round(720 / 11 / 60, 2))
        self.assertEqual(sim["p90_delay_min"], 4.0)
        self.assertEqual(sim["runtime_min"], round(700 / 60, 2))
        self.assertEqual(sim["scheduled_runtime_min"], 10.0)
        self.assertEqual(sim["speed_kmh"], round(2000 / 700 * 3.6, 2))
        self.assertEqual(sim["regularity"]["stop"], "SYN_B")
        self.assertAlmostEqual(sim["regularity"]["bunching_share"], 0.333, places=3)
        self.assertEqual(sim["regularity"]["headway_cv"], 0.413)
        self.assertEqual(route["status"], {"am_peak": "on time", "inter_peak": "schedule only"})
        self.assertEqual(route["schedule"]["inter_peak"]["headway_min"], 15.0)
        stop_b = next(s for s in out["stops"] if s["id"] == "SYN_B")
        self.assertEqual(stop_b["scheduled_buses_per_h"], {"am_peak": 6.0, "inter_peak": 4.0})
        self.assertEqual(stop_b["est_mean_delay_min"]["am_peak"], round(180 / 4 / 60, 2))
        self.assertFalse(out["periods"]["inter_peak"]["simulated"])
        self.assertIn("SUMO model estimates", out["provenance"]["simulated_metrics"])

    def test_schedule_only(self):
        runs = {p: {"trips": {}, "stopinfos": None} for p in self.schedule["periods"]}
        out = bus_status.compute(self.schedule, self.stops, runs)
        self.assertEqual(set(out["routes"][0]["status"].values()), {"schedule only"})
        self.assertEqual(out["routes"][0]["simulated"], {})

    def test_cli_assigns_periods(self):
        with tempfile.TemporaryDirectory() as tmp:
            gtfs = Path(tmp) / "gtfs"
            (gtfs / "am_peak").mkdir(parents=True)
            for name in ("schedule.json", "stops.json"):
                (gtfs / name).write_text((FIXTURE / name).read_text())
            (gtfs / "am_peak/trips.json").write_text((FIXTURE / "trips.json").read_text())
            run = Path(tmp) / "run_am_peak"
            run.mkdir()
            (run / "stopinfos.xml").write_text((FIXTURE / "stopinfos.xml").read_text())
            out = Path(tmp) / "status.json"
            bus_status.main(["unused", str(run), "--gtfs-dir", str(gtfs), "--out", str(out)])
            result = json.loads(out.read_text())
            self.assertEqual(result["routes"][0]["status"]["am_peak"], "on time")
            with self.assertRaises(SystemExit):
                bus_status.assign_runs([tmp], self.schedule["periods"])


class SumoMatching(unittest.TestCase):
    """Matcher on a tiny generated grid (skipped without SUMO)."""

    @classmethod
    def setUpClass(cls):
        try:
            from traffic.corridor_sumo import sumo_env

            netgenerate = sumo_env.binary("netgenerate")
            cls.sumolib = sumo_env.sumolib()
        except Exception as exc:
            raise unittest.SkipTest(f"SUMO unavailable: {exc}") from exc
        cls.tmp = tempfile.TemporaryDirectory()
        cls.net_path = Path(cls.tmp.name) / "grid.net.xml"
        subprocess.run(
            [netgenerate, "--grid", "--grid.number", "4", "--grid.length", "200",
             "--lefthand", "true", "--no-turnarounds", "true", "-o", str(cls.net_path)],
            check=True, capture_output=True,
        )  # fmt: skip
        cls.net = cls.sumolib.net.readNet(str(cls.net_path))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_stops_along_a_street(self):
        # Stops 4 m to the left of the eastbound carriageway of the y=200 street
        # (left-hand traffic: kerb on the left), plus one stop far off the network.
        stops = [
            {"stop": "s1", "x": 100.0, "y": 206.0},
            {"stop": "s2", "x": 300.0, "y": 206.0},
            {"stop": "far", "x": 300.0, "y": 900.0},
            {"stop": "s3", "x": 500.0, "y": 206.0},
        ]
        m = gtfs_bus.Matcher(self.net, radius=30.0).match(stops, None)
        self.assertEqual([p["stop"] for p in m["stops"]], ["s1", "s2", "s3"])
        self.assertEqual(m["matched_share"], 0.75)
        self.assertAlmostEqual(m["path_length"], 400.0, delta=25.0)
        for a, b in zip(m["edges"], m["edges"][1:], strict=False):
            self.assertIn(self.net.getEdge(b), self.net.getEdge(a).getOutgoing())
        for p in m["stops"]:
            from_node = p["lane"].getEdge().getFromNode().getCoord()
            to_node = p["lane"].getEdge().getToNode().getCoord()
            self.assertGreater(to_node[0], from_node[0])  # eastbound
        self.assertEqual(gtfs_bus._stop_edge_index(m), sorted(gtfs_bus._stop_edge_index(m)))


if __name__ == "__main__":
    unittest.main()
