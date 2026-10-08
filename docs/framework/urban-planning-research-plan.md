# Tool-using agents for constrained urban planning — research plan

Date: 2026-09-30. Target: Nature Computational Science; acceptance is not assumed.

## Research question

Can an agent organize computational experiments across a fixed urban tool space,
adapt to changed planning constraints, and find independently verified interventions
more efficiently than strong optimization and fixed-workflow baselines?

The framework and its solvers are existing research assets. The new contribution
must be experimentally attributable to task interpretation, diagnostic tool selection,
experiment allocation, or adaptation. A successful tool invocation or attractive map
does not establish that contribution.

## Tool inventory and implementation priorities

| Tool | Existing asset | Required addition | Current status |
| --- | --- | --- | --- |
| Inspect scene/task | Scene metadata, ENU geometry and result manifests | Explicit available actions, fixed constraints and data identities | Pilot implemented: `inspect_task` |
| Propose intervention | Editable geometry and scene parameters | Typed, reversible action records; immutable baseline | Pilot: lists of hypothetical panel site IDs |
| Check feasibility | Geometry/masks | Site exclusions, cost/count budget, overlap, domain-specific constraints | Pilot implemented: `validate_plan`; land rights/access not modeled |
| Solar evaluation | Solar solver, recorded shadows and sun positions | Apply elevated panel occlusion to ground receptors | Pilot implemented; direct beam only |
| Wind/thermal evaluation | Existing field models and adapters | Intervention-aware recalculation, declared coupling, fidelity and validity range | Planned; not exposed as working pilot tools |
| Pollution/traffic evaluation | Tracer solver and traffic code | Emissions/demand intervention adapters and objective definitions | Planned |
| Flood evaluation | Shallow-water solver and terrain | Spatial surface/drainage interventions with physically justified bounds | Planned |
| Diagnostics | Field arrays | Spatial summaries and targeted mechanism tests with charged costs | Pilot only returns objective/constraint metrics; richer diagnostics planned |
| Budget/audit | Framework provenance and run retention | Count all evaluations, preserve decisions, close submitted runs | Implemented in session interface |
| Independent validation | Protocol/numerical checks | Held-out scenarios, resolution study, independent solver/observations | Correlated temporal holdout implemented; stronger checks pending |
| Baselines | No shared planning benchmark | Random, rules, constrained BO, evolutionary search | Random, ranking, local search and GP constrained EI implemented |
| Agent runner | This interactive Codex session | Fixed model/prompt runner, token/runtime logging, repeated episodes | JSON tool interface and one exploratory episode; formal runner pending |
| Result export | Existing five layer types | Export scores/maps/inputs/traces without another viewer | Protocol v1.1 scalar layers implemented |

Reusable code: `src/urban_planning/`. Scene config:
`project/south_ken/configs/planning_solar_pilot.json`. Scratch runs:
`Storage.scratch('south_ken', 'urban_planning', run_id)`. Retained runs follow
the existing protocol. Nothing is published automatically.

## Experimental stages and completion criteria

### E0 — interface and numerical checks (implemented)

Check sun-direction/height geometry, union of overlapping shadows, radiation units,
invalid plans, count/site/winter constraints, exhausted budgets, immutable inputs,
and irreversible submission. Share one evaluator between agent and baselines.
Keep external weather, evaluation parameters and intervention choices separate.

### E1 — South Kensington optical pilot (executed)

Use a 160 x 360 m scene-local window, ground receptors every 4 m excluding buildings,
and 15 geometric candidate sites for 12 x 12 m horizontal opaque panels. The initial
configuration requested 16 sites; preparation found only 15 valid sites, so the
count was reduced before any objective evaluation. No radiation score was used
to generate candidates. Equal unit costs are synthetic, not currency estimates.

Objective: maximize summer direct-ground-irradiation reduction; constrain winter
direct-irradiation loss to 0.5%, at most three panels and three cost units.
Changed task: at most two panels and two cost units; p03 and p08 unavailable.
This change was fixed before scoring, not tailored to observed optimum sites.
Use source-recorded 2026-06-21 and 2026-12-21 intervals from 10:00–16:00 UTC.
Alternate intervals between development and temporal holdout. Do not interpolate
missing frames. This is a correlated time split, not independent weather testing.

The pilot reuses the existing solar model's stored building shadows and sun terms.
Panel occlusion is an analytic ray/plane calculation over the unchanged background.
It does not model diffuse radiation changes, multiple reflections, thermal comfort,
wind, foundations, pedestrian circulation or tree physiology. Receptors are uniform
ground locations, not measured people. Candidate sites are not approved public land.
Legacy background provenance remains `legacy-unrecorded`; the new evaluations can
be replayed from preserved compact inputs without the old external data directory.

