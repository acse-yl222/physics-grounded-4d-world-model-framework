"""Translate a small Urban World Model JSON contract into the frozen E2 schema."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import numpy as np

from experiments import sh64_bat2_ledger as battery

K_SERVICE = 240
K_STATE = K_SERVICE + 1


class ScenarioError(ValueError):
    """Raised when an integration scenario violates the frozen scheduler contract."""


@dataclass(frozen=True)
class ScenarioMaps:
    station_external: tuple[str, ...]
    uav_external: tuple[str, ...]
    order_external: tuple[str, ...]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ScenarioError(message)


def _square_matrix(value: Any, size: int, name: str, *, integer: bool) -> np.ndarray:
    dtype = np.int64 if integer else np.float64
    arr = np.asarray(value, dtype=dtype)
    _require(arr.shape == (size, size), f"{name} must have shape [{size}, {size}]")
    _require(bool(np.isfinite(arr).all()), f"{name} contains a non-finite value")
    _require(bool((arr >= 0).all()), f"{name} contains a negative value")
    _require(bool((np.diag(arr) == 0).all()), f"{name} diagonal must be zero")
    return arr


def build_runtime(scenario: dict[str, Any]):
    """Return ``(fx, authority, policy, maps)`` for the source-faithful controller.

    The adapter deliberately keeps the validated E2 assumptions: a 240-slot service
    horizon, homogeneous 75-unit batteries, four energy units per flight slot, a
    two-slot swap, and a five-slot drop-off service window beginning at physical
    collection-to-drop-off arrival.
    """

    _require(isinstance(scenario, dict), "scenario must be a JSON object")
    _require(int(scenario.get("horizon_slots", K_SERVICE)) == K_SERVICE,
             "the current research snapshot requires horizon_slots=240")

    stations = scenario.get("stations")
    _require(isinstance(stations, list) and len(stations) >= 2,
             "stations must contain at least two entries")
    station_ids = [str(row.get("id")) for row in stations]
    _require(len(set(station_ids)) == len(station_ids), "station IDs must be unique")
    station_index = {sid: idx + 1 for idx, sid in enumerate(station_ids)}
    coordinates = np.asarray([[float(row["x"]), float(row["y"])] for row in stations], dtype=float)
    _require(bool(np.isfinite(coordinates).all()), "station coordinates must be finite")
    hubs = [idx + 1 for idx, row in enumerate(stations) if str(row.get("role", "station")).lower() == "hub"]
    _require(bool(hubs), "at least one station must have role='hub'")

    m = len(stations)
    travel = _square_matrix(scenario.get("travel_time_slots"), m, "travel_time_slots", integer=True)
    distance_data = scenario.get("distance_cost", scenario.get("distance_km", travel.tolist()))
    distance = _square_matrix(distance_data, m, "distance_cost", integer=False)

    fleet = scenario.get("fleet")
    _require(isinstance(fleet, list) and fleet, "fleet must contain at least one UAV")
    fleet = sorted(fleet, key=lambda row: str(row.get("id")))
    uav_ids = [str(row.get("id")) for row in fleet]
    _require(len(set(uav_ids)) == len(uav_ids), "UAV IDs must be unique")
    uav_index = {uid: idx for idx, uid in enumerate(uav_ids)}

    battery_cfg = dict(scenario.get("battery", {}))
    b_max = int(battery_cfg.get("max_soc", 75))
    b_init = int(battery_cfg.get("initial_soc", 75))
    energy = int(battery_cfg.get("energy_per_flight_slot", 4))
    reserve = int(battery_cfg.get("reserve", 0))
    swap_slots = int(battery_cfg.get("swap_duration_slots", 2))
    swap_soc = int(battery_cfg.get("swap_completion_soc", 75))
    _require((b_max, b_init, energy, reserve, swap_slots, swap_soc) == (75, 75, 4, 0, 2, 75),
             "this snapshot supports only the validated battery proxy: 75/75, energy=4, reserve=0, swap=2->75")
    for row in fleet:
        _require(int(row.get("initial_soc", b_init)) == b_init,
                 "per-UAV initial_soc must equal the homogeneous battery initial_soc")
    try:
        births = np.asarray([station_index[str(row["start_station"])] for row in fleet], dtype=np.int64)
    except KeyError as exc:
        raise ScenarioError(f"unknown fleet start_station: {exc}") from exc

    requests = scenario.get("requests")
    _require(isinstance(requests, list) and requests, "requests must contain at least one paired request")
    requests = sorted(requests, key=lambda row: str(row.get("id")))
    order_ids = [str(row.get("id")) for row in requests]
    _require(len(set(order_ids)) == len(order_ids), "request IDs must be unique")
    orders = []
    for ordinal, row in enumerate(requests, start=1):
        try:
            c = station_index[str(row["collection_station"])]
            d = station_index[str(row["dropoff_station"])]
        except KeyError as exc:
            raise ScenarioError(f"request {order_ids[ordinal - 1]} references an unknown station: {exc}") from exc
        kp = int(row["collection_slot"])
        earliest = kp + int(travel[c - 1, d - 1])
        window = row.get("dropoff_service_window", [earliest, earliest + 4])
        _require(isinstance(window, list) and len(window) == 2,
                 f"request {order_ids[ordinal - 1]} dropoff_service_window must be [first,last]")
        first, last = int(window[0]), int(window[1])
        _require(first == earliest and last == earliest + 4,
                 f"request {order_ids[ordinal - 1]} must use the frozen five-slot window [{earliest},{earliest + 4}]")
        _require(1 <= kp <= K_SERVICE and last <= K_SERVICE,
                 f"request {order_ids[ordinal - 1]} lies outside the 240-slot horizon")
        eligible_external = row.get("eligible_uavs", uav_ids)
        _require(isinstance(eligible_external, list) and eligible_external,
                 f"request {order_ids[ordinal - 1]} requires at least one eligible UAV")
        try:
            eligible = sorted({uav_index[str(uid)] for uid in eligible_external})
        except KeyError as exc:
            raise ScenarioError(f"request {order_ids[ordinal - 1]} references an unknown UAV: {exc}") from exc
        eligible_hubs = sorted({int(births[u]) for u in eligible})
        orders.append({
            "order_id": ordinal,
            "c": c,
            "d": d,
            "k_p": kp,
            "k_d": last,
            "W_D": list(range(first, last + 1)),
            "U_base": eligible,
            "n_U_base": len(eligible),
            "eligible_hubs": eligible_hubs,
        })

    hub_mask = np.zeros(m, dtype=float)
    hub_mask[np.asarray(hubs, dtype=int) - 1] = 1.0
    hard_contract = {
        "ordinary_station_time_capacity": int(scenario.get("ordinary_station_time_capacity", 1)),
        "order_endpoint_footprint_nonbinding": True,
        "hubs_nonbinding": True,
    }
    fx = {
        "N": len(fleet),
        "K": K_STATE,
        "M": m,
        "D_cost": distance,
        "T_steps": travel,
        "station_xz": coordinates,
        "orders": orders,
        "hub_mask": hub_mask,
        "births": births,
        "hubs": hubs,
        "hard_contract": hard_contract,
        "roles": {"hub": hubs, "station": [i for i in range(1, m + 1) if i not in hubs]},
        "axis": "STATE241_ROW0_BIRTH_DIRECT_K",
    }

    authority_payload = {
        "model_id": battery.MODEL_ID,
        "B_max": b_max,
        "B_init": b_init,
        "E_per_slot": energy,
        "reserve": reserve,
        "swap_slots": swap_slots,
        "swap_soc": swap_soc,
        "hubs_1based": hubs,
        "K_service": K_SERVICE,
    }
    authority_digest = hashlib.sha256(
        json.dumps(authority_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    authority = battery.AuthV2(
        battery.MODEL_ID, b_max, b_init, energy, reserve, swap_slots,
        swap_soc, tuple(hubs), K_SERVICE, authority_digest,
    )
    policy = battery.PolicyV2(
        version="BATTERY_POLICY_V2",
        model_id=battery.MODEL_ID,
        battery_extension_enabled=True,
        recharge_variants_enabled=True,
        swap_service_mode="UNBOUNDED_SWAP_SERVICE_PROXY",
        authority_digest=authority_digest,
    ).validate()
    maps = ScenarioMaps(tuple(station_ids), tuple(uav_ids), tuple(order_ids))
    return fx, authority, policy, maps
