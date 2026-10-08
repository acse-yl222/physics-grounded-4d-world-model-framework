"""Local entry point for the existing Colab-exported reproduction ZIP.

prepare needs only Python's standard library. run requires a CUDA GPU and the
bundled dependencies. The numerical workflow inside the ZIP is used unchanged.
"""

from pathlib import Path, PurePosixPath
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import sys
import zipfile


CHUNK = 8 << 20


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_name(name):
    p = PurePosixPath(name)
    # Reject Windows drive/alternate-stream paths as well as POSIX traversal.
    return (
        bool(name)
        and not p.is_absolute()
        and ".." not in p.parts
        and "\\" not in name
        and ":" not in name
    )


def validate_manifest(manifest):
    if manifest.get("schema") != 1 or not isinstance(manifest.get("files"), dict):
        raise ValueError("Unsupported bundle manifest")
    for name, entry in manifest["files"].items():
        if not safe_name(name) or name == "bundle_manifest.json":
            raise ValueError(f"Unsafe manifest path: {name}")
        if not isinstance(entry.get("bytes"), int) or entry["bytes"] < 0:
            raise ValueError(f"Invalid file size: {name}")
        value = entry.get("sha256", "")
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError(f"Invalid checksum: {name}")


def verify_bundle(bundle):
    bundle = Path(bundle).resolve()
    if not (bundle / "bundle_manifest.json").is_file():
        raise FileNotFoundError("Bundle not prepared. Run: python run_local.py prepare")
    manifest = json.loads((bundle / "bundle_manifest.json").read_text())
    validate_manifest(manifest)
    for name, entry in manifest["files"].items():
        path = bundle / name
        if not path.resolve().is_relative_to(bundle):
            raise ValueError(f"Path escapes extracted bundle: {name}")
        if (
            not path.is_file()
            or path.stat().st_size != entry["bytes"]
            or sha(path) != entry["sha256"]
        ):
            raise ValueError(
                f"Missing/modified bundle file: {name}. Restore it from the original ZIP."
            )
    print("All bundle files passed SHA256 verification.", flush=True)
    return manifest


def prepare(archive, bundle):
    archive, bundle = Path(archive).resolve(), Path(bundle).resolve()
    if not archive.is_file():
        raise FileNotFoundError(f"ZIP not found: {archive}. Use --archive /path/to/file.zip")
    sums = archive.parent / "SHA256SUMS.txt"
    if sums.is_file():
        expected = []
        for line in sums.read_text().splitlines():
            fields = line.split(maxsplit=1)
            if len(fields) == 2 and fields[1].lstrip("*") == archive.name:
                expected.append(fields[0])
        if len(expected) > 1:
            raise ValueError("Ambiguous ZIP checksum entries")
        if expected:
            print("Verifying ZIP checksum...", flush=True)
            if sha(archive) != expected[0]:
                raise ValueError(
                    "ZIP checksum mismatch; download the complete original archive again."
                )
    if bundle.exists() and any(bundle.iterdir()):
        manifest = verify_bundle(bundle)
        with zipfile.ZipFile(archive) as z:
            if json.loads(z.read("bundle_manifest.json")) != manifest:
                raise ValueError(
                    "Existing extraction belongs to another ZIP. Choose a new --bundle path."
                )
        print("Existing verified extraction reused:", bundle)
        return manifest
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP entries")
        for info in z.infolist():
            mode = info.external_attr >> 16
            if not safe_name(info.filename) or (mode & 0o170000) == 0o120000:
                raise ValueError(f"Unsafe ZIP entry: {info.filename}")
        manifest = json.loads(z.read("bundle_manifest.json"))
        validate_manifest(manifest)
        if set(names) != set(manifest["files"]) | {"bundle_manifest.json"}:
            raise ValueError("ZIP entries and manifest differ")
        needed = sum(i.file_size for i in z.infolist())
        bundle.parent.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(bundle.parent).free < needed + (2 << 30):
            raise RuntimeError(
                f"Not enough disk: extraction requires {needed / 2**30:.1f} GiB plus working space."
            )
        bundle.mkdir(exist_ok=True)
        for info in z.infolist():
            if info.filename == "bundle_manifest.json":
                continue
            target = bundle / info.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256()
            with z.open(info) as src, target.open("wb") as dst:
                for chunk in iter(lambda: src.read(CHUNK), b""):
                    h.update(chunk)
                    dst.write(chunk)
            entry = manifest["files"][info.filename]
            if h.hexdigest() != entry["sha256"] or target.stat().st_size != entry["bytes"]:
                raise ValueError(f"Extracted checksum mismatch: {info.filename}")
            print("Extracted:", info.filename, flush=True)
        # Manifest is the completion marker; write only after successful extraction.
        (bundle / "bundle_manifest.json").write_bytes(z.read("bundle_manifest.json"))
    print("Prepared:", bundle)
    meta = json.loads((bundle / "experiment.json").read_text())
    print("Packaging-session Python:", meta["environment"]["python"])
    print("Packaging-session PyTorch:", meta["environment"]["packages"]["torch"])
    print("These are not necessarily the original inference environment versions.")
    print("Next install a CUDA-enabled PyTorch build for your machine, then:")
    print(f'  python -m pip install -r "{bundle / "requirements.txt"}"')
    print("  python run_local.py check")
    return manifest


