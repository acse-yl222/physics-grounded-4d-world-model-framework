"""Inspect paired OGL Environment Agency elevation grids without modifying geometry."""
from pathlib import Path
import json
import rasterio
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent/'input/canary_wharf_20261007/references'
with rasterio.open(root/'ea_dsm_1m.tif') as a, rasterio.open(root/'ea_dtm_1m.tif') as b:
    assert a.crs==b.crs and a.transform==b.transform and a.shape==b.shape
    dsm=a.read(1,masked=True);dtm=b.read(1,masked=True);ndsm=dsm-dtm
    extent=[a.bounds.left,a.bounds.right,a.bounds.bottom,a.bounds.top]
    report={'shape':list(a.shape),'crs':str(a.crs),'resolution_m':list(a.res),'vertical_reference':'Elevation metres ODN; difference metres above modelled terrain','difference_percentiles_m':np.percentile(ndsm.compressed(),[0,1,50,95,99,100]).tolist(),'negative_difference_cells':int(np.sum(ndsm<0)),'geometry_modified':False,'caveats':['Mixed source survey vintage','Trees and roof equipment contribute to DSM','Negative surface differences retained for quality review, not clamped','Water and glass roofs require inspection before interpretation']}
fig,axes=plt.subplots(1,2,figsize=(14,7),layout='constrained')
for ax,data,title,vmin,vmax in [(axes[0],dtm,'Terrain elevation (m ODN)',-2,12),(axes[1],ndsm,'Surface minus terrain (m)',0,240)]:
    im=ax.imshow(data,extent=extent,origin='upper',vmin=vmin,vmax=vmax,cmap='viridis',interpolation='none')
    ax.set_title(title);ax.set_xlabel('Easting (EPSG:27700)');ax.set_ylabel('Northing');ax.ticklabel_format(style='plain',useOffset=False)
    fig.colorbar(im,ax=ax,shrink=.65)
fig.suptitle('Canary Wharf — Environment Agency 1 m LiDAR subset\nMixed survey dates; height evidence, not a current-year survey')
fig.text(.5,.005,'Contains Environment Agency information © Environment Agency copyright/database right 2022. OGL v3.',ha='center',fontsize=8)
fig.savefig(root/'lidar-height-review.png',dpi=160)
(root/'lidar_height_review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
