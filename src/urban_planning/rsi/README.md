# Urban planning Agent / RSI system v0.1

The executable system has two loops: a task agent selects physical evaluations,
diagnostics and a submitted plan; an updater proposes a versioned replacement for
that agent's planner instructions, updater instructions and reusable memory.
Approved descendants inherit all three. Base-model weights, evaluator, task split,
tool implementation, budgets and promotion rule stay fixed.

This first version evolves **structured instructions and memory**, not arbitrary
Python code, solver code or model weights. It implements the machinery needed to
study recursive self-improvement; running it does not establish an RSI advantage.
The bundled tasks reuse previously inspected solar-pilot data, so they are engineering
acceptance tasks, not fresh independent research tests.

## Run with the existing Claude Code login

Requires Python 3.11+, NumPy and jsonschema, and a logged-in Claude Code CLI supporting
`--safe-mode`, `--tools`, `--json-schema` and `--no-session-persistence`.

```sh
PYTHONPATH=src python3 -m urban_planning.rsi prepare --config project/south_ken/configs/rsi_agent_v01.json
PYTHONPATH=src python3 -m urban_planning.rsi evolve --run RUN_DIRECTORY --provider claude
PYTHONPATH=src python3 -m urban_planning.rsi status --run RUN_DIRECTORY
PYTHONPATH=src python3 -m urban_planning.rsi final --run RUN_DIRECTORY --provider claude
PYTHONPATH=src python3 -m urban_planning.rsi export --run RUN_DIRECTORY --retain
```

Use the directory printed by `prepare`. Storage configuration is respected. An
optional `--model MODEL_ID` selects a Claude model explicitly; otherwise the installed
CLI default is used and the actual model IDs are recorded and checked across calls.
Do not switch provider/model between evolution and final evaluation.

Claude receives only structured task briefs, editable agent state and allowed
feedback. It runs from an empty temporary directory with built-in tools disabled,
customizations disabled, empty MCP configuration, no persisted conversation and a
replacement system prompt. Authentication remains the existing local Claude login.
The controller dispatches declared urban tools to a separate trusted evaluator
process. This is a restricted model interface, **not an OS sandbox for arbitrary
hostile programs**. No generated text is executed as code or commands.

Reference: https://code.claude.com/docs/en/cli-reference .

## Tools and inherited state

- `evaluate`: evaluate a candidate site list; all invalid and duplicate requests cost budget.
- `diagnose`: evaluate and summarize affected receptor fractions and reduction quantiles;
  costs one evaluation and does not register a candidate for submission.
- `submit`: commit a previously evaluated feasible plan (including the empty baseline);
  closes the episode and returns development metrics only.
- Updater output: strict JSON `{revision: {planner, updater, memory}, rationale}`.
  Extra fields, evaluator modifications or malformed structures are rejected.

Every modification records parent ID, content hash, complete revision, text diff,
author provider and rationale. A child is promoted only if it submits valid plans
on all promotion tasks, has no task-score regression, and its mean improvement
exceeds the configured threshold. Ties and failed candidates remain archived.
This small deterministic gate is not statistical evidence of superiority; multiple
lineages, stochastic replication and independent tasks are needed for research.

`--arm fixed_updater` retains the seed updater instructions while allowing planner
changes; `--arm fixed_agent` performs the configured development rounds without
revision. These modes share budget ceilings, but do not automatically consume equal
compute or constitute a completed budget-matched benchmark. Existing conventional
optimization baselines remain in `urban_planning.benchmark`.

## Split isolation and one-shot final evaluation

Development episodes feed the updater. Promotion tasks independently compare parent
and child; their outputs remain in controller logs, not in subsequent model prompts.
The current controller exposes task briefs and development feedback only. Final
scores are withheld even after an episode is submitted. After evolution, the selected
revision and its identities are frozen; all final decisions are made before withheld
scores are calculated. Final scores never re-enter the model. The lifecycle refuses
further evolution or another final evaluation of that run.

The trusted controller/evaluator can read the private prepared input bundle. Model
requests contain neither input file paths nor combined development/holdout arrays.
The original solar pilot's interface remains unchanged; do not use its holdout-revealing
`submit_plan` as a replacement for this runner's `submit`.

