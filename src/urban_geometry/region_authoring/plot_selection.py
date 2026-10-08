"""Plot official borough context and retained building footprints for an AOI."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch
from matplotlib.patches import Patch as LegendPatch
from pyproj import Transformer
from shapely.geometry import shape, box
from shapely.ops import transform


def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);args=p.parse_args();root=args.project
    region=json.loads((root/'region.json').read_text());t=Transformer.from_crs(4326,region['executed_crs'],always_xy=True)
    aoi=transform(t.transform,box(*region['bbox_wgs84']))
    boroughs=json.loads((root/'references/boroughs.geojson').read_text())
    geometry=json.loads((root/'geometry.json').read_text())
    fig,axs=plt.subplots(1,2,figsize=(14,7),gridspec_kw={'width_ratios':[1,1.2]})
    fig.patch.set_facecolor('#f5f6f4')
    for ax in axs:
        ax.set_facecolor('#eef1f0');ax.set_aspect('equal');ax.tick_params(labelsize=8)
    def polygons(g):return [g] if g.geom_type=='Polygon' else list(g.geoms)
    th=None
    for f in boroughs['features']:
        g=transform(t.transform,shape(f['geometry']));name=f['properties']['name']
        if name=='Tower Hamlets':th=g
        for poly in polygons(g):axs[0].add_patch(Patch(poly.exterior.coords,facecolor='#c6dadc' if name=='Tower Hamlets' else '#e3e6e2',edgecolor='#849296',linewidth=.7))
    x0,y0,x1,y1=th.bounds;axs[0].set_xlim(x0-700,x1+700);axs[0].set_ylim(y0-500,y1+500)
    for f in boroughs['features']:
        g=transform(t.transform,shape(f['geometry']));c=g.representative_point()
        if x0-600<c.x<x1+600 and y0-400<c.y<y1+400:
            axs[0].text(c.x,c.y,f['properties']['name'],ha='center',fontsize=10,weight='medium')
    axs[0].add_patch(Patch(aoi.exterior.coords,fill=False,edgecolor='#c15c32',linewidth=2))
    axs[0].annotate('Selected: Canary Wharf',xy=(0,0),xytext=(-3700,-2200),arrowprops={'arrowstyle':'->','color':'#a6502c'},fontsize=10,color='#8f4023')
    axs[0].set_title('Tower Hamlets · official borough boundary',loc='left',fontsize=13)
    axs[0].set_xlabel('East from scene origin (m)');axs[0].set_ylabel('North from scene origin (m)')
    for r in geometry['buildings']:
        if r['kind']=='site':
            for part in r['water']:axs[1].add_patch(Patch(part['outer'],facecolor='#b6d7df',edgecolor='none'))
            continue
        color='#547e8a' if r['height_basis']=='source_reported_height' else '#c39d67'
        for part in r['geometry']:
            axs[1].add_patch(Patch(part['outer'],facecolor=color,edgecolor='#f5f6f4',linewidth=.15))
            for ring in part['holes']:axs[1].add_patch(Patch(ring,facecolor='#eef1f0',edgecolor='none'))
    axs[1].add_patch(Patch(aoi.exterior.coords,fill=False,edgecolor='#c15c32',linewidth=1.5))
    axs[1].set_xlim(-560,560);axs[1].set_ylim(-560,560)
    axs[1].set_title('Canary Wharf · approx. 1,000 × 1,000 m',loc='left',fontsize=13)
    axs[1].set_xlabel('East (m)');axs[1].set_ylabel('North (m)')
    axs[1].legend(handles=[LegendPatch(facecolor='#547e8a',label='Source-reported height'),LegendPatch(facecolor='#c39d67',label='Estimated height'),LegendPatch(facecolor='#b6d7df',label='Mapped water')],loc='upper left',fontsize=8)
    fig.text(.04,.035,'Boundary: GLA / Ordnance Survey, OGL v3 · Buildings/water: © OpenStreetMap contributors, Overture Maps Foundation (ODbL)\n2026-09-23.1 release · Unsurveyed flat ground · Complete intersecting footprints retained beyond selection',fontsize=8,color='#435054')
    fig.subplots_adjust(bottom=.16,top=.91,wspace=.24)
    (root/'renders').mkdir(exist_ok=True);fig.savefig(root/'renders/area-selection.png',dpi=160)


if __name__=='__main__':main()
