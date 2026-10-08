import json,numpy as np,math
from pathlib import Path
R=Path('project/tower_hamlets/input/canary_wharf_20261007');a=json.loads((R/'references/morgan_photo_camera.json').read_text())['parameters_xyz_yaw_pitch_roll_logf'];c=np.array(a[:3]);yaw,pitch,roll=a[3:6];fw=np.array([math.cos(yaw)*math.cos(pitch),math.sin(yaw)*math.cos(pitch),math.sin(pitch)]);right=np.array([math.sin(yaw),-math.cos(yaw),0]);up=np.cross(right,fw);r=right*math.cos(roll)+up*math.sin(roll);u=-right*math.sin(roll)+up*math.cos(roll);f=math.exp(a[6]);p=json.loads((R/'references/207561_identity_audit.json').read_text())['source_geometry']['geometry'][0]['outer']
def project(q):
 d=np.array(q)-c;return [960.5+f*d@r/(d@fw),640-f*d@u/(d@fw)]
for n,(x,y) in enumerate(p):print(n,project([x,y,141.76]),project([x,y,30]),[x,y])
P=np.array(p[2]);Q=np.array(p[3]);normal=np.array([Q[1]-P[1],P[0]-Q[0],0]);origin=np.array([*P,0]);points=[]
for xx,yy in [(1712,394),(1714,470),(1719,550),(1728,620),(1745,701),(1770,784)]:
 ray=fw+r*((xx-960.5)/f)+u*((640-yy)/f);t=(origin-c)@normal/(ray@normal);pt=c+t*ray;points.append(pt.tolist());print(xx,yy,pt)
json.dump({'points':points,'pixels':[[1712,394],[1714,470],[1719,550],[1728,620],[1745,701],[1770,784]],'plane':'mapped south side wall plane, estimated camera'},open('cache/onebank_curve.json','w'),indent=2)
