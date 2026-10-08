"""Strict integration boundary around the preserved research implementation."""
from __future__ import annotations

import math
from pathlib import Path
import re
import tempfile

from jsonschema import Draft202012Validator, validators


_ID = {"type": "string", "minLength": 1}
_INT = {"type": "integer", "minimum": 0, "maximum": 2**31 - 1}
_NUM = {"type": "number", "minimum": 0}


def _object(properties, required):
    return {"type": "object", "properties": properties,
            "required": required, "additionalProperties": False}


def _array(items, minimum=1):
    return {"type": "array", "items": items, "minItems": minimum}


_SCHEMA = _object({
    "schema_version": {"const": "mfmu.integration.v1"},
    "scenario_id": _ID,
    "horizon_slots": {**_INT, "const": 240},
    "stations": _array(_object({
        "id": _ID, "x": {"type": "number"}, "y": {"type": "number"},
        "role": {"enum": ["hub", "station"]},
    }, ["id", "x", "y", "role"]), 2),
    "travel_time_slots": _array(_array(_INT)),
    "distance_km": _array(_array(_NUM)),
    "distance_cost": _array(_array(_NUM)),
    "fleet": _array(_object({
        "id": _ID, "start_station": _ID, "initial_soc": {**_INT, "const": 75},
    }, ["id", "start_station"])),
    "battery": _object({key: {**_INT, "const": value} for key, value in {
        "max_soc": 75, "initial_soc": 75, "energy_per_flight_slot": 4,
        "reserve": 0, "swap_duration_slots": 2, "swap_completion_soc": 75,
    }.items()}, []),
    "ordinary_station_time_capacity": {**_INT, "minimum": 1},
    "requests": _array(_object({
        "id": _ID, "collection_station": _ID, "dropoff_station": _ID,
        "collection_slot": {**_INT, "minimum": 1, "maximum": 240},
        "dropoff_service_window": {**_array(_INT, 2), "maxItems": 2},
        "eligible_uavs": {**_array(_ID), "uniqueItems": True},
    }, ["id", "collection_station", "dropoff_station", "collection_slot"])),
}, ["schema_version", "horizon_slots", "stations", "travel_time_slots", "fleet", "requests"])
_SCHEMA["oneOf"] = [{"required": ["distance_km"]}, {"required": ["distance_cost"]}]
_Validator = validators.extend(Draft202012Validator, type_checker=(
    Draft202012Validator.TYPE_CHECKER.redefine(
        "integer", lambda _checker, value: type(value) is int)))


def _finite(value):
    if isinstance(value, dict):
        for child in value.values():
            _finite(child)
    elif isinstance(value, list):
        for child in value:
            _finite(child)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            valid = math.isfinite(value)
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError("scenario numbers must be finite and representable")


def validate_scenario(scenario: dict) -> None:
    """Reject coercible/fractional input before entering the frozen adapter."""
    _Validator(_SCHEMA).validate(scenario)
    _finite(scenario)
    from ._vendor.mfmu_scheduler.scenario import build_runtime
    build_runtime(scenario)  # Also checks matrix shape, IDs and the model contract.


def schedule(scenario: dict, *, run_seed: int = 0, backend: str = "mean_field",
             device: str = "cpu", max_rounds: int = 32,
             work_directory: str | Path | None = None) -> dict:
    """Schedule paired requests with an explicit solver and a fresh work directory.

    Default: actual PyTorch mean-field Inner plus global Outer. The explicitly
    selected ``portable_fail_closed`` mode is a uniform integration test only.
    Numerical overrides are intentionally not exposed by this integration API.
    Returns discrete journeys, not obstacle-aware continuous flight trajectories.
    """
    validate_scenario(scenario)
    if type(run_seed) is not int or not 0 <= run_seed < 2**32:
        raise ValueError("run_seed must be an integer in [0, 2**32)")
    if type(max_rounds) is not int or max_rounds < 1:
        raise ValueError("max_rounds must be a positive integer")
    if backend not in ("mean_field", "portable_fail_closed"):
        raise ValueError("backend must be mean_field or portable_fail_closed")
    if not isinstance(device, str) or not re.fullmatch(r"cpu|cuda(?::[0-9]+)?", device):
        raise ValueError("device must be cpu, cuda, or cuda:<index>")
    if backend == "portable_fail_closed" and device != "cpu":
        raise ValueError("the uniform test backend runs on CPU only")
    if backend == "mean_field":
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("Install the scheduler extra: pip install -e '.[scheduler]'") from exc
        if device.startswith("cuda"):
            index = int(device.split(":")[1]) if ":" in device else 0
            if not torch.cuda.is_available() or index >= torch.cuda.device_count():
                raise ValueError(f"CUDA device unavailable: {device}")
    if work_directory is None:
        work = Path(tempfile.mkdtemp(prefix="fieldfleet-"))
    else:
        work = Path(work_directory).absolute()
        work.mkdir(parents=True, exist_ok=False)
    from ._vendor.mfmu_scheduler.api import schedule as core_schedule
    return core_schedule(scenario, run_seed=run_seed, backend=backend, device=device,
                         max_rounds=max_rounds, work_directory=work)
