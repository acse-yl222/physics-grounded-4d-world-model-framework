# Limitations and evidence boundary

This repository is an experimental integration preview derived from source commit `fa1f47994659550586748888c9d6323ac9f1fa83`. It is not a production scheduler, a flight-safety component, or a validated continuous-motion planner.

## Evidence boundary

The upstream sealed SH64/Q10000 run reached global closure after 28 rounds, committed 10,000/10,000 requests under the frozen proxy contract, recorded zero final hard violations, and passed independent replay. All 10,000 final owners nevertheless used `NO_INNER_SIGNAL_UNIFORM_OWNER_LOTTERY`. Consequently, that run does not establish a realised Mean-field owner-guidance benefit.

The upstream result does not automatically validate this refactored package or a new Urban World Model scenario. Package outputs therefore report:

```text
port_parity_status = NOT_ESTABLISHED
input_scope = CUSTOM_SCENARIO_UNVALIDATED
q10000_claim_applies_to_this_run = false
```

## Model scope

- The service horizon is fixed at 240 discrete slots.
- Inputs use a static initial fleet at row 0.
- The frozen battery proxy uses integer SoC 75, four units per flight slot, zero additional reserve, and a two-slot swap restoring SoC to 75.
- Hub swap service and order endpoints are non-binding capacity proxies; UAV-time rows remain exclusive.
- Output journey segments are scheduling records, not obstacle-aware continuous 3D trajectories.
- Wind, weather, no-fly zones, communications, uncertainty, collision avoidance, charger inventory, and battery degradation are outside this snapshot.
- A post-drop-off safe-Hub object is a feasibility certificate; it does not necessarily materialise that return flight.

## Claims not established

The available evidence does not establish global optimality, general convergence, real-time performance, production reliability, or superiority over another scheduler. It also does not establish improved service rate, journey quality, energy use, runtime, or global closure speed caused by the Mean-field Inner.

Public visibility is for inspection only and does not make this an open-source release. Confirm intellectual-property, third-party-code, and licensing permissions before any reuse or redistribution beyond GitHub's public-repository functionality.