def dependencies():
    try:
        import torch
        import numpy
        import h5py
        import pandas
        import matplotlib
        import diffusers
        import einops
    except ImportError as e:
        raise RuntimeError(
            "Missing/incompatible dependencies. Install CUDA PyTorch and the extracted requirements.txt in a clean virtual environment. "
            + str(e)
        ) from e
    return torch


def environment(torch, meta):
    flags = meta["environment"]["torch_flags"]
    torch.backends.cuda.matmul.allow_tf32 = flags["matmul_allow_tf32"]
    torch.backends.cudnn.allow_tf32 = flags["cudnn_allow_tf32"]
    torch.backends.cudnn.benchmark = flags["cudnn_benchmark"]
    torch.backends.cudnn.deterministic = flags["cudnn_deterministic"]
    torch.use_deterministic_algorithms(
        flags["deterministic_algorithms"], warn_only=flags["deterministic_warn_only"]
    )
    packages = {name: importlib.metadata.version(name) for name in meta["environment"]["packages"]}
    return {
        "python": platform.python_version(),
        "system": platform.system(),
        "packages": packages,
        "cuda": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "gpu": torch.cuda.get_device_name() if torch.cuda.is_available() else None,
        "torch_flags": flags,
    }


def check(bundle, require_cuda=True):
    manifest = verify_bundle(bundle)
    meta = json.loads((bundle / "experiment.json").read_text())
    if meta["inference"]["mode"] != "full" or meta["inference"]["seed"] != 42:
        raise RuntimeError("This runner expects the full-volume, seed-42 experiment.")
    torch = dependencies()
    local = environment(torch, meta)
    print("Python:", local["python"], "| PyTorch:", torch.__version__)
    print("Recorded environment provenance:", meta["environment"]["note"])
    for name, version in local["packages"].items():
        recorded = meta["environment"]["packages"][name]
        if version != recorded:
            print(f"Environment difference: {name}: local={version}, packaging={recorded}")
    if torch.cuda.is_available():
        print(
            "GPU:",
            torch.cuda.get_device_name(),
            "| VRAM GiB:",
            round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1),
        )
    elif require_cuda:
        raise RuntimeError(
            "CUDA is unavailable. Full inference requires a suitable NVIDIA GPU and CUDA-enabled PyTorch; this runner does not substitute CPU/MPS or tiled inference."
        )
    print("File/dependency check passed. GPU memory capacity is not verified until inference runs.")
    return manifest, meta, torch, local


