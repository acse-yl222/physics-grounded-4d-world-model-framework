"""Export certified scheduler results as protocol-v1.1 delivery time series.

This adapter preserves the solver's validation receipts and checks their structural
consistency. It does not independently prove those receipts or fabricate UAV flight
coordinates. A safe-hub certificate is not a recorded return journey.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from common.contract import validate
from common.storage import scene_id


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _slot(value: Any, label: str) -> int:
    _require(type(value) is int and 0 <= value <= 240, f"{label} must be an integer slot in [0,240]")
    return value


def _index(rows: Any, key: str, label: str) -> dict[str, dict]:
    _require(isinstance(rows, list), f"{label} must be a list")
    result = {}
    for row in rows:
        _require(isinstance(row, dict), f"{label} entries must be objects")
        identity = row.get(key)
        _require(isinstance(identity, str) and bool(identity), f"{label} requires nonempty string {key}")
        _require(identity not in result, f"duplicate {label} ID: {identity}")
        result[identity] = row
    return result


def _delivery_events(scenario: dict, result: dict) -> Counter:
    """Check the public v1 result contract and use committed drop-off service slots."""
    _require(result.get("schema_version") == "mfmu.schedule-result.v1", "unsupported scheduler result schema")
    _require(result.get("scenario_id") == scenario.get("scenario_id"), "result scenario_id differs from scenario")
    validation = result.get("validation", {})
    _require(isinstance(validation, dict), "missing result validation")
    for field in ("committable", "global_closure", "independent_replay_pass", "dry_run_equals_commit"):
        _require(validation.get(field) is True, f"result is not certified: {field}")
    _require(type(validation.get("hard_violation_count")) is int and validation["hard_violation_count"] == 0,
             "result has missing or nonzero hard_violation_count")
    diagnostics = result.get("diagnostics", {})
    _require(isinstance(diagnostics, dict) and diagnostics.get("stop_reason") == "GLOBAL_CLOSURE", "result did not reach GLOBAL_CLOSURE")
    digest = _sha(json.dumps(scenario, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
    _require(diagnostics.get("input_sha256") == digest, "result input_sha256 does not match the scenario")
    requests = _index(scenario.get("requests"), "id", "requests")
    fleet = _index(scenario.get("fleet"), "id", "fleet")
    stations = _index(scenario.get("stations"), "id", "stations")
    assignments = _index(result.get("assignments"), "request_id", "assignments")
    journeys = _index(result.get("journeys"), "request_id", "journeys")
    _require(assignments.keys() == journeys.keys(), "assignments and journeys do not match")
    _require(assignments.keys() <= requests.keys(), "result contains unknown requests")
    for field in ("accepted", "rejected"):
        _require(type(validation.get(field)) is int and validation[field] >= 0, f"invalid validation.{field}")
    _require(validation["accepted"] == len(assignments), "accepted count differs from committed assignments")
    _require(validation["accepted"] + validation["rejected"] == len(requests), "accepted/rejected counts do not cover input requests")
    events: Counter = Counter()
    owner_journeys: dict[str, list[dict]] = {}
    for identity, assignment in assignments.items():
        journey, request = journeys[identity], requests[identity]
        owner = assignment.get("uav_id")
        _require(owner in fleet and journey.get("uav_id") == owner, "assignment/journey owner mismatch")
        _require(owner in request.get("eligible_uavs", fleet), "assigned UAV is ineligible")
        collection = _slot(assignment.get("collection_slot"), "collection_slot")
        service = _slot(assignment.get("dropoff_service_slot"), "dropoff_service_slot")
        _require(collection == request.get("collection_slot") and collection <= service, "invalid collection/service timing")
        _require(journey.get("dropoff_service_slot") == service, "assignment/journey service mismatch")
        _require(isinstance(assignment.get("action_kind"), str) and assignment["action_kind"] == journey.get("action_kind"),
                 "assignment/journey action mismatch")
        _require(journey["action_kind"] in ("DIRECT_ORDER", "RECHARGE_THEN_ORDER"), "unknown journey action_kind")
        _require(isinstance(journey.get("journey_digest"), str) and re.fullmatch(r"[a-f0-9]{64}", journey["journey_digest"]) is not None,
                 "missing journey digest")
        window = request.get("dropoff_service_window")
        if window is not None:
            _require(isinstance(window, list) and len(window) == 2 and window[0] <= service <= window[1], "service outside request window")
        segments = journey.get("segments")
        _require(isinstance(segments, list) and bool(segments), "committed journey has no segments")
        previous = None
        collection_events = []
        delivery_events = []
        for segment in segments:
            _require(isinstance(segment, dict), "invalid journey segment")
            begin = _slot(segment.get("slot_from"), "segment.slot_from")
            end = _slot(segment.get("slot_to"), "segment.slot_to")
            _require(begin <= end <= service, "segment timing exceeds committed service")
            _require(segment.get("from_station") in stations and segment.get("to_station") in stations, "segment references unknown station")
            _require(type(segment.get("soc_after")) is int and 0 <= segment["soc_after"] <= 75, "invalid segment battery state")
            if segment.get("kind") == "C_SERVICE":
                collection_events.append(segment)
            if segment.get("kind") == "D_SERVICE":
                delivery_events.append(segment)
            if previous is not None:
                _require(begin == previous["slot_to"] and segment["from_station"] == previous["to_station"], "discontinuous journey segments")
            previous = segment
        _require(len(collection_events) == len(delivery_events) == 1, "journey requires exactly one collection and delivery service")
        pickup = collection_events[0]
        _require(pickup["from_station"] == pickup["to_station"] == request.get("collection_station")
                 and pickup["slot_from"] == pickup["slot_to"] == collection, "collection event does not match request")
        delivery = delivery_events[0]
        _require(delivery["from_station"] == delivery["to_station"] == request.get("dropoff_station")
                 and delivery["slot_from"] == delivery["slot_to"] == service, "delivery event does not match assignment")
        post = journey.get("post_state", {})
        _require(isinstance(post, dict) and post.get("station") == request.get("dropoff_station") and post.get("slot") == service,
                 "journey post_state differs from drop-off")
        _require(previous["slot_to"] == service and previous["to_station"] == request.get("dropoff_station"), "journey does not end at committed drop-off")
        _require(type(post.get("soc")) is int and post["soc"] == previous["soc_after"], "post_state battery differs from final segment")
        certificate = journey.get("safe_hub_certificate", {})
        _require(isinstance(certificate, dict) and certificate.get("hub") in stations
                 and stations[certificate["hub"]].get("role") == "hub", "missing safe-hub certificate")
        _require(type(certificate.get("soc_at_hub")) is int and certificate["soc_at_hub"] >= 0, "invalid safe-hub battery certificate")
        _require(service <= _slot(certificate.get("arrival_row"), "certificate.arrival_row"), "safe-hub arrival precedes service")
        owner_journeys.setdefault(owner, []).append(journey)
        events[service] += 1
    for owner, sequence in owner_journeys.items():
        station = fleet[owner].get("start_station")
        earliest = 0
        for journey in sorted(sequence, key=lambda j: j["dropoff_service_slot"]):
            first = journey["segments"][0]
            _require(first["slot_from"] >= earliest and first["from_station"] == station, "inconsistent consecutive UAV journeys")
            station, earliest = journey["post_state"]["station"], journey["post_state"]["slot"]
    return events


def _source_snapshot(destination: Path) -> str:
    """Hash the actual module bytes, regardless of a caller's Git cwd or install."""
    root = Path(__file__).resolve().parent
    paths = sorted(root.rglob("*.py"))
    metadata = sorted({*root.glob("SOURCE_MANIFEST*"), *root.glob("NOTICE*")})
    _require(any(p.name.startswith("SOURCE_MANIFEST") for p in metadata), "module SOURCE_MANIFEST is missing")
    _require(any(p.name.startswith("NOTICE") for p in metadata), "module NOTICE is missing")
    items = []
    for path in [*paths, *metadata]:
        _require(path.is_file() and not path.is_symlink(), "source snapshot requires regular source files")
        name = "uav_scheduling/" + path.relative_to(root).as_posix()
        items.append((name, path.read_bytes()))
    source_digest = hashlib.sha256()
    for name, data in sorted(items):
        source_digest.update(name.encode() + b"\0" + data + b"\0")
    with ZipFile(destination, "x", compression=ZIP_DEFLATED) as archive:
        for name, data in sorted(items):
            entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
    return "sha256:" + source_digest.hexdigest()


