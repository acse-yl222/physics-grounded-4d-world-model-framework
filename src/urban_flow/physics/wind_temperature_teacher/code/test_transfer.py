from common.layout import scene_input

"""Small CPU engineering tests. These are NOT scientific coupled results."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import zipfile

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cloud_workflow as w
import prepare_assets as assets

CFG = {
    "seed": 42,
    "factor": 4,
    "fine_spacing_m": 1.0,
    "wind_step_seconds": 25.0,
    "temperature_step_seconds": 90.0,
    "temperature_steps": 2,
    "ambient_c": 26.0,
    "ground_c": 30.0,
    "roof_c": 30.0,
    "surface_exchange_per_s": 0.001,
    "diffusivity_m2_s": 1.0,
    "forcing_layers": 2,
    "cfl_safety": 0.8,
    "temperature_overlap": [4, 8, 8],
}
STATS = {
    "temp_mean": 26.0,
    "temp_std": 2.0,
    "velocity_scale": 2.0,
    "height_scale": 20.0,
    "surface_temp_mean": 28.0,
    "surface_temp_std": 4.0,
    "surface_exchange_scale": 0.002,
}


def geo(shape=(8, 8, 8)):
    return {
        "solid": np.zeros(shape, bool),
        "roof": np.zeros(shape, bool),
        "height": np.zeros(shape[1:], np.float32),
    }


class TransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)

    def test_reduce_and_coarse_mask(self):
        a = np.arange(8**3, dtype=np.float32).reshape(8, 8, 8)
        self.assertAlmostEqual(w.block_reduce(a, 4)[0, 0, 0], a[:4, :4, :4].mean())
        solid = np.zeros_like(a, bool)
        solid[0, 0, 0] = True
        g = w.coarse_geometry(solid, 4, 4.0)
        self.assertEqual(g["solid"].sum(), 1)
        self.assertEqual(g["roof"].sum(), 1)
        self.assertEqual(g["height"][0, 0], 4.0)
        velocity = w.coarse_wind(np.ones((3, 8, 8, 8), np.float32), g["solid"], 4)
        self.assertTrue((velocity[:, 0, 0, 0] == 0).all())
        np.testing.assert_array_equal(velocity[:, 1, 1, 1], [-1, 1, 1])

    def test_wind_derivative_coordinate_signs(self):
        source = (Path(__file__).parent / "vendor/scaled/tools/NN4PDEs.py").read_text()
        selected = []
        for node in ast.parse(source).body:
            if not isinstance(node, ast.Assign):
                continue
            target = node.targets[0]
            while isinstance(target, ast.Subscript):
                target = target.value
            if isinstance(target, ast.Name) and (
                target.id.startswith("p_div_") or target.id in ("w2", "w3", "w4")
            ):
                selected.append(node)
        env = {"torch": torch, "dx": 1.0}
        exec(compile(ast.Module(body=selected, type_ignores=[]), "verified_stencils", "exec"), env)
        z, y, x = torch.meshgrid(
            *(torch.arange(5, dtype=torch.float32) for _ in range(3)), indexing="ij"
        )
        responses = [
            float(torch.nn.functional.conv3d(r[None, None], env[k]).mean())
            for r, k in ((x, "w2"), (y, "w3"), (z, "w4"))
        ]
        np.testing.assert_array_equal(np.sign(responses), [-1, 1, 1])

    def test_temporal_interpolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(5):
                np.save(Path(tmp) / f"wind_{i:03d}.npy", np.full((3, 2, 2, 2), i, np.float32))
            np.testing.assert_allclose(w.wind_at(tmp, 90), 3.6)
            np.testing.assert_allclose(w.wind_at(tmp, -90), 0)
            with self.assertRaises(FileNotFoundError):
                w.wind_at(tmp, 150)

    def test_input_order_and_scaling(self):
        g = geo()
        g["solid"][1, 1, 1] = True
        g["roof"][1, 1, 1] = True
        g["height"][:] = 8
        a = w.make_input(
            np.stack([np.full((8, 8, 8), v) for v in [24, 26, 28]]),
            np.stack([np.full((8, 8, 8), v) for v in [3, 4, 0]]),
            g,
            CFG,
            STATS,
        )
        self.assertEqual(a.shape, (15, 8, 8, 8))
        np.testing.assert_allclose(
            a[:, 1, 1, 1], [-1, 0, 1, 1.5, 2, 0, 2.5, 1, 0, 1, 0.4, 1, 0.5, 0.5, 0]
        )

    def test_input_matches_original_yiqi_dataset(self):
        p = Path(__file__).parent / "original/temperature_surrogate_3d.py"
        spec = importlib.util.spec_from_file_location("_yiqi_original_test", p)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        g = geo()
        g["solid"][1, 2, 3] = True
        g["roof"][1, 2, 3] = True
        g["height"][:] = 12
        rng = np.random.default_rng(4)
        temps = rng.normal(26, 1, (4, 8, 8, 8)).astype(np.float32)
        winds = rng.normal(0, 1, (3, 4, 8, 8, 8)).astype(np.float32)
        case = SimpleNamespace(
            n_training_steps=3,
            temperature=temps,
            u=winds[0],
            v=winds[1],
            w=winds[2],
            solid_mask=g["solid"],
            roof_mask=g["roof"],
            height_field=g["height"],
            study_area_mask=np.ones((8, 8), bool),
            surface_exchange=np.full((8, 8), CFG["surface_exchange_per_s"], np.float32),
            ground_surface_temperature=np.full((8, 8), CFG["ground_c"], np.float32),
            ambient_temp_series=np.full(4, CFG["ambient_c"], np.float32),
        )
        dataset = module.TemperatureSurrogateDataset(
            [case], module.SurrogateStats(**STATS), patch_size=(8, 8, 8), random_crop=False
        )
        expected = dataset[0]["x"].numpy()
        actual = w.make_input(temps[:3], winds[:, 2], g, CFG, STATS)
        np.testing.assert_allclose(actual, expected, rtol=1e-6, atol=1e-6)

    def test_uniform_physics(self):
        cfg = {**CFG, "ground_c": 26.0, "roof_c": 26.0}
        out, log = w.physical_step(
            np.full((8, 8, 8), 26, np.float32), np.ones((3, 8, 8, 8), np.float32), geo(), cfg
        )
        np.testing.assert_allclose(out, 26, atol=1e-5)
        self.assertGreater(log["substeps"], 1)

    def test_heat_bounded_and_solids(self):
        g = geo()
        g["solid"][:2, 3:5, 3:5] = True
        g["roof"][1, 3:5, 3:5] = True
        wind = np.zeros((3, 8, 8, 8), np.float32)
        wind[0] = -2
        wind[1] = 0.4
        out, _ = w.physical_step(np.full((8, 8, 8), 26, np.float32), wind, g, CFG)
        self.assertGreater(out[~g["solid"]].max(), 26)
        self.assertGreaterEqual(out.min(), 26 - 1e-4)
        self.assertLessEqual(out.max(), 30 + 1e-4)
        self.assertTrue((out[g["roof"]] == 30).all())

    def test_negative_wind_boundary(self):
        cfg = {**CFG, "roof_c": 26.0}
        t = torch.full((8, 8, 8), 28.0)
        velocity = torch.zeros((3, 8, 8, 8))
        velocity[0] = -1
        g = geo()
        w.impose(t, velocity, torch.from_numpy(g["solid"]), torch.from_numpy(g["roof"]), cfg)
        self.assertTrue((t[:-1, 1:-1, -1] == 26).all())
        self.assertTrue((t[:-1, 1:-1, 0] == 28).all())

    def test_tiled_coverage(self):
        class Constant(torch.nn.Module):
            def forward(self, x):
                return torch.ones((1, 1, *x.shape[-3:]))

        a = np.zeros((15, 16, 40, 40), np.float32)
        p = w.predict(Constant(), a, STATS, (8, 32, 32), (4, 8, 8), "cpu")
        np.testing.assert_allclose(p, 28.0)

    def test_config_rejects_bad_clock(self):
        with self.assertRaises(ValueError):
            w.validate_config({**CFG, "wind_step_seconds": 90.0})

    def test_run_manifest_rejects_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "SOURCE_INFO.json"
            source.write_text("{}")
            f = root / "asset"
            f.write_text("trusted")
            with patch.object(w, "ROOT", root):
                w.prepare_run({"test": f}, CFG, root / "run")
                w.prepare_run({"test": f}, CFG, root / "run")
                with self.assertRaises(ValueError):
                    w.prepare_run({"test": f}, {**CFG, "ground_c": 35}, root / "run")

    def test_physical_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "temperature").mkdir()
            (root / "wind").mkdir()
            for i in range(5):
                np.save(root / "wind" / f"wind_{i:03d}.npy", np.zeros((3, 8, 8, 8), np.float32))
            w.physical_reference(CFG, root, geo())
            values = [np.load(root / "temperature" / f"reference_{i:03d}.npy") for i in range(5)]
            with patch.object(
                w, "physical_step", side_effect=AssertionError("Should reuse saved frame")
            ):
                w.physical_reference(CFG, root, geo())
            for i, a in enumerate(values):
                np.testing.assert_array_equal(
                    a, np.load(root / "temperature" / f"reference_{i:03d}.npy")
                )

    def test_recursive_does_not_use_future_truth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "temperature").mkdir()
            (root / "wind").mkdir()
            for i, v in enumerate((24, 26, 28, 60, 80)):
                np.save(
                    root / "temperature" / f"reference_{i:03d}.npy",
                    np.full((8, 8, 8), v, np.float32),
                )
            for i in range(5):
                np.save(root / "wind" / f"wind_{i:03d}.npy", np.zeros((3, 8, 8, 8), np.float32))
            seen = []

            def fake(model, x, *args):
                seen.append(x[:3].copy())
                return np.full((8, 8, 8), 30, np.float32)

            with (
                patch.object(w, "load_temperature", return_value=(None, STATS, (8, 8, 8))),
                patch.object(w, "predict", side_effect=fake),
            ):
                rows = w.run_temperature({"temperature": "dummy"}, CFG, root, geo())
            # Calls: recursive at 0, one_step at 0, recursive at 90, one_step at 90.
            np.testing.assert_array_equal(
                seen[2][:, 0, 0, 0], [0, 1, 2]
            )  # [26,28,30], not [26,28,60]
            np.testing.assert_array_equal(seen[3][:, 0, 0, 0], [0, 1, 17])
            self.assertEqual(len(rows), 6)

    def test_exact_temperature_weights(self):
        base = Path(__file__).resolve().parent.parent
        model, stats, patch_size = w.load_temperature(
            scene_input("south_ken", "models", "temperature_one_step.pt")
        )
        with torch.inference_mode():
            out = model(torch.zeros((1, 15, *patch_size)))
        self.assertEqual(out.shape, (1, 1, *patch_size))
        self.assertTrue(torch.isfinite(out).all())
        self.assertAlmostEqual(stats["velocity_scale"], 1.603515625)

    def test_tiny_actual_temperature_pipeline_and_plot(self):
        # Small artificial engineering fixture; discarded, never delivered as a result.
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ("wind", "temperature", "figures"):
                (root / d).mkdir()
            g = geo((8, 32, 32))
            g["solid"][:2, 10:14, 10:14] = True
            g["roof"][1, 10:14, 10:14] = True
            for i in range(5):
                np.save(root / "wind" / f"wind_{i:03d}.npy", np.zeros((3, 8, 32, 32), np.float32))
            cfg = {**CFG, "temperature_steps": 1}
            w.physical_reference(cfg, root, g)
            weight = scene_input("south_ken", "models", "temperature_one_step.pt")
            rows = w.run_temperature({"temperature": weight}, cfg, root, g)
            self.assertEqual(len(rows), 3)
            self.assertTrue(np.isfinite(rows[0]["mae_c"]))
            with patch.object(plt, "show"):
                w.plot_results(cfg, root, g)
            self.assertGreater((root / "figures/temperature_comparison.png").stat().st_size, 1000)
            plt.close("all")

    def test_minimal_asset_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contents = {
                "weights/w.pt": b"wind",
                "weights/v.pt": b"vae",
                "data/inputs/sigma.npy": b"geo",
                "data/physical/W_005000.h5": b"uvw",
                "not_needed_pollution.h5": b"pollution",
            }
            exp = {"weights": {"wind": "weights/w.pt", "wind_vae": "weights/v.pt"}}
            contents["experiment.json"] = json.dumps(exp).encode()
            manifest = {
                "schema": 1,
                "files": {
                    k: {"sha256": hashlib.sha256(v).hexdigest(), "bytes": len(v)}
                    for k, v in contents.items()
                },
            }
            archive = root / "test.zip"
            with zipfile.ZipFile(archive, "w") as z:
                for k, v in contents.items():
                    z.writestr(k, v)
                z.writestr("bundle_manifest.json", json.dumps(manifest))
            paths = assets.prepare(archive, root / "out")
            self.assertEqual(set(paths), {"wind", "wind_vae", "geometry", "initial_wind"})
            self.assertFalse((root / "out/not_needed_pollution.h5").exists())
            assets.prepare(archive, root / "out")
            for name in ("../escape", "/absolute", "C:bad", "a\\b"):
                with self.assertRaises(ValueError):
                    assets.safe(name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
