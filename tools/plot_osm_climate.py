"""Plot retained campus inputs and climate results without rerunning simulations."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Polygon as PolygonPatch
import numpy as np

from common.storage import Storage
from traffic.sumo_pipeline import lonlat_to_scene, scene_to_lonlat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene')
    arguments = parser.parse_args()
    storage = Storage.load()
    metadata = storage.metadata(arguments.scene)
    output = metadata / 'reports'
    output.mkdir(parents=True, exist_ok=True)
    config = json.loads((metadata / 'configs/osm_climate.json').read_text())
    traffic = json.loads((metadata / 'configs/traffic.json').read_text())
    geometry_id = json.loads((metadata / 'configs/geometry_result.json').read_text())['run_id']
    geometry = storage.run(arguments.scene, geometry_id)
    document = ET.parse(geometry / 'map.osm.xml').getroot()
    nodes = {element.get('id'): [float(element.get('lon')), float(element.get('lat'))] for element in document.findall('node')}
    roads, campus = [], None
    for way in document.findall('way'):
        tags = {tag.get('k'): tag.get('v') for tag in way.findall('tag')}
        references = [element.get('ref') for element in way.findall('nd')]
        if any(reference not in nodes for reference in references):
            continue
        if tags.get('highway') or way.get('id') == '395256540':
            points = lonlat_to_scene([nodes[reference] for reference in references], traffic['transform'])
            if tags.get('highway'):
                roads.append(points)
            if way.get('id') == '395256540':
                campus = points
    figures, axes = plt.subplots(2, 3, figsize=(14, 9), constrained_layout=True)
    for row, scenario in enumerate(config['weather']):
        result = json.loads((metadata / 'configs' / (scenario['id'] + '_result.json')).read_text())
        folder = storage.run(arguments.scene, result['run_id'])
        invalid = np.load(folder / 'invalid.npy').astype(bool)
        wind = np.load(folder / 'wind.npy')
        fields = [np.ma.masked_where(invalid, np.linalg.norm(wind, axis=0)),
                  np.ma.masked_where(invalid, np.load(folder / 'temperature.npy')[-1]), np.load(folder / 'surface.npy')]
        labels = ['Wind at 12 m [m/s]', 'Air at 12 m, t = 600 s [°C]', 'Surface temperature [°C]']
        for column, (field, label) in enumerate(zip(fields, labels)):
            axis = axes[row, column]
            plot = axis.imshow(field, origin='lower', extent=[-1000, 1000, -1000, 1000], cmap='viridis' if column == 0 else 'inferno')
            if campus is not None:
                axis.plot(campus[:, 0], campus[:, 1], color='#56e2db', linewidth=1)
            axis.set_title(scenario['id'].capitalize() + ' · ' + label, fontsize=10)
            axis.set_xlabel('East [m]')
            axis.set_ylabel('North [m]')
            axis.set_xlim(-1000, 1000)
            axis.set_ylim(-1000, 1000)
            figures.colorbar(plot, ax=axis, shrink=.8)
    figures.suptitle('Thapar University + surroundings | 2 km × 2 km\nExploratory simulations: assumed building heights/materials; not validated local weather', fontsize=13)
    figures.savefig(output / 'climate_overview.png', dpi=160)
    plt.close(figures)
    figure, axis = plt.subplots(figsize=(9, 9), constrained_layout=True)
    axis.set_facecolor('#f3f4ef')
    if campus is not None:
        axis.add_patch(PolygonPatch(campus, facecolor='#e0eddf', edgecolor='#19766d', linewidth=2, label='Mapped campus boundary'))
    axis.add_collection(LineCollection(roads, colors='#808c94', linewidths=.7, label='OSM roads and paths'))
    features = json.loads((geometry / 'footprints_local.json').read_text())['features']
    for feature in features:
        coordinates = feature['geometry']['coordinates']
        polygons = [coordinates] if feature['geometry']['type'] == 'Polygon' else coordinates
        assumed = feature['properties']['height_basis'] == 'assumed_unknown_height'
        for polygon in polygons:
            axis.add_patch(PolygonPatch(polygon[0], facecolor='#d48b5a' if assumed else '#497994', edgecolor='white', linewidth=.3))
            for hole in polygon[1:]:
                axis.add_patch(PolygonPatch(hole, facecolor='#f3f4ef', edgecolor='white', linewidth=.3))
    axis.set(xlim=(-1000, 1000), ylim=(-1000, 1000), xlabel='East [m]', ylabel='North [m]', aspect='equal')
    axis.set_title('Thapar University, Patiala | proposed 2 km × 2 km study area\nOrange: assumed 9 m height; blue: height/levels tags\nMapped footprints only: completeness has not been verified', fontsize=12)
    axis.legend(loc='lower left')
    axis.text(.99, .01, '© OpenStreetMap contributors · ODbL 1.0', transform=axis.transAxes, ha='right', fontsize=8)
    figure.savefig(output / 'study_area.png', dpi=160)
    plt.close(figure)
    bounds = scene_to_lonlat([[-1000, -1000], [1000, 1000]], traffic['transform'])
    report = {'bbox_wgs84_west_south_east_north': bounds.flatten().tolist(),
              'campus_boundary_present': campus is not None,
              'campus_boundary_inside_focus': bool(campus is not None and (np.abs(campus) <= 1000).all()),
              'campus_way_id': '395256540', 'road_and_path_ways_in_download': len(roads)}
    (output / 'spatial_check.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