def copy_inputs(bundle, output, manifest):
    bundle, output = Path(bundle).resolve(), Path(output).resolve()
    if output == bundle or output.is_relative_to(bundle):
        raise ValueError("Choose an output folder outside the immutable extracted bundle.")
    output.mkdir(parents=True, exist_ok=True)
    for name, entry in manifest["files"].items():
        if not name.startswith("data/"):
            continue
        src, dst = bundle / name, output / name.removeprefix("data/")
        if not dst.resolve().is_relative_to(output):
            raise ValueError(f"Output input path escapes the run directory: {dst}")
        if dst.is_symlink():
            raise ValueError(f"Refusing to write through output symlink: {dst}")
        if dst.exists():
            if sha(dst) != entry["sha256"]:
                raise ValueError(
                    f"Existing run input differs: {dst}. Choose another --output folder."
                )
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(dst.suffix + ".partial")
        shutil.copyfile(src, tmp)
        if sha(tmp) != entry["sha256"]:
            raise RuntimeError(f"Input copy checksum mismatch: {name}")
        tmp.replace(dst)
        print("Copied input/reference:", dst.name, flush=True)


def load_workflow(bundle):
    code = bundle / "code"
    if (
        "workflow" in sys.modules
        and Path(sys.modules["workflow"].__file__).resolve() != (code / "workflow.py").resolve()
    ):
        raise RuntimeError("Another workflow is already imported. Start a fresh Python process.")
    sys.path.insert(0, str(code))
    sys.path.insert(0, str(code / "vendor/scaled"))
    import workflow

    return workflow


