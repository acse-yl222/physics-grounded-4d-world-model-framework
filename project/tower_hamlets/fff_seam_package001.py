from pathlib import Path
import json,hashlib,zipfile
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/fff_seam-comparison-001';p=O/'fff_seam-checks.json';d=json.load(open(p));d['visual_reviewed']=True;d['reviewed_views']=['overview','seam','top','profile'];d['regional_source_sha256']=hashlib.sha256((P/'runs/canary_wharf_appearance_owner87aa_001/region.blend').read_bytes()).hexdigest();p.write_text(json.dumps(d,indent=2));(O/'fff_seam-report.md').write_text('''# Exact-clipped local terrain comparison

Independent display only; no regional retention or global edits. Source pair buildings and measured terrain come from fff_boundary-ground-contact-001. Every original mesh vertex remains exactly unchanged, including roof absolute elevations and estimated wall extensions. The outside-AOI owner remains context, not an added inventory building.

Latest owner87aa site ground is two triangles/six vertices at z=-0.10000000149m; water508triangles does not reach this northern location. A library read imported relevant objects only; no full regional scene assembly or replacement performed. Exact site topology retained for reproducibility.

Retained measured patch bounds ENU[-513,352,-493,372]. Local display window[-518,347,-488,377]. The old ground's projected overlap137.562224m² is subtracted exactly. Remaining old ground218.781112m² is triangulated, with zero positive projected overlap against the patch and zero symmetric-difference error within numerical tolerance. This comparison clips only the original local window; outside-window region is neither exported nor changed.

Old ground minus DTM at shared patch boundary remains1.407000–1.693000m. Exact planar clipping eliminates overlap, but cannot resolve this physical inconsistency. The seam is deliberately open and labelled as dataset/display boundary, NOT a real cliff. No ramp, blending slope, vertical skirt, inferred retaining wall or arbitrary terrain flattening is added. Both grounds and gap are visible in inspected overview/seam/top images; profile explicitly separates source surfaces. Terrain remains nearest-raster sampling on1m ENU grid and interpolated triangles, with unresolved capture vintage; it is not native BNG-grid precision.

Native reopen and independent GLB reimport pass (all mesh counts/triangle counts); ground-contact source SHA unchanged. Original terrain and pair vertices exact. Other regional buildings are not copied or edited. This asset is suitable as an honest independent comparison; not a physically seamless regional integration. Source/hash package includes this bounded implementation and input attribution records, no original photographs.
''')
files=list(P.glob('fff_seam*.py'))+list(O.glob('fff_seam*.json'))+[O/'fff_seam-report.md',R/'exports/fff_boundary-ground-contact-001/checks.json',R/'exports/fff_boundary-ground-contact-001/source_hash.json',R/'exports/fff_boundary-evidence-002/fff_boundary-terrain-report.json',R/'references/fff_boundary_lidar_sources001.json']
with zipfile.ZipFile(O/'fff_seam-source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in files:
  if f.is_file():z.write(f,str(f.relative_to(P)))
(O/'fff_seam-hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file() and p.name!='fff_seam-hashes.json'},indent=2));print(d)
