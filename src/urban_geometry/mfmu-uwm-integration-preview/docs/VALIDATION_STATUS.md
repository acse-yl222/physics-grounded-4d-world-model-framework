# Validation status

## Sealed E2 campaign

The source snapshot is derived from the closed E2 Global Multiple-Update campaign at commit `fa1f47994659550586748888c9d6323ac9f1fa83`.

Verified campaign-level facts recorded by the sealed closeout include:

- 28 global Outer rounds, indexed 0–27;
- 28 whole-batch Inner executions;
- global closure in round 27;
- 10,000 accepted requests out of 10,000, with zero rejected requests;
- zero final hard-validation violations;
- independent replay passed, including plan consistency and ledger state/event agreement;
- fresh-clone tests passed in normal and optimised Python modes.

## Mean-field attribution

The following final-decision counts were zero:

- `INNER_G_WEIGHTED_DRAW_FINAL_COUNT`;
- `INNER_POLICY_CONSUMED_COUNT`;
- `NON_TIE_INNER_OWNER_COUNT`.

All 10,000 final owner decisions were labelled `NO_INNER_SIGNAL_UNIFORM_OWNER_LOTTERY`.

Accordingly, the campaign validates the MFMU control-flow integration, whole-batch soft-field recomputation, qualification/abstention interface, hard-constrained multiple-update loop, BatteryLedger journey construction, closure, and replay. It does not validate a scheduling benefit caused by non-uniform Mean-field owner guidance.

## Lightweight repository checks

The synthetic tests in this repository are deliberately smaller and data-independent. They verify that the portable interface reaches exact closure, produces complete journeys, commits with zero hard violations, and passes independent replay. Their backend is explicitly labelled `PORTABLE_UNIFORM_FAIL_CLOSED_DEMO`; it is not a scientific Mean-field result.

## Non-claims

Neither the sealed campaign nor this lightweight package establishes:

- global optimality;
- superiority to another scheduler;
- reduced global rounds caused by Mean-field guidance;
- improved journey time, energy, or service rate caused by Mean-field guidance;
- production reliability or a general-purpose battery model.