def plot_results(bundle, output):
    import numpy as np
    import pandas as pd
    import h5py
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    times = [5000, 5250, 5500, 5750, 6000]
    expected = [output / "coupled/metrics.csv"] + [
        output / "coupled" / f"state_{t:06d}.h5" for t in times
    ]
    missing = [str(p) for p in expected if not p.is_file()]
    if missing:
        raise FileNotFoundError(
            "No complete local predictions to plot. Run inference first. The shared ZIP contains reference fields, not the original full prediction fields.\n"
            + "\n".join(missing)
        )
    metrics = pd.read_csv(output / "coupled/metrics.csv")
    recorded = pd.read_csv(bundle / "recorded_results/metrics.csv")
    comparison = metrics[["time", "rmse_raw", "mean"]].merge(
        recorded[["time", "rmse_raw", "mean"]], on="time", suffixes=("_local", "_recorded")
    )
    comparison["rmse_difference"] = comparison.rmse_raw_local - comparison.rmse_raw_recorded
    comparison.to_csv(output / "recorded_run_comparison.csv", index=False)
    print(comparison.to_string(index=False))
    # Read a single height slice rather than loading all prediction volumes.
    solid = (
        np.load(bundle / "data/inputs/sigma.npy", mmap_mode="r", allow_pickle=False).squeeze()[7]
        != 0
    )
    pred, ref = [], []
    for t in times:
        with h5py.File(output / "coupled" / f"state_{t:06d}.h5") as f:
            pred.append(f["C"][7])
        with h5py.File(bundle / "data/physical" / f"C_{t:06d}.h5") as f:
            ref.append(f["C"][7])
    upper = max(1e-6, max(float(np.quantile(a[~solid], 0.995)) for a in pred + ref))
    limit = max(
        1e-6, max(float(np.quantile(np.abs(a - b)[~solid], 0.995)) for a, b in zip(pred, ref))
    )
    fig, axes = plt.subplots(3, 5, figsize=(20, 12), layout="constrained")
    for i, t in enumerate(times):
        for r, a in enumerate([ref[i], pred[i], pred[i] - ref[i]]):
            im = axes[r, i].imshow(
                np.ma.masked_where(solid, a),
                origin="upper",
                cmap="magma" if r < 2 else "RdBu_r",
                vmin=0 if r < 2 else -limit,
                vmax=upper if r < 2 else limit,
            )
            axes[r, i].set_title(
                f"{['Physical reference', 'Coupled prediction', 'Prediction - reference'][r]}: {t}"
            )
            axes[r, i].set_xticks([])
            axes[r, i].set_yticks([])
            if i == 4:
                fig.colorbar(im, ax=axes[r, :], shrink=0.65, label="concentration")
    fig.savefig(output / "pollution_comparison.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(metrics.time, metrics.rmse_raw, label="Coupled prediction")
    ax.plot(metrics.time, metrics.persistence_rmse_raw, label="Persistence")
    ax.set(xlabel="Time index", ylabel="Fluid-only concentration RMSE")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.savefig(output / "rmse_comparison.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("Figures and recorded-run comparison saved to:", output)


def run(bundle, output):
    import gc

    manifest, meta, torch, local = check(bundle)
    output = output.resolve()
    if output == bundle or output.is_relative_to(bundle):
        raise ValueError("--output must be outside the extracted bundle.")
    # Validate referenced checkpoint paths before loading any trusted pickle payload.
    for name in meta["weights"].values():
        if name not in manifest["files"] or not name.startswith("weights/"):
            raise ValueError("Weight path not in verified bundle manifest")
    output.mkdir(parents=True, exist_ok=True)
    guard = {
        "bundle_manifest_sha256": sha(bundle / "bundle_manifest.json"),
        "environment": local,
        "mode": meta["inference"]["mode"],
        "amp": meta["inference"]["amp"],
    }
    marker = output / "local_environment.json"
    if marker.exists() and json.loads(marker.read_text()) != guard:
        raise RuntimeError(
            "Bundle or local runtime differs from this existing run. Use a new --output directory; do not mix environments in a resumed rollout."
        )
    # Space for absent input/reference copies and conservative uncompressed outputs.
    copy_bytes = sum(
        v["bytes"]
        for k, v in manifest["files"].items()
        if k.startswith("data/") and not (output / k.removeprefix("data/")).exists()
    )
    remaining = sum(
        not (output / "coupled" / f"state_{t:06d}.h5").exists() for t in range(5000, 6001, 50)
    )
    reserve = remaining * 64 * 1024 * 1024 * 4 + (3 << 30)
    if shutil.disk_usage(output).free < copy_bytes + reserve:
        raise RuntimeError(
            f"Insufficient output disk. Allow approximately {(copy_bytes + reserve) / 2**30:.1f} GiB additional free space."
        )
    marker.write_text(json.dumps(guard, indent=2) + "\n")
    copy_inputs(bundle, output, manifest)
    wf = load_workflow(bundle)
    weights = {k: bundle / name for k, name in meta["weights"].items()}
    print(
        "Loading verified weights. Full-volume inference is unchanged from the bundled workflow.",
        flush=True,
    )
    models = None
    try:
        models = wf.load_models(
            weights["wind"], weights["wind_vae"], weights["pollution"], weights["pollution_vae"]
        )
        print("Pollution concentration cap:", models[3].cap, flush=True)
        wf.run_coupled(
            output,
            models,
            settings={
                "weights": {k: sha(v) for k, v in weights.items()},
                "seed": 42,
                "save_full_wind": False,
                "local_environment_sha256": sha(marker),
            },
            mode=meta["inference"]["mode"],
            amp=meta["inference"]["amp"],
            save_wind=False,
        )
    except torch.cuda.OutOfMemoryError:
        raise RuntimeError(
            "GPU memory exhausted. Use a higher-memory NVIDIA GPU (the author ran on A100). No CPU, tiled or reduced-precision fallback was applied. Existing completed checkpoints remain in the output folder."
        ) from None
    finally:
        del models
        gc.collect()
        torch.cuda.empty_cache()
    plot_results(bundle, output)
    print(
        "Reproduction finished. Scientific accuracy still requires evaluation; the recorded experiment underpredicts concentration."
    )


def main(argv=None):
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "check", "run", "plot"])
    parser.add_argument(
        "--archive", type=Path, default=base / "wind_pollution_reproduction_bundle.zip"
    )
    parser.add_argument("--bundle", type=Path, default=base / "wind_pollution_reproduction_bundle")
    parser.add_argument("--output", type=Path, default=base / "local_results")
    args = parser.parse_args(argv)
    args.bundle = args.bundle.resolve()
    args.output = args.output.resolve()
    if args.action == "prepare":
        prepare(args.archive, args.bundle)
    elif args.action == "check":
        check(args.bundle)
    elif args.action == "run":
        run(args.bundle, args.output)
    else:
        verify_bundle(args.bundle)
        plot_results(args.bundle, args.output)


if __name__ == "__main__":
    main()