def export_run(run_directory: Path, scenario: dict, result: dict, *, context: dict, parameters: dict) -> Path:
    """Write a fresh self-contained run; refuse overwrite or an uncertified result.

    ``context`` explicitly supplies ``scene_id``, protocol ``spatial`` metadata and
    positive finite ``slot_seconds``. Optional ``epoch`` is an ISO UTC start time.
    A station-only schedule cannot establish a 3D trajectory: this export therefore
    exposes only cumulative committed deliveries at actual drop-off event times.
    """
    target = Path(run_directory)
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"run directory already exists: {target}")
    _require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", target.name) is not None, "invalid run directory name")
    _require(isinstance(context, dict) and isinstance(parameters, dict), "context and parameters must be JSON objects")
    _require(isinstance(scenario, dict) and isinstance(result, dict), "scenario and result must be JSON objects")
    _require(isinstance(context.get("scene_id"), str) and re.fullmatch(r"[a-z][a-z0-9_]*", context["scene_id"]) is not None, "explicit scene_id is required")
    canonical_scene = scene_id(context["scene_id"])
    spatial = context.get("spatial")
    _require(isinstance(spatial, dict) and spatial.get("frame") == "ENU" and spatial.get("units") == "m", "explicit spatial ENU/m metadata is required")
    seconds = context.get("slot_seconds")
    _require(type(seconds) in (float, int) and math.isfinite(seconds) and seconds > 0, "slot_seconds must be explicit, positive and finite")
    # Reject non-JSON/nonfinite content before reserving the output directory.
    for document in (scenario, result, context, parameters):
        _json_bytes(document)
    events = _delivery_events(scenario, result)
    slots = sorted({0, *events})
    times = [slot * seconds for slot in slots]
    _require(all(math.isfinite(t) for t in times), "converted event times are nonfinite")
    cumulative = 0
    values = []
    for slot in slots:
        cumulative += events[slot]
        values.append([cumulative])
    clean_result = json.loads(_json_bytes(result))
    clean_result.get("diagnostics", {}).pop("work_directory", None)
    target.mkdir(parents=True, exist_ok=False)
    try:
        (target / "data").mkdir()
        (target / "provenance").mkdir()
        artifacts = []

        def emit(identity: str, relative: str, data: Any) -> str:
            content = _json_bytes(data)
            (target / relative).write_bytes(content)
            digest = _sha(content)
            artifacts.append({"id": identity, "asset": relative, "sha256": digest, "media_type": "application/json"})
            return digest

        scenario_hash = emit("scenario", "data/scenario.json", scenario)
        emit("schedule_result", "data/result.json", clean_result)
        context_hash = emit("context", "provenance/context.json", context)
        parameter_hash = emit("parameters", "provenance/parameters.json", parameters)
        emit("deliveries", "data/deliveries.json", {"labels": ["Committed deliveries"], "values": values})
        emit("export_scope", "provenance/export_scope.json", {
            "input_scene_id": context["scene_id"],
            "canonical_scene_id": canonical_scene,
            "representation": "Cumulative committed delivery events; no inferred 3D trajectories.",
            "validation": "Solver receipts plus exporter consistency checks; not a fresh independent scheduler replay.",
            "omitted_result_fields": ["diagnostics.work_directory"] if "work_directory" in result.get("diagnostics", {}) else [],
            "safe_hub_certificate": "Reachability certificate, not an executed return journey.",
        })
        snapshot = target / "provenance/source_snapshot.zip"
        revision = _source_snapshot(snapshot)
        artifacts.append({"id": "source_snapshot", "asset": "provenance/source_snapshot.zip", "sha256": _sha(snapshot.read_bytes()), "media_type": "application/zip"})
        time = {"unit": "s", "samples": times}
        if "epoch" in context:
            time["epoch"] = context["epoch"]
        manifest = {
            "schema_version": "1.1.0", "scene_id": canonical_scene, "simulation": "nvmf_scheduler",
            "run_id": target.name, "status": "complete", "created_at": datetime.now(timezone.utc).isoformat(),
            "provenance": {"code_revision": revision, "dirty": True, "parameters": parameters,
                           "inputs": [{"id": "scenario", "sha256": scenario_hash}, {"id": "context", "sha256": context_hash},
                                      {"id": "parameters", "sha256": parameter_hash}]},
            "spatial": spatial, "time": time, "artifacts": artifacts,
            "layers": [{"id": "committed_deliveries", "kind": "time_series", "format": "json", "asset": "data/deliveries.json",
                        "sampling": "step", "field": {"name": "cumulative_committed_deliveries", "unit": "1"},
                        "display": {"widget": "time_series", "capabilities": ["pick"]}}],
        }
        provisional = target / "manifest.pending.json"
        provisional.write_bytes(_json_bytes(manifest))
        validate(provisional)
        final = target / "manifest.json"
        provisional.rename(final)
        return final
    except Exception:
        shutil.rmtree(target)
        raise
