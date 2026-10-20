"""Bird simulation steps must carry every stateful per-bird value into the next step."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

BIRDS_DEPS = all(importlib.util.find_spec(name) for name in ("numpy", "scipy"))


@unittest.skipUnless(BIRDS_DEPS, "Requires the birds extras (numpy, scipy)")
class BirdStatePersistenceTests(unittest.TestCase):
    def setUp(self):
        import numpy as np

        from urban_geometry.birds.sim.config import SimConfig
        from urban_geometry.birds.sim.states import FORAGE

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        # init_state needs voxel metadata, so supply an empty grid (open ground) instead of a scene.
        geometry = Path(directory.name) / "geometry.npz"
        np.savez(
            geometry,
            geometry=np.zeros((4, 8, 8), dtype=bool),
            grid_spacing=10.0,
            grid_spacing_z=10.0,
            grid_origin=np.array([-40.0, -40.0, 0.0]),
        )
        site = {"size": [20.0, 20.0], "forward": [1, 0, 0], "normal": [0, 0, 1], "quality": 1.0}
        self.config = SimConfig(
            geometry_path=str(geometry),
            world={
                "roosts": [{**site, "center": [-25.0, -25.0, 5.0]}],
                "forage_sites": [{**site, "center": [10.0, 10.0, 5.0]}],
                "roads": [],
                "point_sources": [],
            },
            world_generation="off",
            n_birds=2,
            start_state=FORAGE,
            spawn_point=(10.0, 10.0, 1.0),
            init_flock_radius=0.5,
            # without the day cycle no dusk departure occurs, so both birds keep foraging
            enable_environment=False,
            enable_wave_routing=False,
            # food density is capped at 1, so every landing is a foodless hop
            ars_food_threshold=1.0,
        )

    def test_step_returns_every_initial_state_key(self):
        from urban_geometry.birds.sim.integrator import init_state, step

        state = init_state(self.config)
        keys = set(state)
        missing = keys - set(step(state, self.config))
        self.assertFalse(missing, f"step() dropped state keys: {sorted(missing)}")

    def test_intensive_forager_gives_up_after_consecutive_foodless_hops(self):
        import numpy as np

        from urban_geometry.birds.sim.integrator import init_state, step
        from urban_geometry.birds.sim.states import FORAGE

        state = init_state(self.config)
        state["forage_mode"][:] = 1  # both birds start exploiting a patch
        highest = 0
        for _ in range(400):
            state = step(state, self.config)
            giveup = state.get("forage_giveup", np.zeros(self.config.n_birds, dtype=np.int32))
            highest = max(highest, int(giveup.max()))
            if not state["forage_mode"].any():
                break
        self.assertTrue((state["bstate"] == FORAGE).all())
        self.assertGreater(highest, self.config.ars_giveup_hops)
        self.assertFalse(state["forage_mode"].any(), "foragers never left a foodless patch")


if __name__ == "__main__":
    unittest.main()
