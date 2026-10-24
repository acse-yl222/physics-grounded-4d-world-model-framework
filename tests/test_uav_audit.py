"""The UAV route audit must never leave a partial retained run behind."""

import contextlib
import hashlib
import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SCENE = "white_city"
RUN_ID = "audit_test_run"
REVISION = "0123456789abcdef" * 2 + "01234567"
GEOMETRY = [
    "height_m.npy",
    "metadata.json",
    "ground_mesh_m_yx.npy",
    "ground_mesh_valid_yx.npy",
    "asphalt_8m_yx.npy",
    "canopy_8m_yx.npy",
]


def load_audit():
    """Import the audit with plotting stubbed; figures only need to exist as files."""
    figure = mock.MagicMock()
    figure.savefig.side_effect = lambda path, **_: Path(path).write_bytes(b"figure")
    pyplot = mock.MagicMock()
    pyplot.subplots.side_effect = lambda *_, **__: (figure, mock.MagicMock())
    collections = mock.MagicMock()
    stubs = {
        "matplotlib": mock.MagicMock(pyplot=pyplot, collections=collections),
        "matplotlib.pyplot": pyplot,
        "matplotlib.collections": collections,
    }
    # patch.dict restores sys.modules, so neither the stubs nor this import leak;
    # load the shared project package first so it is not re-imported afterwards.
    importlib.import_module("common.locations")
    with mock.patch.dict(sys.modules, stubs):
        sys.modules.pop("uav_routing.audit", None)
        return importlib.import_module("uav_routing.audit")


def travel_time(path):
    """The anisotropic no-wind model time that compute records for each route."""
    delta = np.diff(path, axis=0) / np.array([15, 15, 5])
    db = delta[:, 2] * 0.2
    return float(np.sum((-db + np.sqrt(db**2 + 0.96 * np.sum(delta**2, axis=1))) / 0.96))


class UavAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_audit()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "workspace"
        self.scene = self.root / "project" / SCENE
        self.runs = self.scene / "runs"
        self.runs.mkdir(parents=True)
        (self.scene / "views").mkdir()
        (self.scene / "project.json").write_text(json.dumps({"spatial": {"frame": "enu"}}))
        self.geometry = base / "voxel_2m"
        self.geometry.mkdir()
        for name in GEOMETRY:
            (self.geometry / name).write_bytes(name.encode())
        self.wave = base / "wave"
        (self.wave / "src/wavepde").mkdir(parents=True)
        (self.wave / "src/wavepde/__init__.py").write_text("")
        # ground_sites.py writes the scene's selected sites under input/<version>/.
        self.sites = self.scene / "input/stations_ground_20261007"
        self.sites.mkdir(parents=True)
        (self.sites / "stations.json").write_text(json.dumps([{"label": "H1"}, {"label": "C1"}]))
        (self.sites / "selection.json").write_text(json.dumps({"method": "fixture"}))
        np.savez_compressed(self.sites / "ground_site_audit.npz", valid=np.ones((2, 2), bool))
        self.out = base / "compute"
        self.out.mkdir()
        self.write_compute_output()

    def write_compute_output(self, takeoff_m=30.0):
        """Minimal ground-mode compute output: two pads and two directed routes."""
        origin = np.array([0.0, 0.0, -4.0])
        np.savez_compressed(
            self.out / "domain_8m.npz",
            mask=np.zeros((8, 8, 10), bool),
            origin_enu_m=origin,
            spacing_m=8.0,
            height_yx_m=np.zeros((8, 8)),
        )
        pads = [np.array([12.0, 12.0, 0.0]), np.array([36.0, 12.0, 0.0])]
        stations = [
            dict(id=i + 1, label=label, role=role, pad_enu_m=pad.tolist())
            for i, (label, role, pad) in enumerate(zip(["H1", "C1"], ["hub", "collection"], pads))
        ]
        for s in stations:
            s["gate_enu_m"] = [*s["pad_enu_m"][:2], 30.0]
        (self.out / "stations_enu.json").write_text(json.dumps(stations))
        routes = []
        for i, j in [(0, 1), (1, 0)]:
            name = f"route_{stations[i]['label']}_{stations[j]['label']}.npy"
            lift = np.array([0, 0, takeoff_m])
            path = np.array([pads[i], pads[i] + lift, pads[j] + [0, 0, 30], pads[j]])
            np.save(self.out / name, path)
            routes.append(
                dict(
                    source_index=i,
                    target_index=j,
                    source=stations[i]["label"],
                    target=stations[j]["label"],
                    success=True,
                    path=name,
                    path_travel_time_s=travel_time(path),
                )
            )
        np.save(self.out / "travel_time_matrix_s.npy", np.zeros((2, 2)))
        (self.out / "travel_time_matrix_s.csv").write_text("H1,C1\n0,0\n0,0\n")
        summary = dict(
            scene=SCENE,
            ground_mode=True,
            routes=routes,
            geometry={"source_sha256": "0" * 64},
            station_sha256=hashlib.sha256((self.sites / "stations.json").read_bytes()).hexdigest(),
        )
        (self.out / "summary.json").write_text(json.dumps(summary))

    def place_operator_copies(self):
        """Hand-placed copies let the unfixed audit reach its later retention steps."""
        pairs = {"stations_ground.json": "stations.json", "ground_site_audit.npz": None}
        for target, source in pairs.items():
            (self.out / target).write_bytes((self.sites / (source or target)).read_bytes())

    def run_audit(self, **revision):
        argv = ["audit", "--scene", SCENE, "--wave-repo", str(self.wave)]
        argv += ["--geometry", str(self.geometry), "--output", str(self.out)]
        argv += ["--run-id", RUN_ID, "--framework", str(self.root)]
        revision = revision or {"return_value": REVISION + "\n"}
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(self.audit.subprocess, "check_output", **revision),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.audit.main()

    def assert_no_run(self):
        self.assertEqual(sorted(p.name for p in self.runs.iterdir()), [])
        self.assertFalse((self.scene / "views" / f"{RUN_ID}.json").exists())

    def test_retains_ground_site_inputs_from_the_scene_input_directory(self):
        self.run_audit()
        run = self.runs / RUN_ID
        self.assertEqual(sorted(p.name for p in self.runs.iterdir()), [RUN_ID])
        manifest = json.loads((run / "manifest.json").read_text())
        self.assertEqual(manifest["provenance"]["code_revision"], REVISION)
        artifacts = {a["asset"]: a["sha256"] for a in manifest["artifacts"]}
        for asset, source in [
            ("stations_ground.json", self.sites / "stations.json"),
            ("ground_site_audit.npz", self.sites / "ground_site_audit.npz"),
        ]:
            self.assertEqual((run / asset).read_bytes(), source.read_bytes())
            self.assertEqual(artifacts[asset], hashlib.sha256(source.read_bytes()).hexdigest())
        for asset in artifacts:
            self.assertTrue((run / asset).is_file(), asset)
        view = json.loads((self.scene / "views" / f"{RUN_ID}.json").read_text())
        self.assertIn(RUN_ID, view["runs"])
        # A retained run is never replaced, and the refusal leaves nothing behind.
        before = (run / "manifest.json").read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_audit()
        self.assertEqual(sorted(p.name for p in self.runs.iterdir()), [RUN_ID])
        self.assertEqual((run / "manifest.json").read_bytes(), before)

    def test_missing_ground_input_fails_before_creating_the_run(self):
        (self.sites / "ground_site_audit.npz").unlink()
        with self.assertRaises(FileNotFoundError) as caught:
            self.run_audit()
        self.assert_no_run()
        self.assertIn("ground_site_audit.npz", str(caught.exception))

    def test_station_file_must_match_the_compute_input(self):
        (self.sites / "stations.json").write_text(json.dumps([{"label": "changed"}]))
        with self.assertRaises(ValueError):
            self.run_audit()
        self.assert_no_run()

    def test_git_revision_failure_leaves_no_partial_run_and_allows_retry(self):
        self.place_operator_copies()
        failure = subprocess.CalledProcessError(128, ["git", "rev-parse", "HEAD"])
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_audit(side_effect=failure)
        self.assert_no_run()
        self.run_audit()
        self.assertTrue((self.runs / RUN_ID / "manifest.json").is_file())

    def test_failure_while_assembling_removes_the_staged_run(self):
        self.place_operator_copies()
        with (
            mock.patch.object(self.audit.tarfile, "open", side_effect=OSError("disk full")),
            self.assertRaises(OSError),
        ):
            self.run_audit()
        self.assert_no_run()

    def test_route_validation_failures_raise_without_assert(self):
        # Explicit errors survive python -O, which strips assert statements.
        self.write_compute_output(takeoff_m=20.0)
        with self.assertRaises(ValueError) as caught:
            self.run_audit()
        self.assertIn("vertical", str(caught.exception))
        self.assert_no_run()
        self.write_compute_output()
        summary = json.loads((self.out / "summary.json").read_text())
        summary["routes"][0]["path_travel_time_s"] += 1.0
        (self.out / "summary.json").write_text(json.dumps(summary))
        with self.assertRaises(ValueError):
            self.run_audit()
        report = json.loads((self.out / "independent_validation.json").read_text())
        self.assertEqual(report["passed"], 1)
        self.assert_no_run()


if __name__ == "__main__":
    unittest.main()