Methods: random feasible-structure search (10 seeds), single-site ranking (one
deterministic run), feasible local search (one deterministic run), fixed-kernel
Gaussian-process constrained expected improvement (10 seeds), and one explicitly
exploratory interactive Codex episode. Initial evaluation cap 24, changed cap 12.
Invalid/repeated agent requests consume budget; an empty baseline is free for all.
Deterministic runs are not duplicated to inflate sample counts.

Offline exhaustive enumeration establishes a finite-space reference. It is not
budget matched. Agent submission precedes exhaustive reference computation.
Record actual calls, objective/constraint metrics, regret, and local evaluator time.
The interactive episode has no dependable model snapshot/token-cost record and
cannot support a formal comparative claim. Local evaluator runtime is not total
agent runtime. Only one actual interactive initial-task episode is run.

Completion gate: a valid, replayable result bundle and honest diagnosis of whether
the task distinguishes methods. Do not change constraints after looking at results
and report the revised task as a preregistered confirmation experiment.

### E2 — discriminating task suite (next)

First inspect E1 difficulty. If individual-site screening effectively solves the
problem, add meaningful interactions rather than treating a tie as an agent win.
Candidate extensions: several panel sizes with overlapping shadows and unequal
costs; differently weighted occupied areas backed by explicit assumptions or data;
multiple task briefs; real exclusions of selected sites; and additional recorded
dates/new solar runs. Seasonal deployment must include operating costs so removing
all panels in winter is not a free trivial solution.

Create development/calibration/test task IDs before tuning prompts. Separate whole
dates, spatial patches and weather events, not individual correlated frames. Freeze
objective normalization, constraints, tool visibility and budgets. Use a fixed test
suite after exploratory choices. Add an evolutionary baseline when the intervention
space becomes mixed/discrete and multiobjective; retain strong constrained BO.

Primary endpoint: best independently feasible objective at fixed total compute
budget. Secondary: cost-to-target, feasibility, held-out regret, tool failures,
constraint-change adaptation and human setup effort. Different fidelity calls have
different costs; report GPU/CPU seconds and monetary model costs where available.
Report worst-case and distributional outcomes, not just the best run.

### E3 — reproducible agent cohort and ablations (planned)

Integrate a provider-neutral model runner with an explicitly recorded model version,
system prompt, tool schemas, decoding settings, seeds where supported, full traces,
token usage and failures. Keep planning/evaluator files read-only to the runner;
the current local session identity check is an audit mechanism, not a security
sandbox. Never expose exhaustive or held-out outputs to the planner.

Compare fixed workflow, constrained BO, evolutionary baseline where suitable,
general tool-using agent, and the proposed diagnostic/experiment-selection method.
Distinguish better problem formulation from better numerical search. Ablations:
remove diagnostics, remove adaptive experiment choice, fix fidelity, remove memory
across tasks. Measure whether tools chosen are actually useful, not merely numerous.

Start with 10 independent seeds per stochastic method/task as an exploratory
design, then determine confirmatory replication from observed variance and the
smallest scientifically useful effect; 10 is not a power guarantee. Use paired task
comparisons and confidence intervals clustered by independent scenario. Grid cells
and timesteps are not independent experimental replicates. Include all failures.

### E4 — physical credibility and transfer (planned)

Run spatial sampling/grid refinement, boundary/context sensitivity and independent
shadow geometry checks; add observations targeted to the core claimed mechanism.
Cross-solver agreement is not field validation. Use new South Kensington patches
and White City transfer, then an external city if broad geographic claims are made.
For coupled tasks define interfaces, units, valid parameter ranges and synchronization
before use. Never interpret arbitrary tracer units as measured pollution concentration.

### E5 — manuscript evidence (planned)

Figure 1: task/tools/action/evaluation architecture and South Kensington inputs.
Figure 2: verified physical response and geometry/cost constraints.
Figure 3: quality versus total compute with strong baselines and uncertainty.
Figure 4: changed-task and held-out-scenario performance.
Figure 5: ablations, failure cases and transferable planning insights.

Do not choose only positive outcomes. A finding that strong BO or a rule policy
matches the agent means the method/claim needs revision, not selective reporting.

## Useful context

