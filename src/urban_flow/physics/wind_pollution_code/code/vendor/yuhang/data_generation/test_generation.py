import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

from physical_dataset import generate
from velocity_latents import cache_latents


class FakeEncoder(nn.Module):
    def encode(self, value):
        value = torch.cat((value, value[:, :1]), dim=1)
        return F.avg_pool3d(value, kernel_size=4)


class GenerationTest(unittest.TestCase):
    def test_pollution_generation_pairs_corrected_wind(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wind = root / "wind"
            out = root / "pollution"
            wind.mkdir()
            uvw = np.zeros((3, 2, 3, 8), dtype=np.float32)
            uvw[0] = -1
            with h5py.File(wind / "000000.h5", "w") as file:
                file.create_dataset("uvw", data=uvw)
            np.save(root / "sigma.npy", np.zeros((1, 1, 2, 3, 8), dtype=np.float32))
            source = torch.zeros((2, 3, 8))
            source[..., 5] = 1

            generate(
                wind,
                root / "sigma.npy",
                out,
                source,
                steps=1,
                dt=0.1,
                ub=1,
                source_rate=0.2,
                flip_u=True,
            )

            with h5py.File(out / "000000.h5") as file:
                concentration = file["C"][:]
                self.assertEqual(file.attrs["wind_t"], 0)
                self.assertEqual(file.attrs["velocity_sign"], "u_negated")
            saved_source = np.load(out / "source.npy")
            np.testing.assert_array_equal(saved_source, source.numpy())
            self.assertEqual(np.count_nonzero(concentration[..., :5]), 0)
            self.assertGreater(np.count_nonzero(concentration[..., 6:]), 0)

    def test_wind_latent_cache_writes_model_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wind = root / "wind"
            out = root / "latents"
            wind.mkdir()
            with h5py.File(wind / "000000.h5", "w") as file:
                file.create_dataset("uvw", data=np.ones((3, 4, 8, 8), dtype=np.float32))

            cache_latents(
                wind,
                out,
                [0],
                FakeEncoder(),
                checkpoint="compression.pth",
                latent_scale=0.1,
            )

            with h5py.File(out / "000000.h5") as file:
                self.assertEqual(file["z_v"].shape, (4, 1, 2, 2))
                self.assertEqual(file["z_v"].dtype, np.dtype("float16"))
                self.assertEqual(file.attrs["source_timestep"], 0)
                self.assertAlmostEqual(file.attrs["latent_scale"], 0.1)


if __name__ == "__main__":
    unittest.main()