The included task suite uses initial constraints for development, changed constraints
for promotion, and initial constraints with the prior temporal holdout for final
scoring. Final task execution can query development data to plan; it cannot query
withheld scores. This is correlated, already-inspected data, explicitly unsuitable
for claims of unseen-weather or unseen-city generalization.

## Costs, failures and reproducibility

`events.jsonl` logs every model request/response, physical-tool result, error,
episode and promotion. `state.json` records total requests, reported tokens,
evaluation requests and elapsed provider/evaluator time. Empty baseline and final
scoring also count in total evaluator requests. Episode budgets apply to requested
candidate evaluations and diagnostics. Invalid requests never create a free search.

`model_calls` counts provider invocations; a Claude invocation can contain multiple
internal CLI turns. CLI turn counts and model usage are recorded per response.
Claude input totals include cache creation/read tokens. `reported_cost_usd` is the
CLI's reported list-price estimate, **not the actual subscription bill**. Missing
usage/cost is explicitly counted as unknown rather than imputed to zero.

Request/evaluation counts have hard caps; per-response output is capped. The total
reported-token limit is checked before each next request, so a request can overshoot
the total limit; it is not a preflight tokenizer-based hard spend limit. Provider
calls have timeouts; failures are logged and never silently replaced by scripted
answers. Failed runs remain inspectable; prepare a new run rather than resuming an
incompletely committed generation. There is no automatic retry or model fallback.

Input/configuration and evaluator/runner source identities are checked. Source
snapshots and compact physical inputs are retained. The export contains all lineage
artifacts and uses the existing protocol-v1.1 static time-series widget for per-task
final metrics. It does not fabricate a physical time axis or publish scene data.
Changing source while a run is active intentionally invalidates it.

`--provider fixture` uses explicitly scripted responses for offline integration tests;
its exports are labelled as such. It is not an LLM run and cannot establish improvement.
An optional `--provider responses --model MODEL_ID` supports a Responses API endpoint,
using an environment key and JSON-schema outputs; no dependency on the OpenAI SDK.
Reference: https://developers.openai.com/api/docs/guides/structured-outputs .

## Validation

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_rsi_agent.py' -v
python3 tools/check_contract.py RUN_DIRECTORY/export/manifest.json
```

Tests use synthetic data and labelled model fixtures. They check successful inheritance,
rejected revisions, final-score isolation, one-shot evaluation, tampering, failed calls,
cost charging, diagnostics and subprocess execution. The separate live Claude run
validates the real CLI transport and control flow; neither replaces scientific controls.

## Repeated curriculum experiments (v0.2)

`urban_planning.rsi.curriculum` constructs three levels of deterministic option and
constraint tasks from retained solar inputs. `urban_planning.rsi.batch` runs two
independent model-call lineages, carrying only approved frozen revisions forward.
Each promotion compares two parent and two candidate episodes, alternating order;
task means must not regress. Final selected and original fixed agents each receive
two repetitions. All three stages in a lineage freeze before its final evaluations.
These repetitions are not independent cities, and the gate is not a significance test.

The recorded protocol is `docs/framework/rsi-curriculum-experiment-plan.md`.
`urban_planning.rsi_curriculum_analysis` performs controller-only analysis after
completion, including all failed attempt costs and a post-hoc exhaustive test ceiling.
The initial 4,096-token updater limit caused recorded L2 failures; the explicit
`rsi_curriculum_recovery` procedure reuses untested frozen L1 versions and raises new
L2/L3 output capacity to 16,384. `rsi_curriculum_retry` allows exactly one documented
retry for the observed zero-output structured-response failure. Neither procedure
uses final feedback or changes physical budgets, scoring or promotion thresholds.
Their retained failure evidence must accompany any result or cost report.

After the recorded batch completed and all six runs were retained, the default
output capacity was raised to 16,384 for future runs. Transport exceptions without
a response now increment both unknown-usage and unknown-cost counters. Historical
run snapshots preserve the exact earlier engine; no archived scores were rerun or
rewritten using these post-batch repairs. Structured-response failures still terminate
the current episode/update and are recorded, not silently retried.
