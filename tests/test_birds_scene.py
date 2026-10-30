"""Bird scene coupling (urban_geometry.birds.scene) on small synthetic fixtures: no network, no scene data."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
HAVE_DEPS = all(importlib.util.find_spec(m) for m in ("scipy", "PIL"))


@unittest.skipUnless(HAVE_DEPS, "Install the birds extra (scipy) and Pillow")
class BirdSceneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    # ---- fields: decoding and placement follow scene.json exactly as the viewer does
    def write_scene(self):
        from PIL import Image

        scene = self.dir / "scene"
        web = scene / "physics" / "web"
        grid = {"cell_m": 4, "cols": 20, "rows": 10, "x0": 100.0, "z_south": 50.0}
        layers = {
            "wind": {"file": "wind.npy", "cell_m": 4, "frames": 2, "t0_s": 10.0, "step_s": 10.0},
            "temp": {"file": "temp.npy", "cell_m": 4, "frames": 1, "t0_s": 0.0, "step_s": 0},
        }
        (web / "wind").mkdir(parents=True)
        (web / "temp").mkdir(parents=True)
        (scene / "scene.json").write_text(json.dumps({"grid": grid, "layers": layers}))
        index = {
            "layers": {
                "wind": {"kind": "rgb3", "range": [-2.5, 2.5], "frames": 2, "note": "u, v, w"},
                "temp": {"kind": "gray", "range": [0, 51], "frames": 1, "note": "C"},
            }
        }
        (web / "index.json").write_text(json.dumps(index))
        enc = lambda v: np.uint8(round((v + 2.5) / 5 * 255))
        for k, u in enumerate((1.0, 2.0)):
            img = np.full((10, 20, 3), enc(0.0), np.uint8)
            img[:, :10, 0] = enc(u)  # west half: u = 1 then 2 m/s
            img[:5, :, 1] = enc(1.0)  # rows 0-4 = SOUTH half: v = 1 m/s
            Image.fromarray(img, "RGB").save(web / "wind" / f"{k:03d}.png")
        Image.fromarray(np.full((10, 20), 100, np.uint8), "L").save(web / "temp" / "000.png")
        return scene

    def test_fields_decode_place_and_interpolate(self):
        from urban_geometry.birds.scene.fields import SceneFields

        fields = SceneFields(self.write_scene(), [100, -50, 180, -10], pad_m=0)
        wind = fields.samplers()["wind"]
        west_south = np.array([[110.0, -45.0, 30.0]])
        east_north = np.array([[170.0, -15.0, 30.0]])
        self.assertAlmostEqual(wind(west_south, 10.0)[0, 0], 1.0, delta=0.03)
        self.assertAlmostEqual(wind(west_south, 15.0)[0, 0], 1.5, delta=0.03)  # linear in time
        self.assertAlmostEqual(wind(west_south, 99.0)[0, 0], 2.0, delta=0.03)  # held at the end
        self.assertAlmostEqual(wind(west_south, 10.0)[0, 1], 1.0, delta=0.03)  # row 0 = south
        self.assertAlmostEqual(np.abs(wind(east_north, 10.0)).max(), 0.0, delta=0.03)
        temp = fields.samplers()["temperature"](west_south, 0.0)[0]
        self.assertAlmostEqual(temp, 20.0, delta=0.01)

    # ---- sun clock: morning < 0.5 < evening, light 0 at night and 1 at noon
    def test_sun_clock(self):
        from urban_geometry.birds.scene.fields import SunClock

        clock = SunClock(lambda h: 20 * np.sin(np.pi * (h - 6) / 12), duration_s=1000)
        self.assertAlmostEqual(clock.sunrise_h, 6.0, delta=0.05)
        self.assertAlmostEqual(clock.sunset_h, 18.0, delta=0.05)
        self.assertEqual(clock.light(0.0), 0.0)  # 45 min before sunrise
        self.assertLess(clock.phase(0.0), 0.5)
        self.assertGreater(clock.phase(1000.0), 0.5)
        noon_t = (12.0 - clock.start_h) / (clock.end_h - clock.start_h) * 1000
        self.assertAlmostEqual(clock.light(noon_t), 1.0, delta=1e-3)
        self.assertAlmostEqual(clock.phase(noon_t), 0.5, delta=1e-3)

    # ---- placement: parks first, waterside when there are no parks; roosts on flat roofs
    def write_geometry(self, parks=True):
        n, cell = 600, 2.0
        geo = self.dir / ("geo_parks" if parks else "geo_water")
        geo.mkdir()
        height = np.zeros((n, n), np.float32)
        height[290:300, 290:300] = 15.0  # one flat 20 x 20 m roof in the middle
        low = np.zeros((n, n), bool)
        water = np.zeros((n, n), bool)
        if parks:
            low[300:330, 470:500] = True  # 60 x 60 m parks ~ 370 m east and west of the roof
            low[300:330, 100:130] = True
        else:
            water[100:500, 500:510] = True  # a dock ~ 410 m east of the roof
        meta = {
            "spacing_xyz_m": [cell] * 3,
            "source_region_origin_xyz_m": [0.0, 0.0, 0.0],
            "shape_zyx": [16, n, n],
        }
        (geo / "metadata.json").write_text(json.dumps(meta))
        solid = np.zeros((16, n, n), bool)
        solid[:8, height > 0] = True
        np.save(geo / "solid.npy", solid)
        np.save(geo / "height_m.npy", height)
        np.save(geo / "ground_mesh_m_yx.npy", np.zeros((n, n), np.float32))
        np.savez(geo / "bird_landcover_2m.npz", low_vegetation=low, tree=low & False, water=water)
        for name in ("asphalt", "paving"):
            np.save(geo / f"{name}_8m_yx.npy", np.zeros((n // 4, n // 4), bool))
        return geo

    def test_placement_tiers(self):
        from urban_geometry.birds.scene.geometry import SceneGeometry
        from urban_geometry.birds.scene.placement import choose_sites

        box = [0.0, 0.0, 1200.0, 1200.0]
        world, report = choose_sites(SceneGeometry(self.write_geometry(parks=True)), box)
        self.assertEqual({s["kind"] for s in world["forage_sites"]}, {"park"})
        self.assertEqual(
            len({s["center"][0] < 600 for s in world["forage_sites"]}), 2
        )  # both parks
        roost = world["roosts"][0]
        self.assertAlmostEqual(roost["center"][2], 15.0)
        self.assertTrue(580 <= roost["center"][0] <= 600 and 580 <= roost["center"][1] <= 600)
        world, report = choose_sites(SceneGeometry(self.write_geometry(parks=False)), box)
        self.assertEqual(report["candidates"]["park"], 0)
        self.assertEqual({s["kind"] for s in world["forage_sites"]}, {"waterside"})

    # ---- replay: int16 encoding round trip and viewer frame
    def test_replay_round_trip(self):
        from urban_geometry.birds.scene.export import write_replay

        rng = np.random.default_rng(0)
        pos = rng.uniform(-900, 900, (4, 5, 3))
        vel = rng.normal(0, 5, (4, 5, 3))
        bank = rng.uniform(-1, 1, (4, 5))
        states = rng.integers(0, 5, (4, 5)).astype(np.uint8)
        m = write_replay(self.dir / "r", pos, vel, bank, states, np.arange(4.0), {"scene": "t"})
        q = np.fromfile(self.dir / "r" / "bird_replay.i16", "<i2").reshape(4, 5, 6).astype(float)
        e = m["encoding"]
        xyz = np.array(e["offset_m"]) + q[..., :3] * e["position_scale_m"]
        expected = np.stack([pos[..., 0], pos[..., 2], -pos[..., 1]], axis=-1)  # viewer X, Y, Z
        self.assertLess(np.abs(xyz - expected).max(), 0.051)
        yaw = q[..., 3] * e["angle_scale_rad"]
        self.assertLess(
            np.abs(np.angle(np.exp(1j * (yaw - np.arctan2(vel[..., 0], -vel[..., 1]))))).max(), 1e-3
        )
        self.assertTrue(
            np.array_equal(np.fromfile(self.dir / "r" / "bird_states.u8", np.uint8), states.ravel())
        )
        self.assertEqual((m["frames"], m["birds"], m["schema"]), (4, 5, "uwm-bird-replay-2"))

    # ---- a flock's moments come out in day order from its state counts
    def test_flock_moments(self):
        from urban_geometry.birds.scene.export import flock_moments

        F, T, M, D, R = range(5)
        day = [R, R, T, F, F, F, T, M, M, D, R, R]  # one state per frame, whole flock
        moments = flock_moments(
            np.array(day, dtype=np.uint8)[:, None].repeat(10, 1), np.arange(12.0)
        )
        self.assertEqual(
            [(m["label"], m["start_s"], m["end_s"]) for m in moments],
            [
                ("Roosting", 0, 2),
                ("Leaving the roost", 2, 3),
                ("Foraging", 3, 6),
                ("Heading home", 6, 7),
                ("Murmuration", 7, 9),
                ("Settling", 9, 10),
            ],
        )

    # ---- the sim reads scene fields and the sun clock through its hooks; defaults leave it unchanged
    def test_sim_hooks(self):
        from urban_geometry.birds.sim.config import SimConfig
        from urban_geometry.birds.sim.environment import day_fraction, day_phase, get_environment
        from urban_geometry.birds.sim.wind import get_wind

        class Clock:
            phase = staticmethod(lambda t: 0.25)
            light = staticmethod(lambda t: 0.4)

        p = np.zeros((3, 3))
        cfg = SimConfig(
            external_fields={
                "wind": lambda pos, t: np.tile([1.0, 2.0, 0.0], (len(pos), 1)),
                "temperature": lambda pos, t: np.full(len(pos), -5.0),
            },
            day_clock=Clock(),
        )
        self.assertTrue(np.array_equal(get_wind(p, 0.0, cfg), np.tile([1.0, 2.0, 0.0], (3, 1))))
        env = get_environment(p, 0.0, cfg)
        self.assertTrue(np.all(env["temperature"] == -5.0))
        self.assertEqual((day_phase(0.0, cfg), day_fraction(0.0, cfg)), (0.25, 0.4))
        plain = SimConfig(wind_mode="none")
        self.assertIsNone(plain.external_fields)
        self.assertTrue(np.all(get_wind(p, 0.0, plain) == 0))


if __name__ == "__main__":
    unittest.main()
