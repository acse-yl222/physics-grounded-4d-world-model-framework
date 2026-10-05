# Building Parameter Schema v0 — parameterised 3D semantics

Draft 2026-07-26, responding to the supervisor direction (Yueyan, email 07-26):
*"not only editing the building's shape, but parameterising the building
information in 3D … attributes that can be understood, edited, and optimised,
not just geometry that can be dragged around"* — study Archicad's structured
approach first, then bind to Blender's native parametric machinery.

## 1. What Archicad actually does (and what we take from it)

Archicad separates FOUR things that our current `spec.json` mixes together:

| Archicad concept | what it is | our takeaway |
|---|---|---|
| **GDL library part** | a script + a TYPED parameter list; the geometry is regenerated from parameters every time | an element is *code with parameters*, never a frozen mesh — maps to a Blender **geometry-node group** whose group inputs are the parameters |
| **Parameter script** | per-part logic: valid ranges, value lists, subordination (parameter hierarchy), derived values | every parameter carries `unit / range / choices`; cross-parameter rules live WITH the element (e.g. `sill_h + win_h < floor_h`) — maps to Blender **drivers** + validation in our schema layer |
| **Subtype tree** | every part has a subtype in a tree aligned with IFC entities (window ⊂ opening ⊂ element); subtypes INHERIT parameters | our element types form a small inheritance tree with shared base params (id, anchor, size, material) |
| **Classification & Properties** | any element additionally carries classification (what it IS, IFC-mappable) + property sets (what is KNOWN about it) — separate from geometry params | semantics ride on the element as **properties**, not geometry: function, era, material class, provenance. In Blender: object custom properties (exportable) |

The key structural lesson: **geometry parameters and semantic properties are two
different layers on the same element.** Editing tools touch layer 1; understanding,
search and optimisation mostly read layer 2.

## 2. Schema v0

One building = one JSON document. Hierarchy (each node = element with `type`,
`params`, `props`, children):

```
Building
├── Storeys            (count, heights — the vertical grammar)
├── Facade[]           (one per orientation/edge; the facade GRAMMAR lives here)
│   └── Bay[]          (repeating unit: width, rhythm)
│       └── Opening[]  (window/door: w, h, sill, style)
├── Roof               (form, pitch, tone, dormers)
├── Ornament[]         (hybrid assets: portico, sculpture — external mesh + anchor)
└── Palette            (named materials, photo-measured colours)
```

### Element base (inherited by everything, Archicad-subtype style)

```jsonc
{
  "id": "el_017",             // stable id -> Blender object/nodegroup name
  "type": "window",           // subtype tree: element > opening > window
  "params": { ... },          // layer 1: typed geometry parameters (see below)
  "props": {                  // layer 2: semantic properties (classification)
    "ifc": "IfcWindow",
    "source": "photo|osm|lidar|default|agent",   // provenance -- OUR addition
    "confidence": 0.0-1.0,
    "notes": "sash, painted timber"
  }
}
```

`props.source`/`confidence` is the one thing Archicad does NOT have that we need:
every value in this pipeline is *measured, inferred or defaulted*, and the refine
loop should prefer to optimise low-confidence parameters first and trust
photo-measured ones.

### Every parameter is typed (the "parameter script" discipline)

```jsonc
"floor_h": {"value": 3.2, "unit": "m", "range": [2.4, 5.0], "source": "lidar"}
// shorthand in examples below: floor_h: 3.2
```

### Building

```jsonc
{
  "building": {
    "params": {
      "footprint": "polygon|obb",      // OSM pts or L x W
      "storeys": 5, "floor_h": 3.2,
      "wall_class": "brick|stone|stucco|glass|concrete"
    },
    "props": {"osmid": 110085215, "name": "Royal School of Mines",
              "function": "education", "era": "1910s", "listed": true}
  }
}
```

### Facade — the grammar is a parameter, not a drawing

```jsonc
{
  "type": "facade", "edge": 11,                  // polygon edge / "-y" for obb
  "params": {
    "grammar": "punched|ribbon|giant|curtain|blank",  // library round 3-4 vocab
    "bay_m": 6.0,                                // rhythm
    "base_storeys": 1, "attic": true,
    "front": true                                // from front_edges(pano)
  },
  "children": [ /* Bay -> Opening */ ]
}
```

### Opening (leaf)

```jsonc
{
  "type": "window",
  "params": {"w": 1.4, "h": 2.1, "sill_h": 0.9, "row": 2, "col": 3,
             "style": "sash|casement|arched|fixed", "recess": 0.12},
  "props": {"ifc": "IfcWindow", "source": "photo", "confidence": 0.8}
}
```

### Ornament (the hybrid channel)

