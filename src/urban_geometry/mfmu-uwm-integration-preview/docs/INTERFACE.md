# Urban World Model integration interface

## Input

`mfmu_scheduler.schedule()` accepts one JSON-compatible dictionary.

### Stations and network

```json
{
  "horizon_slots": 240,
  "stations": [
    {"id": "hub-west", "x": 0.0, "y": 0.0, "role": "hub"},
    {"id": "station-a", "x": 1.0, "y": 0.0, "role": "station"}
  ],
  "travel_time_slots": [[0, 1], [1, 0]],
  "distance_km": [[0.0, 0.8], [0.8, 0.0]]
}
```

Station and UAV identifiers may be strings. The adapter maps them to the one-based station labels and zero-based UAV indices used internally. Coordinates are retained for label-invariant physical identities.

`travel_time_slots` and `distance_km` must be finite, non-negative square matrices in the same station order. Their diagonals must be zero. `distance_cost` may be supplied instead of `distance_km` when a non-geometric cost matrix is intended.

### Fleet

```json
{
  "fleet": [
    {"id": "uav-01", "start_station": "hub-west", "initial_soc": 75}
  ]
}
```

The current battery ledger assumes a homogeneous initial SoC of 75.

### Paired requests

```json
{
  "requests": [
    {
      "id": "request-001",
      "collection_station": "station-a",
      "dropoff_station": "station-b",
      "collection_slot": 10,
      "dropoff_service_window": [11, 15],
      "eligible_uavs": ["uav-01", "uav-02"]
    }
  ]
}
```

The first drop-off service slot must equal:

```text
collection_slot + travel_time_slots[collection_station, dropoff_station]
```

The frozen E2 contract then permits five consecutive drop-off service slots. `eligible_uavs` is optional and defaults to the whole fleet.

### Battery model

```json
{
  "battery": {
    "max_soc": 75,
    "initial_soc": 75,
    "energy_per_flight_slot": 4,
    "reserve": 0,
    "swap_duration_slots": 2,
    "swap_completion_soc": 75
  }
}
```

The adapter rejects different values instead of silently running outside the validated battery semantics.

## Output

The returned object uses `schema_version = "mfmu.schedule-result.v1"` and contains:

- `assignments`: external request/UAV IDs, collection slot, selected drop-off service slot, and action kind;
- `journeys`: complete ordered segments with station IDs, time slots, battery states, optional swap data, and a post-drop-off safe-Hub certificate;
- `validation`: closure, accepted/rejected counts, hard-violation count, independent replay, and dry-run/commit equality;
- `diagnostics`: backend identity, global rounds, run seed, provenance counts, controller counters, and null-control information.

The adapter sorts external UAV and request IDs before assigning internal indices, so reordering those JSON arrays does not change their canonical identities. The result also reports `port_parity_status=NOT_ESTABLISHED` and `q10000_claim_applies_to_this_run=false`: the upstream sealed result is background evidence, not automatic validation of a new custom scenario or this integration refactor.

When `diagnostics.mean_field_policy_consumed_count` is zero, the schedule must not be described as a realised Mean-field-guided owner allocation.

## Proposed group boundary

The Urban World Model may provide station geometry, travel matrices, fleet state, paired requests, and battery/resource settings through this adapter. MFMU returns assignments and complete journey timelines suitable for downstream transport visualisation, simulation, or auditing. The scheduler does not own the upstream urban geometry model or downstream renderer.
