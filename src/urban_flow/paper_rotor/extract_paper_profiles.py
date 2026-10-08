"""Extract Fig. B.33 vector data; requires PyMuPDF, never treats it as raw experiments."""
import argparse
import hashlib
import json
from pathlib import Path
import pymupdf


def extract(pdf):
    page=pymupdf.open(pdf)[23]
    drawings=page.get_drawings()
    panels=sorted([d['rect'] for d in drawings if d['fill']==(1.,1.,1.)
                   and 410<d['rect'].y0<590 and d['rect'].width>300],key=lambda r:r.y0)
    if len(panels)!=3:raise ValueError('Unexpected B.33 panel geometry')
    output=[]
    for distance,rect in zip((1,3,5),panels):
        def convert(x,y):return [(x-rect.x0)/rect.width*3-1.5,1-(y-rect.y0)/rect.height*1.2]
        curves={};points=[]
        for d in drawings:
            r=d['rect'];cx=(r.x0+r.x1)/2;cy=(r.y0+r.y1)/2
            if not rect.contains(pymupdf.Point(cx,cy)):continue
            if d['color'] in ((1.,0.,0.),(0.,0.,1.)) and len(d['items'])>10:
                values=[]
                for item in d['items']:
                    if item[0]!='l':raise ValueError('Unexpected non-linear curve segment')
                    if not values:values.append(convert(*item[1]))
                    values.append(convert(*item[2]))
                curves['kEpsilon' if d['color'][0] else 'kOmegaSST']=values
            if (d['fill']==(0.,0.,0.) and len(d['items'])==8
                and all(item[0]=='c' for item in d['items']) and 2<r.width<2.3 and abs(r.width-r.height)<.01):
                # First-panel legend marker is outside the data region vertically.
                if distance==1 and cx>430 and cy<432:continue
                points.append(convert(cx,cy))
        if set(curves)!={'kEpsilon','kOmegaSST'} or len(points)<20:raise ValueError('Incomplete figure extraction')
        output.append({'x_over_D':distance,'axes_pdf_points':list(rect),'curves':curves,'experimental_markers':sorted(points)})
    return {'source_pdf_sha256':hashlib.sha256(Path(pdf).read_bytes()).hexdigest(),'page':24,'figure':'B.33',
            'columns':['y_over_R','one_minus_U_over_Uref'],'method':'PDF vector paths and ring centres; axes visually identified as [-1.5,1.5] and [-0.2,1.0]',
            'raw_experimental_data':False,'uncertainty':'Plot digitization; marker centre precision does not establish original measurement accuracy.','profiles':output}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pdf',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    data=extract(a.pdf);a.output.write_text(json.dumps(data,indent=2)+'\n')
    print([(v['x_over_D'],len(v['experimental_markers'])) for v in data['profiles']])