```jsonc
{
  "type": "ornament",
  "params": {"anchor": [x, y, z], "scale": 1.0, "face": "-y"},
  "props": {"kind": "sculpture_group", "source": "3dgen",
            "asset": "assets/rsm_montford_left.glb",
            "tri_budget": 15000}                 // supervisor: watch mesh size
}
```

## 3. Binding to Blender (the code-writing agent's target)

- **One geometry-node group per element type** (`GN_Facade`, `GN_Window`,
  `GN_Roof`…), group inputs = the `params`. The agent AUTHORS node groups in
  Python (nodes/links are fully scriptable) instead of emitting frozen meshes —
  change `storeys` on the modifier and the building regenerates.
- **Drivers** encode cross-parameter logic (Archicad's parameter script):
  building height = `storeys * floor_h`; window z = `row * floor_h + sill_h`.
- **Object custom properties** carry `props` (semantics survive into the .blend
  and out to glTF/IFC-style exports).
- Known caveat: geometry-node modifier inputs set from Python need an explicit
  depsgraph update nudge (long-standing quirk, see T87006) — the harness wraps
  this.
- The editing tool (later): a small N-panel that lists the schema tree and edits
  modifier inputs — "vibe-code a small tool" per the email; it falls out of the
  binding almost for free.

## 4. Optimisation (the loop this schema unlocks)

The refine loop currently rewrites a whole spec. With the schema the loop
becomes **search over a typed parameter vector**:

- objective = checklist pass-rate (+ DreamSim anchor), as today;
- move set = per-parameter deltas within `range`, prioritised by LOW
  `confidence` (don't fight photo-measured values);
- the judge's failed checks name the parameter to move ("storey count wrong" →
  `storeys`), which is exactly the structure the 07-06 knobs lesson asked for.

## 5. Migration from the current pipeline

| today | schema v0 |
|---|---|
| `spec.json` masses/terrace/ribbon/giant | `building.params` + `facade[].grammar` |
| `colors.json` (facade_colors) | `palette` with `source: "photo"` |
| `front_edges` | `facade[].params.front` |
| fallback shell | a full document with everything `source: "default"`, `confidence: 0.2` |
| components.py parts | re-authored as GN groups (incremental; obb terrace first) |

## 6. Conditional fields in today's terrace kit (`components.py`)

Not every field in the `terrace` block acts on every building. The terrace
articulation is a TYPOLOGY, not a property of masonry: a 2026-07-19 review found
campus slabs rendering with chimney rows, balconies and porticos, so the housing
parts were put behind a gate. The editor still exposes the fields on every
building, so a toggle that changes nothing is a gate, not a failure -- the
rebuild completes and reports success.

Two gates apply, in order.

**Gate 1 -- masonry only.** The whole terrace kit is skipped for a glass mass
(`if not glass:`); a glass mass gets a thin roof slab instead.

**Gate 2 -- `long_low`,** evaluated per mass:

```python
typ      = desc.get("typology", "terrace")
long_low = mass_length >= 2.2 * mass_height and typ == "terrace"
```

| field | default | acts when |
|---|---|---|
| `terrace.bay_m` | 7.5 | any masonry mass (sets the bay rhythm) |
| `terrace.stucco_floors` | 1 if `typology == "terrace"`, else 0 | any masonry mass, every face |
| `terrace.shopfront` | off | front face only (`-y` by kit convention) |
| `terrace.pediment` | off | front face only (`-y`) |
| `terrace.roof_form` | `valley` if `long_low`, else `flat` (non-terrace) / `gable` | any masonry mass |
| `terrace.roof_tone`, `terrace.dormers` | dark / off | any masonry mass |
| `terrace.balcony` | **on** | `long_low` |
| `terrace.railings` | **on** | `long_low`, and no shop parade on the front |
| `terrace.bay_windows` | off | `long_low` |
| chimneys | -- | `long_low` |
| porticos, house bays | -- | `long_low`, and the mass does not sit on the photo-projected front |

A shop parade on the front means `scene/shops.py` found units on `-y`: the
unit's own recessed door is then the entrance, so kit railings and porticos
would double it.

**Consequence for editing.** On a tall or narrow mass, or one whose `typology`
is not `terrace`, toggling `balcony`, `railings` or `bay_windows` rebuilds the
building unchanged. This is why the edit benchmark counts rebuilds that
completed rather than fields that visibly move a given building.

## 7. Next steps

1. Freeze v0 field names on ONE building (a Queen's Gate terrace: obb, punched
   grammar, mansard) and hand-write its document.
2. Prototype `GN_Facade`+`GN_Window` node groups via Python; bind the document;
   verify a `storeys` edit regenerates correctly.
3. Point the refine loop at the parameter vector of that one building.
4. N-panel editor prototype after 2 works.
