"""Run the portable, fail-closed integration example from a source checkout."""

import json
from pathlib import Path

from mfmu_scheduler import schedule


HERE = Path(__file__).resolve().parent
scenario = json.loads((HERE / "minimal_scenario.json").read_text())
result = schedule(scenario, run_seed=20260902)
print(json.dumps({
    "assignments": result["assignments"],
    "validation": result["validation"],
    "diagnostics": {
        "backend": result["diagnostics"]["backend"],
        "rounds": result["diagnostics"]["rounds"],
        "mean_field_policy_consumed_count": result["diagnostics"]["mean_field_policy_consumed_count"],
        "uniform_fail_closed_count": result["diagnostics"]["uniform_fail_closed_count"],
    },
}, indent=2))

