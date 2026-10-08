"""Estimate Fig. B.31 rotor size from embedded raster mesh; diagnostic, not CAD."""
import argparse,json
from pathlib import Path
import numpy as np
import pymupdf
from scipy.signal import find_peaks
from scipy.ndimage import label,find_objects
from PIL import Image
from common.export import digest

def audit(pdf,out):
    out.mkdir(parents=True,exist_ok=True)
    doc=pymupdf.open(pdf);page=doc[23]
    candidates=[i for i in page.get_images(full=True) if i[2:4]==(1771,550)]
    if len(candidates)!=1:raise ValueError('Unexpected figure layout')
    image=doc.extract_image(candidates[0][0]);p=out/('figure_B31_embedded.'+image['ext']);p.write_bytes(image['image'])
    a=np.array(Image.open(p).convert('RGB'),dtype=float)[310:540,1225:1760]
    mask=(a[:,:,0]>110)&(a[:,:,2]>100)&(a[:,:,1]<80)
    y,x=np.where(mask);width=x.max()-x.min()+1;height=y.max()-y.min()+1
    rows=[]
    for axis,profile,extent,spacing in [('y',a[20:60].mean(axis=(0,2)),width,.046),('z',a[:,20:80].mean(axis=(1,2)),height,.033)]:
        peaks,_=find_peaks(-profile,prominence=25,distance=2)
        pitch=float(np.polyfit(np.arange(len(peaks)),peaks,1)[0])
        rows.append({'axis':axis,'diameter_pixels':int(extent),'mesh_pitch_pixels':pitch,'detected_grid_lines':len(peaks),
                     'diameter_cells':extent/pitch,'Table8_MM2_spacing_m':spacing,'inferred_diameter_m':extent/pitch*spacing,
                     'printed_diameter_m':.4647,'ratio_to_printed_diameter':extent/pitch*spacing/.4647})
    # Enclosed background component is the central hole, not the outside mesh.
    b=~mask[y.min():y.max()+1,x.min():x.max()+1]
    components,_=label(b)
    holes=[v for v in find_objects(components) if v[0].start>0 and v[1].start>0 and v[0].stop<b.shape[0] and v[1].stop<b.shape[1]]
    if len(holes)!=1:raise ValueError('Ambiguous inner-hole extraction')
    hole=holes[0]
    hole_sizes=[hole[1].stop-hole[1].start,hole[0].stop-hole[0].start]
    for r,size in zip(rows,hole_sizes):
        r['inner_hole_pixels']=size
        r['inferred_inner_diameter_m']=size/r['mesh_pitch_pixels']*r['Table8_MM2_spacing_m']
    side=np.array(Image.open(p).convert('RGB'),dtype=float)[13:247,1223:1763]
    sm=(side[:,:,0]>35)&(side[:,:,2]>35)&(side[:,:,1]<np.minimum(side[:,:,0],side[:,:,2])*.5)
    sy,sx=np.where(sm)
    peaks,_=find_peaks(-side[10:60].mean(axis=(0,2)),prominence=15,distance=2)
    axial_pitch=float(np.polyfit(np.arange(len(peaks)),peaks,1)[0])
    side_check={'thickness_pixels':int(sx.max()-sx.min()+1),'axial_grid_pitch_pixels':axial_pitch,'inferred_thickness_m':float((sx.max()-sx.min()+1)/axial_pitch*.033),'printed_thickness_m':.08,'interpretation':'Thickness remains consistent with text; approximately twofold discrepancy concerns radial dimensions.'}
    result={'source_pdf_sha256':digest(pdf),'source':'PDF page 24 Fig B.31(c); embedded image, no rescaling',
            'roi_pixels_xyxy':[1225,310,1760,540],'measurements':rows,'side_panel_crosscheck':side_check,
            'limitations':['Raster line detection and displayed mesh spacing are approximate; panel mesh identity must be confirmed with authors.',
                          'Horizontal/vertical size estimates disagree by several percent. They support an approximately twofold discrepancy, not an exact inferred diameter.',
                          'Cannot establish whether text, rendered geometry, grid table or postprocessing normalization is wrong.'],
            'hypothesis':'Text outer and inner diameters may instead have been implemented as radii; test D=.9294 and inner D=.18 separately, retain literal-text baseline.'}
    (out/'mesh_image_audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf',type=Path);p.add_argument('out',type=Path);a=p.parse_args();print(json.dumps(audit(a.pdf,a.out),indent=2))
