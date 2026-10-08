from pathlib import Path
import json,hashlib,zipfile
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/fff_boundary-roof-study-001';E=R/'exports/fff_boundary-evidence-002'
p=O/'fff_boundary-checks.json';d=json.load(open(p));d['visual_reviewed']=True;d['visual_review_notes']='Actual overview, roof, rear and DSM fit views inspected: continuous joint roof, apex in west context; no visible owner seam gap. Terrain diagnostic also inspected.';p.write_text(json.dumps(d,indent=2))
(O/'fff_boundary-report.md').write_text('''# Boundary pair roof candidate

Stable standalone candidate; no regional changes. Original fff95900 owner is separately replaceable in fff_boundary-target.blend/.glb. Full shared roof is in fff_boundary-pair-context.blend/.glb. Outside owner 02ed5509 is in its own context-only collection, excluded from the original 439 inventory. Its vector identity is from official Overture, not inferred from raster.

Both exact mapped footprints are preserved. Shared edge is 10.48221948 m; authored roof top agrees on all shared breakpoints and 101 interpolated samples (maximum difference 0 m). The cut is an internal owner boundary, not an exposed exterior facade. Per-sector solids have closed faces, zero zero-area faces, but coincident internal caps remain: this is editable architectural geometry, not a boolean-union simulation solid. Native reopen and GLB reimport pass: target 3 meshes/32 triangles, pair 7 meshes/80 triangles.

Common four-plane roof is a DSM-supported approximation, not surveyed architecture. Fitted reference eave 7.70020048 m ODN; apex 10.00239320 m ODN, or 5.72239299 scene z after subtracting shared 4.28000021. Peak belongs to outside west owner. Original owner maximum scene z is 5.1828146. Base z=0 is inherited and unverified; no fabricated entrances/facades. Capture vintage remains unresolved.

All 117 roof cells retained in residual reporting: RMSE 1.67664 m, including low mixed edge returns. The 1 m inset fit uses 78 cells, RMSE 0.46373 m. Spatial strip held-out RMSE is 0.49224/0.46904 m across/along. Inset sensitivity 0.5–2 m gives apex 9.935–10.148 m ODN. Initial constrained apex offset reached its bound; relaxed ±2.5 m diagnostic gives unconstrained optimum 1.5464/0.7852 m offset. No unsupported exact physical eave claim.

Actual overview/roof/rear render and fit plot reviewed. Roof is continuous across owners. Target-only display exposes its internal cut; full pair context is preferable for explaining geometry, but should not automatically enter regional inventory.

## Terrain limitation

Actual north_pyramid001 site-support BVH: west context 5/5 representative samples have no ground; original owner 3/5 have no ground and two hit approximately z=-0.1. Licensed DTM surrounding 2 m ring is scene z -1.785 to -1.403 (median -1.556). Across 147 dense sample locations with existing site, site minus DTM is +1.379 to +1.693 m, median +1.504 m. Existing flat site therefore does not match measured terrain; body base zero is also about 1.4–1.8 m above surrounding DTM. Adding a flat slab would conceal this discrepancy.

Smallest full pair footprint ENU bbox: [-509.792035,355.316476,-496.247435,368.332869]. A chosen 2 m context margin is [-511.791402,353.317487,-494.248260,370.332050]; aligned EPSG:27700 1 m grid bbox [537075,180684,537094,180703] is fully covered by retained DTM. This margin is a display choice, not a physical minimum. Any terrain extension requires measured non-flat terrain plus an explicit transition to simplified regional ground, and separate consideration of inherited base height. No ground patch or base correction authored.

Sources, original small DSM/DTM, bounded official vector, exact request/grid/hash/overlap records, fit/support/terrain diagnostics and generation scripts are retained in source archive. No source photograph included. OGL EA raster and Overture feature attribution are in acquisition records; data acquisition dates do not establish capture dates.
''')
files=list(P.glob('fff_boundary*.py'))+list((R/'references').glob('fff_boundary*'))+list(E.glob('fff_boundary*'))+[O/'fff_boundary-report.md',O/'fff_boundary-checks.json']
with zipfile.ZipFile(O/'fff_boundary-source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(files):
  if f.is_file():z.write(f,str(f.relative_to(P)))
h={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(O.iterdir()) if f.is_file() and f.name!='fff_boundary-hashes.json'};(O/'fff_boundary-hashes.json').write_text(json.dumps(h,indent=2));print(json.dumps(h,indent=2))
