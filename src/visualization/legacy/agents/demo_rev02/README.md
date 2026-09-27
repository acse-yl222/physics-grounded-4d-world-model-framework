# FieldFleet × Traffic · South Kensington city demo (revision_02)

Static HTML/three.js viewer of the South Kensington city model with two replay layers:
(1) the NVMF UAV delivery schedule (300 UAVs, 600 orders, one hour) and (2) a bounded
SUMO road-traffic replay on the revision_02 repaired lane network with simulated signal
heads. Everything runs from local files; no network, account or GPU workstation is needed.

**Not a traffic measurement, not TfL data, not evidence about the scheduling capability** —
see "Claim boundary" below.

---

## 1. What you need before starting (two things are NOT in this repository)

| Item | Where it comes from | Put it at |
|---|---|---|
| City model `south_kensington_core008_web.glb` (254 MB, unchanged first-version asset) | sent separately (WeChat) by BoHan | `assets/city.glb` |
| Full-hour traffic replay: `traffic_flow.f32` (106 MB), `tls_frames.jsonl` (85 MB), `frames_index.json` | Mac package `UWM_DEMO_20260911/revision_02/package/FieldFleet_SouthKensington_rev02/data/traffic/replay/` or sent separately | `data/traffic/replay/` (overwrite the 300 s sample files) |

The repository ships a **300-second sample** of the same audited replay (byte-for-byte
prefix), so the page runs as soon as the city model is in place; road traffic then simply
ends at 05:00 until the full-hour files are dropped in. `python3 verify_large_files.py`
checks the sizes and SHA-256 of the placed files.

## 2. Start

```bash
python3 serve_demo.py        # or double-click "Start Demo.command" on macOS
# open http://127.0.0.1:8768/ in Chrome (first load ~10-20 s: it parses the 254 MB city model)
```

## 3. Layout (what to plug where)

```
index.html / index.js        page shell and viewer core (scene, camera, timeline, follow camera)
signals-v2.js                revision_02 signal poles/heads, each head reads states[tls][link] of the recorded frames
stations.js  parking.js      UAV stations, Hub parking allocation, road surface mesh
demo-cues.js                 demo highlight bookmarks (UAV)
actors/ vendor/              instanced car / UAV models, three.js 0.185.1
data/
  stations.json routes.json hub-bays.json parking.json    UAV scene inputs (first version, unchanged)
  schedule.json                staggered display timeline of the NVMF replay (service times, orders, battery unchanged)
  schedule_original.json       original NVMF replay timeline (switchable in the panel)
  uav-cues.json                UAV highlight bookmarks (recomputed for the staggered timeline)
  roads.json                   drivable-lane ribbons of the revision_02 network (6,209 lanes)
  static-vehicle-filter.json   which GLB parked cars to hide (they would sit in simulated traffic)
  traffic/current_replay.json  replay manifest + release gates (status must be PASS)
  traffic/signal_layer_v2.json 851 signal heads / 389 poles / 851 movements
  traffic/replay/              traffic_flow.f32 (f32 records [id,x,y,angle,speed]), frames_index.json, actors.json, tls_frames.jsonl, simulation.json, RUN_CONFIG_V2.json, DEMO_CUES.json
evidence/                     audits, road-repair ledger and before/after maps, collision patches, replacement-spawn analysis
FILES.json                    SHA-256 of every file of the full Mac package
```

Data contracts for other components (birds etc.): world frame = glTF metres, Y up;
SUMO → world: `X = sumo_x − 2912.594719173`, `Z = 1704.705026026 − sumo_y`;
replay positions are vehicle centres (front = centre + 2.25 m along heading); one frame per second.

## 4. What revision_02 changed (demo only)

- Road network re-qualified geometrically on the original OSM network: 611 lanes / 35.4 lane-km reopened, 21 missing middle segments restored (1.34 km), largest strongly connected component 232 → 1,369 edges (12.9 → 94.9 km); 65 short lanes newly closed on building-clearance / sharp-reversal evidence. Maps in `evidence/maps/`.
- Junction collisions: 16 right-turn connections lose their in-junction waiting position (contPos=0, each with collision evidence); one evidenced movement restriction (Queen's Gate Place Mews → Queen's Gate Place). No roads were closed to improve numbers; no teleports, forced removals or disabled collision checks.
- Vehicle behaviour: lane-change mode 517, minGap 2.5 m, rerouting every 60 s.
- Demand: 1,500 spawn templates (925 same lane id, 522 mapped by position, 88 replaced because the first-version origins sit in boundary pockets not connected to the main network); destinations sampled inside the main component (700–2,600 m). Mean trip 1.7 km vs 0.5 km in the first version, so completed-trip counts are not comparable.
- Signals: whole map, every head bound to the recorded control state of its own connection (netconvert default programmes).
- UAV: same-station same-second take-offs released 2 s apart using waiting time (103 groups → 7); original timeline switchable; Hub fade-out kept.

## 5. One-hour result (cloud SUMO 1.27.1, `evidence/AUDIT_REPLAY_V2.json`)

| Metric | First version (its own replay) | revision_02 |
|---|---|---|
| Share of cars moving (hour mean) | 20 % (12 % in the last 10 min) | 43 % (42 %) |
| Cars ever stopped ≥ 600 s | 926 (853 still stuck at the end) | 16 (all moved on) |
| Longest stop | 3,595 s | 962 s |
| Teleports / forced removals | — | 0 / 0 |
| Collision warnings | — | 10 per hour (7 junctions) |
| Centres off the drawn lanes / verified red-light crossings | — | 0 / 0 |

Residual (honest): 56 cars still stopped ≥ 180 s at the end, all on the westbound Kensington
Road / Kensington High Street corridor and its side-street exits (closely spaced, uncoordinated
fixed-time signals with 0.2–7 m micro-links between them); one wall corner in Radley Mews where
a car body can overlap a wall by ≤ 0.3 m for ~30 s.

## 6. Claim boundary

Road traffic is a rule-based SUMO simulation with simulated signal timing; deliveries come from
the original NVMF run; station positions are a demonstration design. The demonstration is neither
a real traffic measurement nor proof of the original scheduling capability. Large files are kept
out of git deliberately (GitHub's 100 MB limit and repository size).

---

## 中文简要

- 仓库里没有城市模型（BoHan 微信发）和整小时交通回放大文件（在 Mac 便携包里）；仓库自带前 300 秒的样本回放，放好 `assets/city.glb` 就能跑，放入整小时文件后看完整一小时。`python3 verify_large_files.py` 校验。
- 启动：`python3 serve_demo.py`，Chrome 打开 http://127.0.0.1:8768/ 。
- 第二版改动、一小时数据、残留问题和声明边界见上文第 4–6 节；证据在 `evidence/`。
