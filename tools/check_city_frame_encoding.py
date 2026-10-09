"""Check every browser PNG against its scientific array and report quantization."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image

def check(root):
    root=Path(root);physics=root/'physics';index=json.loads((physics/'web/index.json').read_text());reports={}
    for key,m in index['layers'].items():
        data=np.load(physics/m['source'],mmap_mode='r');lo,hi=m['range'];worst=0.;clipped=0
        for i,a in enumerate(data):
            pixels=np.asarray(Image.open(physics/'web'/key/f"{i:03d}.{m.get('extension','png')}"))
            if m['kind']=='rgb3':pixels=pixels.transpose(2,0,1)
            if m['kind']=='bit':
                if not np.array_equal(pixels>0,a>0):raise ValueError('Shadow mismatch')
                continue
            transform=m.get('value_transform');v=a.astype('f4')
            if transform=='log1p':v=np.log10(1+np.maximum(v,0)/m['value_scale'])
            elif transform=='log10':v=np.log10(np.maximum(v,.1))
            expected=np.clip(np.round((v-lo)/(hi-lo)*255),0,255).astype('u1')
            if not np.array_equal(pixels,expected):raise ValueError(f'Encoded mismatch {key}/{i}')
            d=lo+pixels.astype('f4')/255*(hi-lo)
            if transform=='log1p':d=m['value_scale']*(10**d-1)
            elif transform=='log10':d=10**d
            if np.any((a==0)&(d!=0)) and transform=='log1p':raise ValueError('Zero pollution changed')
            worst=max(worst,float(np.max(np.abs(d-a))));clipped+=int(np.count_nonzero((v<lo)|(v>hi)))
        if clipped:raise ValueError(f'Browser encoding clips {clipped} scientific values in {key}')
        reports[key]={'frames':len(data),'max_absolute_error':worst,'clipped_values':clipped,'passed':True}
    (root/'browser_encoding_check.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root');check(p.parse_args().root)
