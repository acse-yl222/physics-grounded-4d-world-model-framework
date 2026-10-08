from pathlib import Path
from collections import Counter
import json,sys
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';sys.path.insert(0,str(R))
from src.buildings.dlr_central_frame import frame_data,FEATURE_ID
f=next(q for q in json.loads((R/'geometry.json').read_text())['buildings'] if q['id']==FEATURE_ID);(v,faces),_,p=frame_data(f);n=len(v);thickness=.04;verts=[list(q) for q in v]+[[q[0],q[1],q[2]-thickness] for q in v];top=[list(q) for q in faces];bottom=[[i+n for i in reversed(q)] for q in faces];edges=Counter(tuple(sorted((a,b))) for face in top for a,b in zip(face,face[1:]+face[:1]));walls=[[a,b,b+n,a+n] for (a,b),count in edges.items() if count==1];counts=Counter(tuple(sorted((a,b))) for face in top+bottom+walls for a,b in zip(face,face[1:]+face[:1]));assert all(n==2 for n in counts.values())
(R/'references/dlr_glazing_shell.json').write_text(json.dumps({'objects':[dict(name='DLR_glazing_shell',vertices=verts,roof_faces=top+bottom+walls,wall_faces=[],bottom_faces=[])],'scope':'Existing estimated DLR canopy with0.04m vertical glazing thickness and closed perimeter. Thickness is illustrative; no measured panel construction. Original assumed height retained pending elevation review.','thickness_m':thickness,'edge_incidence_two':True,'source_id':'geograph_dlr_5620872'}));print(len(verts),len(top+bottom+walls))
