from pathlib import Path
import json,hashlib,zipfile
P=Path(__file__).resolve().parent;R=P/'input/canary_wharf_20261007';O=R/'exports/morgan_south-facade-001';d=json.load(open(O/'morgan_south-checks.json'));d['visual_reviewed']=True;d['pane_width_fractions_estimated']=[.2,.3,.3,.2];d['photo_source']='pexels_zak_36533700';d['photo_sha256']=hashlib.sha256((R/'references/pexels-zak-h-36533700.jpeg').read_bytes()).hexdigest();(O/'morgan_south-checks.json').write_text(json.dumps(d,indent=2));(O/'morgan_south-report.md').write_text('''# Morgan south local edge13 candidate

Only ownerb317 mappededge13, two visible glazing bays. Actual original-resolution licensedZakcrop inspected: each bay has narrow side panes, wider central panes, dark central spandrel, slender black frames, brown stone piers and short pale bands. Corrected initial equal-thirds hypothesis to four unequal20/30/30/20 panes. Two-bay placement, heights19–28.48scene, colors, dimensions, thin bands and depth are explicitly estimates. Original body and roof vertices/faces/materials exactly preserved. No extension around perimeter or into lower pale-stone base.

Panels are mounted outside existing blank body, glass outerdepth.045m, stonefront.25m, accents.262m. Relative glass-to-pier recess.205m is real geometry; this is not a cut-through wall opening or interior reconstruction. Added closed prisms have no zero-area faces. Other mapped owners have zero positive plan overlap with added details. Originalbody simplifications/uncertainties remain.

Photo correspondence: previously held-out loweasttip15.17px error for b317 versus332.71px for3ae. Jointrefit18.33pxRMS does not establish exact metric feature placement. Source study003 retained roof and current scene absolute datum preserved. Entireb317 standalone shown for review but regional integration should import ONLY five meshes namedmorgan_south_*; do not replace originalbody/roof from this standalone.

Native reopen/independentGLB import pass. Final corrected detail and complete overview actually inspected. Source archive excludes all photograph originals/crops/overlays; crop exists in cache only. No global/regional edits in standalone stage.
''');files=list(P.glob('morgan_south*.py'))+[P/'photo_study_morgan_near001.py',O/'morgan_south-checks.json',O/'morgan_south-interface.json',O/'morgan_south-report.md',R/'exports/photo-study-morgan-near-001/photo-study-near-landmark.json',R/'exports/photo-study-morgan-near-001/photo-study-visible-edge-candidates.json']
with zipfile.ZipFile(O/'morgan_south-source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in files:z.write(f,str(f.relative_to(P)))
(O/'morgan_south-hashes.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in O.iterdir() if f.is_file() and f.name!='morgan_south-hashes.json'},indent=2))
