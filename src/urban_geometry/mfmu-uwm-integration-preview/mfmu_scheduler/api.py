"""Small, explicit integration API around the frozen MFMU/E2 controller."""

from __future__ import annotations

import hashlib
import json
import tempfile
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import numpy as np

from bounded_studies.r3_global_mu_v3r4_batch_judge_v3 import controller
from bounded_studies.r3_global_mu_v3r4_batch_judge_v3 import readout
from .scenario import ScenarioMaps, build_runtime


class SchedulingDidNotClose(RuntimeError):
    """Raised when the bounded global loop does not reach its exact closure gate."""

    def __init__(self, result: dict[str, Any]):
        super().__init__(f"MFMU scheduler did not close: {result}")
        self.result = result


def _uniform_field(inputs: dict[str, Any]) -> np.ndarray:
    n, k, m = int(inputs["N"]), int(inputs["K"]), int(inputs["M"])
    x = np.full((n, k, m), 1.0 / m, dtype=np.float64)
    x[:, 0, :] = inputs["x0s"]
    for (u, row), station in inputs["pins"].items():
        x[int(u), int(row), :] = 0.0
        x[int(u), int(row), int(station)] = 1.0
    return x


def portable_fail_closed_backend(inputs: dict[str, Any]) -> dict[str, Any]:
    """Portable integration backend used only by the tiny example and smoke tests.

    It supplies a finite uniform field, so the qualified-guidance gate abstains and
    the controller exercises the audited uniform fail-closed path. It is not a
    substitute for the Mean-field numerical solver and is labelled accordingly in
    every returned result.
    """

    x = _uniform_field(inputs)
    digest = hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
    return {
        "x": x,
        "x_tail": [x.copy(), x.copy(), x.copy()],
        "x_perm_tail": x.copy(),
        "record": {
            "backend": "PORTABLE_UNIFORM_FAIL_CLOSED_DEMO",
            "closure_state": "READOUT_STABLE_RAW_UNCLOSED",
            "x_sha256": digest,
            "mean_field_numerical_solver_executed": False,
        },
    }


def _mean_field_backend_factory(
    *, run_seed: int, device: str, initial_inputs: dict[str, Any], config_overrides: dict[str, Any] | None
) -> tuple[Callable[[dict[str, Any]], dict[str, Any]], np.ndarray, dict[str, Any]]:
    try:
        from bounded_studies.r3_global_mu_v3r4_batch_judge_v3 import inner
    except ModuleNotFoundError as exc:
        raise RuntimeError("backend='mean_field' requires PyTorch; install the 'mean-field' optional dependency") from exc
    cfg = dict(inner.C0)
    cfg.update(config_overrides or {})
    x_null, null_record = inner.null_solve(initial_inputs, cfg, run_seed, device=device)
    round_id = 0

    def run_inner(inputs: dict[str, Any]) -> dict[str, Any]:
        nonlocal round_id
        out = inner.solve_round(inputs, cfg, run_seed, round_id, device=device)
        round_id += 1
        return out

    return run_inner, x_null, null_record


def _external_journey(raw: dict[str, Any], maps: ScenarioMaps) -> dict[str, Any]:
    def station(internal: int) -> str:
        return maps.station_external[int(internal) - 1]

    return {
        "request_id": maps.order_external[int(raw["order_id"]) - 1],
        "uav_id": maps.uav_external[int(raw["owner"])],
        "dropoff_service_slot": int(raw["k_serv"]),
        "action_kind": raw["action_kind"],
        "swap_station": station(raw["hub"]) if raw.get("hub") is not None else None,
        "swap_start_slot": raw.get("swap_start"),
        "post_state": {
            "station": station(raw["post_state"]["tail_location"]),
            "slot": int(raw["post_state"]["tail_slot"]),
            "soc": int(raw["post_state"]["soc"]),
        },
        "segments": [
            {
                "kind": segment["kind"],
                "from_station": station(segment["origin"]),
                "to_station": station(segment["destination"]),
                "slot_from": int(segment["t_from"]),
                "slot_to": int(segment["t_to"]),
                "soc_after": int(segment["soc_after"]),
            }
            for segment in raw["segments"]
        ],
        "safe_hub_certificate": {
            **raw["certificate"],
            "hub": station(raw["certificate"]["hub"]),
        },
        "journey_digest": raw["digest"],
    }


