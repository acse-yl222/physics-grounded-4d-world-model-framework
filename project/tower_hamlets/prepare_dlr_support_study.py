from pathlib import Path
import json,sys
R=Path(__file__).resolve().parent/'input/canary_wharf_20261007';sys.path.insert(0,str(R))
from src.buildings.dlr_central_frame import frame_data,cylinders,FEATURE_ID
f=next(b for b in json.loads((R/'geometry.json').read_text())['buildings'] if b['id']==FEATURE_ID);roof,members,p=frame_data(f);rows=[]
v,faces=cylinders([m for m in members if m[0]!='support_column']);rows.append(dict(name='Red_roof_frame',vertices=v,roof_faces=faces,wall_faces=[],bottom_faces=[]))
v=[];faces=[]
for label,a,b,radius in members:
 if label!='support_column':continue
 x,y=a[:2];low=a[2];high=b[2];off=len(v);w=.22
 v.extend([[x+dx,y+dy,z] for z in [low,high] for dx,dy in [(-w,-w),(w,-w),(w,w),(-w,w)]])
 faces.extend([[off+i for i in face] for face in [[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]])
rows.append(dict(name='Grey_square_supports',vertices=v,roof_faces=[],wall_faces=faces,bottom_faces=[]))
(R/'references/dlr_support_study.json').write_text(json.dumps({'objects':rows,'scope':'Photo-informed frame study: red arches retained, vertical supports represented as grey square columns. 0.44m square sections and locations estimated; source platform view does not verify every support. No platform, rail or facade additions.','source_id':'geograph_dlr_5620872','parameters':p}))
print(len(v)//8,'supports')
