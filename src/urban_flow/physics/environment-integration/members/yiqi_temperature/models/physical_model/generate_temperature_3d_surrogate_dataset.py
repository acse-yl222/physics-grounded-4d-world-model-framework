from __future__ import annotations

import json
import gc
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Iterable

import numpy as np

try:
    import torch
except ModuleNotFoundError:
    torch = None

VELOCITY_MODEL_DIR = Path(__file__).resolve().parents[1] / "velocity_calculation"
if str(VELOCITY_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(VELOCITY_MODEL_DIR))

from south_kensington_jupyter import SouthKensingtonConfig
from south_kensington_temperature_3d import Temperature3DScenarioConfig, run_temperature_3d_pipeline


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def write_jsonl(path: Path, records: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def release_memory() -> None:
    gc.collect()
    if torch is not None and torch.cuda.is_available():
        torch.cuda.synchronize()
        torch.cuda.empty_cache()


def default_velocity_cases() -> list[dict[str, object]]:
    return [
        {"velocity_case_id": "v00", "inlet_flow": 0.18, "label": "low"},
        {"velocity_case_id": "v01", "inlet_flow": 0.30, "label": "medium"},
        {"velocity_case_id": "v02", "inlet_flow": 0.42, "label": "high"},
    ]


def default_geometry_cases() -> list[dict[str, object]]:
    return [
        {"geometry_case_id": "g000", "geometry_rotation_deg": 0},
        {"geometry_case_id": "g090", "geometry_rotation_deg": 90},
        {"geometry_case_id": "g180", "geometry_rotation_deg": 180},
        {"geometry_case_id": "g270", "geometry_rotation_deg": 270},
    ]


def default_thermal_cases() -> list[dict[str, object]]:
    return [
        {
            "thermal_case_id": "t00",
            "label": "mild",
            "ambient_temp_c": 23.0,
            "inflow_temp_c": 23.0,
            "cloud_cover_fraction": 0.65,
            "anthropogenic_heat_flux_w_m2": 8.0,
        },
        {
            "thermal_case_id": "t01",
            "label": "baseline",
            "ambient_temp_c": 24.2,
            "inflow_temp_c": 24.2,
            "cloud_cover_fraction": 0.47,
            "anthropogenic_heat_flux_w_m2": 15.0,
        },
        {
            "thermal_case_id": "t02",
            "label": "hot_sunny",
            "ambient_temp_c": 27.0,
            "inflow_temp_c": 27.0,
            "cloud_cover_fraction": 0.20,
            "anthropogenic_heat_flux_w_m2": 22.0,
        },
        {
            "thermal_case_id": "t03",
            "label": "very_hot_urban",
            "ambient_temp_c": 30.0,
            "inflow_temp_c": 30.0,
            "cloud_cover_fraction": 0.10,
            "anthropogenic_heat_flux_w_m2": 30.0,
        },
    ]


def case_complete(case_dir: Path) -> bool:
    required = [
        case_dir / "temperature_fields_3d_c.npy",
        case_dir / "temperature_fields_3d_masked_c.npy",
        case_dir / "temperature_3d_run_summary.json",
    ]
    if any((not path.exists()) or path.stat().st_size == 0 for path in required):
        return False
    try:
        json.loads((case_dir / "temperature_3d_run_summary.json").read_text())
    except json.JSONDecodeError:
        return False
    return True


def generate_temperature_3d_surrogate_dataset(
    dataset_dir: str | Path,
    base_velocity_config: SouthKensingtonConfig | None = None,
    base_temperature_config: Temperature3DScenarioConfig | None = None,
    geometry_cases: list[dict[str, object]] | None = None,
    velocity_cases: list[dict[str, object]] | None = None,
    thermal_cases: list[dict[str, object]] | None = None,
    skip_completed: bool = True,
) -> dict[str, object]:
    dataset_dir = Path(dataset_dir)
    cases_root = dataset_dir / "cases"
    velocity_cache_root = dataset_dir / "velocity_cache"
    velocity_digit_root = dataset_dir / "velocity_digit_outputs"
    cases_root.mkdir(parents=True, exist_ok=True)
    velocity_cache_root.mkdir(parents=True, exist_ok=True)
    velocity_digit_root.mkdir(parents=True, exist_ok=True)

    base_velocity_config = base_velocity_config or SouthKensingtonConfig()
    base_temperature_config = base_temperature_config or Temperature3DScenarioConfig()
    geometry_cases = geometry_cases or default_geometry_cases()
    velocity_cases = velocity_cases or default_velocity_cases()
    thermal_cases = thermal_cases or default_thermal_cases()

    dataset_config = {
        "dataset_dir": str(dataset_dir),
        "n_geometry_cases": len(geometry_cases),
        "n_velocity_cases": len(velocity_cases),
        "n_thermal_cases": len(thermal_cases),
        "expected_cases": len(geometry_cases) * len(velocity_cases) * len(thermal_cases),
        "geometry_cases": geometry_cases,
        "velocity_cases": velocity_cases,
        "thermal_cases": thermal_cases,
        "base_velocity_config": asdict(base_velocity_config),
        "base_temperature_config": asdict(base_temperature_config),
        "cache_strategy": (
            "Velocity is cached once per geometry_rotation_deg and inlet_flow. "
            "The four thermal cases reuse that velocity cache."
        ),
    }
    write_json(dataset_dir / "dataset_config.json", dataset_config)

    manifest: list[dict[str, object]] = []
    generated = 0
    skipped = 0

    for geometry_case in geometry_cases:
        rotation = int(geometry_case["geometry_rotation_deg"])
        geometry_case_id = str(geometry_case["geometry_case_id"])
        for velocity_case in velocity_cases:
            velocity_case_id = str(velocity_case["velocity_case_id"])
            inlet_flow = float(velocity_case["inlet_flow"])
            velocity_key = f"{geometry_case_id}_{velocity_case_id}"
            velocity_cache_dir = velocity_cache_root / velocity_key
            velocity_output_dir = velocity_digit_root / velocity_key
            velocity_config = replace(
                base_velocity_config,
                geometry_rotation_deg=rotation,
                inlet_flow=inlet_flow,
                output_dir=str(velocity_output_dir),
            )

            for thermal_case in thermal_cases:
                thermal_case_id = str(thermal_case["thermal_case_id"])
                case_id = f"case_{geometry_case_id}_{velocity_case_id}_{thermal_case_id}"
                case_dir = cases_root / case_id
                if skip_completed and case_complete(case_dir):
                    print(f"[skip] {case_id}")
                    skipped += 1
                    summary_path = case_dir / "temperature_3d_run_summary.json"
                    summary = json.loads(summary_path.read_text())
                else:
                    print(
                        f"[run] {case_id}: rotation={rotation}, inlet_flow={inlet_flow:.2f}, "
                        f"thermal={thermal_case.get('label', thermal_case_id)}"
                    )
                    temperature_config = replace(
                        base_temperature_config,
                        output_dir=str(case_dir),
                        reuse_velocity_output_dir=str(velocity_cache_dir),
                        ambient_temp_c=float(thermal_case["ambient_temp_c"]),
                        inflow_temp_c=float(thermal_case["inflow_temp_c"]),
                        cloud_cover_fraction=float(thermal_case["cloud_cover_fraction"]),
                        anthropogenic_heat_flux_w_m2=float(
                            thermal_case["anthropogenic_heat_flux_w_m2"]
                        ),
                    )
                    run_outputs = run_temperature_3d_pipeline(
                        velocity_config,
                        temperature_config,
                        keep_outputs=False,
                    )
                    summary = dict(run_outputs["summary"])
                    del run_outputs
                    generated += 1
                    release_memory()

                record = {
                    "case_id": case_id,
                    "case_dir": str(case_dir),
                    "geometry_case_id": geometry_case_id,
                    "geometry_rotation_deg": rotation,
                    "velocity_case_id": velocity_case_id,
                    "inlet_flow": inlet_flow,
                    "velocity_cache_dir": str(velocity_cache_dir),
                    "thermal_case_id": thermal_case_id,
                    "thermal_label": thermal_case.get("label", thermal_case_id),
                    "ambient_temp_c": float(thermal_case["ambient_temp_c"]),
                    "inflow_temp_c": float(thermal_case["inflow_temp_c"]),
                    "cloud_cover_fraction": float(thermal_case["cloud_cover_fraction"]),
                    "anthropogenic_heat_flux_w_m2": float(
                        thermal_case["anthropogenic_heat_flux_w_m2"]
                    ),
                    "temperature_shape": summary.get("temperature_shape"),
                    "velocity_shape": summary.get("velocity_shape"),
                    "cache_reused": bool(summary.get("cache_reused", False)),
                    "temperature_solver_backend_used": summary.get(
                        "temperature_solver_backend_used"
                    ),
                    "summary_path": summary.get(
                        "summary_path", str(case_dir / "temperature_3d_run_summary.json")
                    ),
                }
                write_json(case_dir / "case_metadata.json", record)
                manifest.append(record)
                write_jsonl(dataset_dir / "manifest.jsonl", manifest)
                del record
                release_memory()

    summary = {
        **dataset_config,
        "generated_cases_this_run": generated,
        "skipped_cases_this_run": skipped,
        "manifest_path": str(dataset_dir / "manifest.jsonl"),
    }
    write_json(dataset_dir / "dataset_summary.json", summary)
    return summary