def schedule(
    scenario: dict[str, Any],
    *,
    run_seed: int = 0,
    backend: str = "portable_fail_closed",
    device: str = "cpu",
    max_rounds: int = 32,
    work_directory: str | Path | None = None,
    inner_config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Schedule one paired-request batch and return integration-friendly JSON data.

    ``backend='portable_fail_closed'`` runs the hard-constrained global controller
    with an explicitly uniform, non-guiding field. ``backend='mean_field'`` runs the
    included PyTorch Mean-field solver and its numerical controls.
    """

    fx, authority, policy, maps = build_runtime(scenario)
    scenario_digest = hashlib.sha256(
        json.dumps(scenario, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    order_ids = [int(order["order_id"]) for order in fx["orders"]]
    initial_inputs = controller.inner_inputs(fx, order_ids, {}, [], {})
    if backend == "portable_fail_closed":
        backend_fn = portable_fail_closed_backend
        x_null = _uniform_field(initial_inputs)
        null_record = {"backend": "ANALYTIC_UNIFORM_DEMO_CONTROL", "mean_field_numerical_solver_executed": False}
    elif backend == "mean_field":
        backend_fn, x_null, null_record = _mean_field_backend_factory(
            run_seed=int(run_seed), device=device, initial_inputs=initial_inputs,
            config_overrides=inner_config_overrides,
        )
    else:
        raise ValueError("backend must be 'portable_fail_closed' or 'mean_field'")

    if work_directory is None:
        work = Path(tempfile.mkdtemp(prefix="mfmu-scheduler-"))
    else:
        work = Path(work_directory)
        work.mkdir(parents=True, exist_ok=True)
    identity = {
        "schema": "MFMU_URBAN_WORLD_INTEGRATION_V1",
        "policy_digest": policy.digest(),
        "authority_digest": authority.authority_digest,
        "backend": backend,
    }
    scheduler = controller.GlobalController(
        fx,
        authority,
        policy,
        backend=backend_fn,
        run_uuid=str(uuid.uuid4()),
        run_seed=int(run_seed),
        work=str(work),
        x_null=x_null,
        identity=identity,
        hard_cap=int(max_rounds),
        log=lambda *_args: None,
    )
    stop = scheduler.run()
    if stop.get("stop") != "GLOBAL_CLOSURE":
        raise SchedulingDidNotClose({"stop": stop, "closure": scheduler.closure_report(), "work_directory": str(work)})
    committed = scheduler.final_commit()
    journeys_raw = sorted(committed["committed_journeys"], key=lambda row: int(row["order_id"]))
    journey_by_order = {int(row["order_id"]): row for row in journeys_raw}
    assignments = []
    for record in sorted(committed["committed_records"], key=lambda row: int(row["oid"])):
        oid = int(record["oid"])
        order = fx["orders"][oid - 1]
        provenance = scheduler.provisional[oid]["provenance"]
        assignments.append({
            "request_id": maps.order_external[oid - 1],
            "uav_id": maps.uav_external[int(record["owner"])],
            "collection_slot": int(order["k_p"]),
            "dropoff_service_slot": int(record["k_serv"]),
            "action_kind": journey_by_order[oid]["action_kind"],
            "owner_provenance": provenance,
        })
    provenance_counts = Counter(row.get("provenance") for row in scheduler.provisional.values())
    return {
        "schema_version": "mfmu.schedule-result.v1",
        "scenario_id": scenario.get("scenario_id"),
        "implementation": {
            "package_version": "0.1.0",
            "derived_from_source_commit": "fa1f47994659550586748888c9d6323ac9f1fa83",
            "port_parity_status": "NOT_ESTABLISHED",
        },
        "evidence_scope": {
            "input_scope": "CUSTOM_SCENARIO_UNVALIDATED",
            "sealed_sh64_input_match": False,
            "q10000_port_parity_verified": False,
            "q10000_claim_applies_to_this_run": False,
        },
        "assignments": assignments,
        "journeys": [_external_journey(row, maps) for row in journeys_raw],
        "validation": {
            "committable": True,
            "global_closure": True,
            "accepted": int(committed["accepted"]),
            "rejected": int(committed["rejected"]),
            "hard_violation_count": int(committed["COMMITTED_BATCH_HARD_VIOLATION_COUNT"]),
            "independent_replay_pass": bool(committed["replay"]["PASS"]),
            "dry_run_equals_commit": bool(committed["match"]),
        },
        "diagnostics": {
            "backend": backend,
            "stop_reason": stop["stop"],
            "rounds": int(stop["rounds"]),
            "run_seed": int(run_seed),
            "input_sha256": scenario_digest,
            "mean_field_policy_consumed_count": int(provenance_counts.get(readout.PROV_WEIGHTED, 0)),
            "uniform_fail_closed_count": int(provenance_counts.get(readout.PROV_UNIFORM, 0)),
            "provenance_counts": dict(provenance_counts),
            "controller_counters": scheduler.counters,
            "null_control": null_record,
            "work_directory": str(work),
            "interpretation": (
                "The portable demo exercises uniform fail-closed scheduling, not Mean-field guidance."
                if backend == "portable_fail_closed"
                else "Mean-field guidance is attributable only where provenance is INNER_G_WEIGHTED_DRAW."
            ),
        },
    }