- [NCS scope](https://www.nature.com/natcomputsci/aims).
- [Spatial planning via deep reinforcement learning, NCS 2023](https://www.nature.com/articles/s43588-023-00503-5).
- [Urban planning in the era of LLMs, NCS Perspective 2025](https://www.nature.com/articles/s43588-025-00846-1).
- [CityPlanner, September 2026 preprint](https://arxiv.org/abs/2609.09578).

## Reproduce the pilot

Use Python 3.11+ with the framework's NumPy/jsonschema dependencies. The first
command needs the existing local `sources.local.json` and preserved South Kensington
solar/terrain files; it fails explicitly if they are absent. Subsequent steps need
only the resulting compact task directory.

```sh
PYTHONPATH=src python3 -m urban_planning prepare --config project/south_ken/configs/planning_solar_pilot.json
PYTHONPATH=src python3 -m urban_planning catalog
PYTHONPATH=src python3 -m urban_planning start --task TASK_DIR --session trial01 --actor ACTOR_ID
PYTHONPATH=src python3 -m urban_planning call --task TASK_DIR --session trial01 --tool inspect_task
PYTHONPATH=src python3 -m urban_planning call --task TASK_DIR --session trial01 --tool evaluate_plan --arguments '{"plan":["p10"]}'
PYTHONPATH=src python3 -m urban_planning call --task TASK_DIR --session trial01 --tool submit_plan --arguments '{"plan":["p10"]}'
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src python3 -m urban_planning benchmark --task TASK_DIR
PYTHONPATH=src python3 -m urban_planning export --task TASK_DIR
python3 tools/check_contract.py TASK_DIR/export/manifest.json
python3 -m unittest discover -s tests -p test_urban_planning.py -v
```

`benchmark` and `export` refuse existing destinations. Begin a new prepared task
when inputs/config/evaluator change. Freeze and submit agent decisions before
running offline reference analysis. `p4d retain` can preserve the complete export;
no existing default scene view is replaced.

## RSI positioning — Recursive Self-Improvement, confirmed 2026-09-30

The user confirmed Recursive Self-Improvement: the agent itself should improve.
This section defines the research narrative and evidence requirements. The research
positioning is confirmed; implementation and experimental RSI claims remain unproven.

### Candidate scientific question

Can verifiable physical feedback help an urban-planning agent improve its reusable
experiment-selection and tool-composition procedures across generations, with
benefits on previously unseen tasks after accounting for the cost of improvement?

The existing solar tool sessions modify intervention lists; traffic/morphology
screening compares scripted policies. Neither creates inherited agent revisions.
The South Kensington screening also found that source-strength ranking matched
the stronger decision rules. These are environment and baseline assets, not RSI
evidence. Current inspected holdouts must become development data for this new study.

### Claims and evidence required

| Claim | Necessary observable evidence | Current status |
| --- | --- | --- |
| Better city plan | Feasible intervention improves a fixed physical objective | Simplified pilots only |
| Agent self-improvement | Agent-authored policy/tool revisions persist and improve unseen-task results | Not implemented |
| Recursive improvement | Descendant agent participates in producing subsequent inherited revisions; parent-child lineage and execution traces establish this | Not implemented |
| Improved improvement mechanism | Evolved revision procedure outperforms the original procedure from matched starting agents and budgets | Not tested |

Do not conflate repeated search, human-written fixes, longer context, retained
answers, or increased compute with recursive improvement. A fixed foundation model
can support software-level self-improvement; model-weight learning is a separate claim.

### Proposed experiment, before implementation

1. Freeze the physical evaluator, units, task generator, feasibility rules, trusted
   validation and final-test access. Agent-editable scope is its planning policy,
   diagnostic selection, tool wrappers, reusable memory and, for the recursive arm,
   its revision procedure. Any learned surrogate is checked by the unchanged evaluator.
2. Maintain a version archive: parent hash, exact agent-authored patch, author model,
   prompts, traces, costs, failures and development evaluation. Test candidate revisions
   before promotion; retain rejected revisions for analysis. Hash checks alone do not
   isolate the evaluator: use a separate evaluation process and restricted access.
3. Start a pilot with five independent lineages and up to five revision rounds per
   lineage, including unsuccessful attempts. This is a feasibility design, not a power
   calculation. Choose confirmatory replication only after pilot variance is available.
4. Compare a fixed agent, memory-only agent, fixed external revision procedure,
   inherited self-revising agent, and strong conventional optimization. Allocate equal
   total model and simulation budgets, including revision and failed-candidate costs;
   also report deployment-only costs separately to show amortization.
5. Separate development, repeatedly used promotion validation, and sealed final tasks
   by whole weather/traffic scenarios and spatial regions. Freeze the selected generation
   before final evaluation. Avoid choosing a generation from its final-test performance.
6. Test attribution: remove physical diagnostic feedback; reset inherited changes;
   compare descendant versus original revision procedures on the same starting agents.
   Log human interventions and exclude them from autonomous-improvement claims.
7. Report independently feasible quality, cost-to-target, full improvement cost,
   failed/invalid interventions, cross-task transfer, regression frequency and lineage
   variation. City grid cells are not independent replications. If conventional search
   solves the task cheaply, report that result rather than removing the strong baseline.

### Literature and positioning boundary

- [Darwin Gödel Machine, arXiv:2505.22954v3](https://arxiv.org/abs/2505.22954v3)
  demonstrates agent-code self-modification with empirical benchmark evaluation and
  an archive. Self-editing alone is therefore not a sufficient novelty claim.
- [Hyperagents, arXiv:2603.19461v1](https://arxiv.org/abs/2603.19461v1)
  explicitly makes both task and meta-level agents editable. A stronger recursive
  claim should test the revision mechanism, not merely successive task scores.

Potential contribution, still unproven: physically verified, cost-accounted transfer
of agent improvements across constrained urban computational experiments. South
Kensington is the application/test environment, not by itself the methodological
novelty. Physical-model sensitivity remains relevant under this framing; RSI cannot
turn an unvalidated simulator reward into demonstrated real-world benefit.

### Implementation audit for the recursive interpretation

Inspected against the current checkout, not inferred from passing pilot tests:

| Existing mechanism | Source evidence | Consequence for a multi-generation experiment |
| --- | --- | --- |
| Session closes and reveals holdout on submission | `src/urban_planning/tools.py`, `call_tool`, submission branch | Adequate for the current single-episode protocol; a descendant reading the parent's transcript would see test feedback. A recursive run needs development-only submissions and a separate final-test release after the whole lineage is frozen. |
| All background arrays load into the planner-side Problem instance | `src/urban_planning/problem.py`, `Problem.__init__` and `evaluate(split=...)` | Hiding a tool parameter does not isolate test data. The new runner must not receive the combined background file or direct evaluator object. |
| Source hashes identify the physical evaluator | `src/urban_planning/problem.py`, `identity`; `tools.py`, identity comparison | Preserve the evaluator identity, but add a separate agent-revision identity. A valid agent revision must change its own hash without changing the evaluator hash. |
| Changed-task baseline carries an incumbent plan | `src/urban_planning/benchmark.py`, `benchmark` and `run_policy` | This is solution transfer, not inherited agent improvement. Retain it as a baseline and identify it correctly. |
| Benchmark file contains exhaustive references and holdout metrics | `src/urban_planning/benchmark.py`, output assembly | Keep these artifacts outside the agent's accessible workspace during generation, promotion and revision. |

The existing 125 Python checks and viewer validation do not establish any of these
multi-generation properties. Do not alter the existing pilot's release semantics
silently; implement the confirmed recursive research direction in a separate experimental runner.

Minimum acceptance cases for that runner:

1. A child can inherit its parent's approved policy and development diagnostics,
   but neither a parent transcript nor its exported memory contains final-test scores.
2. Closing one episode does not release lineage-level test feedback. The final-test
   controller accepts only the frozen selected revision and records any attempted reuse.
3. Editing policy code creates a new revision with its parent hash; editing evaluator,
   split definitions or objective normalization invalidates the experimental comparison.
4. Candidate generation, rejected revisions, invalid calls and deployment evaluations
   are all charged to the relevant lineage and included in the cost comparison.
5. Fixed-updater and recursive-updater arms start from identical task agents with equal
   budgets. A matched replay isolates whether the evolved updater improves future revisions.
6. A failed or regressed child remains in the archive and cannot overwrite its parent;
   publication of a generation curve includes failures and the selection rule.

Recommended first scope: preserve base-model weights and physical solvers, and allow
changes to the agent's experiment-selection policy and tool composition. Add editing
of its revision procedure in an explicitly separate arm. This separates a tractable
self-improvement claim from the stronger recursive-mechanism claim instead of assuming
the latter from an upward task-score curve.


### 论文叙事：从城市实验经验到可继承的 Agent 能力

**建议主张（待实验验证）：物理反馈能否驱动城市规划 Agent 形成可继承、可迁移的自我改进？**
暂定标题：*Physics-grounded self-improving agents for urban planning*。
若代际递归机制获得独立证据，再考虑
*Physically grounded recursive self-improvement for urban planning agents*。
标题的证据强度应与最终实验一致，不预设递归过程必然成功或持续加速。

叙事顺序：

1. **问题。** 城市规划需要在交通、形态、环境与现实约束之间反复组织计算实验。
   对固定工作流而言，每一种新任务或失败模式都可能需要人工调整。我们的研究问题是，
   Agent 能否把解决这些任务的经验转化为自身可执行方法的改进。
2. **基础。** 现有框架提供共享场景、可修改动作、物理求解与反馈记录，构成试验环境。
   tools space 的价值在于让行为有后果、错误可诊断、改进可评价；工具数量不是主要创新。
   模拟反馈的可信度来自独立验证，不能因反馈来自物理程序便视作真实世界真值。
3. **机制。** 内层 Agent 提出城市方案、调用工具、检查效果；外层 Agent 从开发任务的
   失败轨迹提出自身策略/工具组合的修改，经独立验证后产生下一版本。下一版本继承修改，
   参与后续任务及自修改过程。基础模型权重可以固定，研究对象明确为 Agent 软件系统。
4. **递归的证据。** 要追踪 A0→A1→A2 的真实生成关系、实际使用的父代能力与补丁。
   若固定外部程序每次只是独立改写同一个初始 Agent，应归入固定改进程序基线。
   “改进机制本身也变强”是更强主张，需从同一起始 Agent 比较新旧修改程序的后续收益。
5. **结果。** 在新任务、同预算下检验后代是否提升可行解质量、降低达到目标的成本或
   减少重复失败。展示改进具体发生在哪里，再用移除该修改的实验验证其贡献。
   不能仅画一个城市方案目标值随迭代上升的曲线来证明 Agent 能力提升。
6. **推广。** 南肯辛顿作为受约束的真实几何实验环境，用新风向/需求/街区检验迁移，
   再用 White City 检验空间迁移。交通、建筑形态、遮阳和材料是任务维度；热学材料任务
   只有在求解器真正接入相应物理量后才进入正式任务集。

假想机制示例（不是已发生的结果）：Agent 在开发场景发现单风向方案失效，归因于
天气覆盖不足，生成可执行的多风向诊断程序；后代继承此程序，在未见任务上减少失效。
若后代进一步改善如何选择诊断场景，并在同预算配对实验中获益，才支持改进机制提升。
若诊断程序由研究者手写，则只能作为人工设计基线，不能计入自主改进证据。

建议论文结果图围绕五条证据组织：

| 图 | 核心问题 | 必需对照或检查 |
| --- | --- | --- |
| 1 | 哪些 Agent 部分可改，哪些评价部分固定？ | 双层实验流程、版本继承与独立评价边界 |
| 2 | 后代能力是否提升？ | 每代在冻结评测任务上的表现；选择不访问该评测；多条独立谱系 |
| 3 | 为什么提升？ | 真实修改案例、对应工具行为变化、撤销修改后的消融 |
| 4 | 提升是否值得且可以迁移？ | 含改进开销的质量—成本曲线；新气象/需求/空间任务 |
| 5 | 递归是否有额外贡献？ | 固定 Agent、记忆、固定外部修改程序、递归修改及常规优化对照 |

最终检验不能反过来筛选代数、提示词或补丁：评测人员可在全部冻结后统一评价归档代，
评价结果不返回进化过程，也不依据其结果再挑选最好的最终代来宣称预先选择的性能。

对 NCS 的定位判断：值得尝试的贡献是具有归因证据的计算方法与物理应用价值。
“已有自修改方法接上一个城市案例”仍不足以成为方法贡献。应证明物理诊断反馈、
多精度计算或约束验证中的某个机制，确实改善自我改进的效率、可靠性或迁移。
本定位并不承诺期刊接受，也不把缺乏物理验证的模拟收益解释为真实城市改善。

本次定位工作已完成：明确对象、叙事、机制边界、现有证据缺口与实验对应关系。
后续工作仍包括独立运行器、代际生成与正式对照；本文件没有将这些列为已完成实验。


### Agent 系统实施更新：2026-09-30

独立运行器已实现于 `src/urban_planning/rsi/`，使用 Claude Code 的真实模型接口；
另保留明确标记的离线测试后端。现有 solar pilot 接口不变。
第一版 Agent 可调用评价、空间诊断及提交动作，自修改范围为规划指令、改进指令与记忆。
版本归档、父子关系、差异、验证晋升/拒绝、全程预算记录、最终版本冻结和单次最终评分均已接入。
继承后的 updater 指令用于 recursive 实验臂的下一轮修改；不执行任意生成的 Python。

本轮检查覆盖 133 项 Python 测试，包括 8 项 RSI 专项检查。真实 Claude 运行的结果另行
记录，不把测试替身的成功晋升算作模型能力证据。用法、模型接口限制和成本口径见
`src/urban_planning/rsi/README.md`。独立新任务、多谱系统计对照与高保真物理验证仍待开展。
