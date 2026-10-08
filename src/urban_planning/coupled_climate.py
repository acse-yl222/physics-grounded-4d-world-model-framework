"""Controlled geometry -> shadow / MAC wind -> physical temperature screening.

Reuses the repository's numerical solvers. No trained surrogate, buoyancy,
turbulence closure, measured weather or pedestrian-comfort claim.
"""
import hashlib
import itertools
import json
import math
from pathlib import Path
from types import SimpleNamespace
import time

import numpy as np

from .problem import write_json
from .traffic_morphology import aggregate, compute_wind


BASE = {'height_steps': [0, 0, 0, 0], 'cool_sectors': []}
ACTION = {
    'type': 'object', 'additionalProperties': False,
    'required': ['action', 'plan', 'reason'],
    'properties': {
        'action': {'type': 'string', 'enum': ['evaluate', 'submit']},
        'plan': {'type': 'object', 'additionalProperties': False,
                 'required': ['height_steps', 'cool_sectors'],
                 'properties': {
                     'height_steps': {'type': 'array', 'minItems': 4, 'maxItems': 4,
                                      'items': {'type': 'integer', 'enum': [-1, 0, 1]}},
                     'cool_sectors': {'type': 'array', 'maxItems': 2, 'uniqueItems': True,
                                      'items': {'type': 'integer', 'minimum': 0, 'maximum': 3}}}},
        'reason': {'type': 'string', 'maxLength': 1200}}}


def key(plan):
    return json.dumps({'height_steps': plan['height_steps'],
                       'cool_sectors': sorted(plan['cool_sectors'])}, sort_keys=True)


def face_centres(faces, inlet):
    """Average positive and negative MAC faces to a cell-centred velocity."""
    result = []
    for component, face in enumerate(faces):
        axis = 2-component
        previous = np.roll(face, 1, axis)
        lower = [slice(None)]*3
        lower[axis] = 0
        previous[tuple(lower)] = inlet if component == 0 else 0
        result.append((face+previous)*.5)
    return np.asarray(result, dtype=np.float32)


class ClimateProblem:
    def __init__(self, directory):
        from common.pipeline.scene_temperature_physical import load_solver
        self.root = Path(directory)
        self.cfg = json.loads((self.root/'config.json').read_text())
        for split in ('development', 'holdout'):
            for weather in self.cfg[split+'_weather']:
                if 'rotation' in weather:
                    expected = ('west', 'south', 'east', 'north')[weather['rotation']]
                    if weather.get('inflow_from') != expected:
                        raise ValueError('Wind label disagrees with row-positive-north array rotation')
        with np.load(self.root/'inputs.npz', allow_pickle=False) as data:
            raw = aggregate(data['south_ken_roof4'], 2, 'max')
        self.cell = self.cfg['cell_m']
        # Conservative voxel-aligned roofs keep shadow and solid geometry consistent.
        self.roof = np.ceil(raw/self.cell)*self.cell
        y, x = np.indices(self.roof.shape)
        self.sector = (x >= x.shape[1]//2).astype(int)+2*(y >= y.shape[0]//2).astype(int)
        self.receptor = self.roof == 0
        b = self.cfg['receptor_boundary_buffer_m']//self.cell
        self.receptor[:b] = False; self.receptor[-b:] = False
        self.receptor[:, :b] = False; self.receptor[:, -b:] = False
        self.model, self.thermal_source = load_solver()
        self.baselines = {}

    def geometry(self, plan):
        height = self.roof.copy()
        for sector, step in enumerate(plan['height_steps']):
            mask = (self.sector == sector) & (self.roof > 0)
            height[mask] = np.maximum(self.cell, height[mask]+step*self.cell)
        return height

    def validate(self, plan):
        import jsonschema
        try:
            jsonschema.validate(plan, ACTION['properties']['plan'])
        except jsonschema.ValidationError:
            return ['Invalid plan schema']
        cost = sum(abs(x) for x in plan['height_steps'])+2*len(plan['cool_sectors'])
        ratio = float(self.geometry(plan).sum()/self.roof.sum())
        errors = []
        if cost > self.cfg['construction_budget']: errors.append('Construction budget exceeded')
        if not self.cfg['volume_ratio_min'] <= ratio <= self.cfg['volume_ratio_max']:
            errors.append('Building volume proxy outside permitted range')
        return errors

    def plans(self):
        result = []
        for heights in itertools.product((-1, 0, 1), repeat=4):
            for n in range(3):
                for cool in itertools.combinations(range(4), n):
                    plan = {'height_steps': list(heights), 'cool_sectors': list(cool)}
                    if not self.validate(plan): result.append(plan)
        return result

    def simulate(self, plan, weather):
        import torch
        from common.pipeline.scene_temperature_physical import fields_and_boundary
        from urban_flow.physics.diurnal_solver import solve_from_state
        from urban_flow.physics.solar.model import ShadowNet, clear_sky
        identity = hashlib.sha256((key(plan)+json.dumps(weather, sort_keys=True)).encode()).hexdigest()[:20]
        out = self.root/'simulations'/identity
        if (out/'result.json').exists():
            return json.loads((out/'result.json').read_text())
        started = time.perf_counter()
        cfg = self.cfg
        roof = self.geometry(plan)
        zz = (np.arange(cfg['height_m']//self.cell)+.5)*self.cell
        solid = zz[:, None, None] < roof[None]
        rotation = weather['rotation']
        fluid_rotated = np.rot90(~solid, rotation, axes=(1, 2)).copy()
        flow_cfg = dict(cfg, inlet_speed_m_s=weather['speed_m_s'])
        # Materials do not affect this one-way wind model. Reuse only identical
        # geometry + wind forcing within the frozen run; queries still cost budget.
        flow_key = hashlib.sha256(json.dumps([plan['height_steps'], rotation, weather['speed_m_s']]).encode()).hexdigest()[:20]
        flow_out = self.root/'flows'/flow_key
        if (flow_out/'report.json').exists():
            with np.load(flow_out/'faces.npz') as data:
                faces = list(data['faces']); inlet = data['inlet']
            flow = json.loads((flow_out/'report.json').read_text())
        else:
            faces, inlet, flow = compute_wind(fluid_rotated, self.cell, flow_cfg, cfg['flow_duration_s'])
            flow_out.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(flow_out/'faces.npz', faces=np.asarray(faces), inlet=inlet)
            write_json(flow_out/'report.json', flow)
        if max(record['divergence_rms'] for record in flow['records']) > 5e-5:
            raise ValueError('Wind divergence quality gate failed')
        wind = face_centres(faces, inlet)
        altitude, azimuth = weather['sun_altitude_deg'], weather['sun_azimuth_deg']
        with torch.inference_mode():
            shadow = ShadowNet(roof, self.cell, 'cpu')(altitude, azimuth).numpy()
        dni, diffuse = clear_sky(altitude, 6)
        irradiance = (~shadow)*dni*math.sin(math.radians(altitude))+diffuse
        albedo = np.full(roof.shape, .2)
        for sector in plan['cool_sectors']:
            albedo[(self.sector == sector) & (roof == 0)] = .6
        ambient = weather['ambient_c']
        excess = self.model.solve_surface_temperature_excess_c(
            (1-albedo)*irradiance, np.full(roof.shape, .95), np.zeros(roof.shape),
            np.full(roof.shape, .3), np.full(roof.shape, 12.),
            5.670374419e-8*(ambient+273.15)**4, ambient, 0.)
        excess_rotated = np.rot90(excess, rotation).copy()
        fields, boundary = fields_and_boundary(~fluid_rotated, wind[None], ambient, 0., cfg['exchange_per_s'])
        boundary['ground_surface_temperature_excess_c'] = excess_rotated
        boundary['roof_surface_temperature_excess_3d'] = fields['roof_mask_3d']*excess_rotated[None]
        thermal = self.model.Temperature3DScenarioConfig(
            temperature_solver_device='cpu', ambient_temp_c=ambient, inflow_temp_c=ambient,
            frame_duration_s=cfg['thermal_duration_s'], diffusion_coeff_m2_s=1.)
        temperature, fluid, thermal_check = solve_from_state(
            self.model, fields, boundary, SimpleNamespace(model_resolution_m=self.cell, height_scale_m=self.cell),
            thermal, np.full(fluid_rotated.shape, ambient, dtype=np.float32))
        if not np.isfinite(temperature).all(): raise ValueError('Non-finite temperature')
        air = np.rot90(temperature[1], -rotation).copy()
        speed = np.rot90(np.linalg.norm(wind[:, 1], axis=0), -rotation).copy()
        values = air[self.receptor]
        result = {
            'simulation_id': identity, 'weather': weather['id'], 'plan': plan,
            'p95_excess_c': float(np.quantile(values, .95)-ambient),
            'mean_excess_c': float(values.mean()-ambient),
            'sector_mean_excess_c': [float(air[self.receptor & (self.sector == i)].mean()-ambient) for i in range(4)],
            'stagnant_fraction': float((speed[self.receptor] < cfg['stagnant_speed_m_s']).mean()),
            'mean_speed_m_s': float(speed[self.receptor].mean()),
            'sunlit_receptor_fraction': float((~shadow[self.receptor]).mean()),
            'flow': flow, 'thermal': thermal_check, 'wall_seconds': time.perf_counter()-started}
        out.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out/'fields.npz', air_c=air, speed_m_s=speed, roof_m=roof,
                            receptor_mask=self.receptor, shadow=shadow,
                            temperature_rotated_c=temperature, wind_centred_rotated=wind,
                            solid_rotated=~fluid_rotated, surface_excess_rotated_c=excess_rotated)
        write_json(out/'result.json', result)
        return result

    def evaluate(self, plan, split='development'):
        if split not in ('development', 'holdout'): raise ValueError('Unknown split')
        errors = self.validate(plan)
        if errors: return {'plan': plan, 'feasible': False, 'errors': errors, 'score': -1., 'constraint': 1.}
        weather = self.cfg[split+'_weather']
        if split not in self.baselines:
            self.baselines[split] = [self.simulate(BASE, w) for w in weather]
        results = [self.simulate(plan, w) for w in weather]
        rows = []
        for result, base in zip(results, self.baselines[split]):
            cooling = 1-result['p95_excess_c']/max(base['p95_excess_c'], .01)
            sector_increase = max(np.asarray(result['sector_mean_excess_c'])-base['sector_mean_excess_c'])
            stagnant_increase = result['stagnant_fraction']-base['stagnant_fraction']
            rows.append({'weather': result['weather'], 'p95_excess_c': result['p95_excess_c'],
                         'p95_cooling_fraction': float(cooling), 'worst_sector_increase_c': float(sector_increase),
                         'stagnant_fraction_increase': float(stagnant_increase),
                         'mean_speed_m_s': result['mean_speed_m_s'], 'sector_mean_excess_c': result['sector_mean_excess_c'],
                         'simulation_id': result['simulation_id']})
        violation = max(max(row['worst_sector_increase_c']/self.cfg['max_sector_warming_c']-1,
                            row['stagnant_fraction_increase']/self.cfg['max_stagnant_increase']-1) for row in rows)
        return {'plan': plan, 'split': split, 'feasible': violation <= 1e-8,
                'score': min(row['p95_cooling_fraction'] for row in rows), 'constraint': float(violation),
                'cost_units': sum(abs(x) for x in plan['height_steps'])+2*len(plan['cool_sectors']),
                'volume_ratio': float(self.geometry(plan).sum()/self.roof.sum()), 'weather': rows}

    def brief(self):
        return {'objective': 'Maximize the worst-weather fractional reduction of p95 air-temperature excess above ambient.',
                'sector_order': ['south_west', 'south_east', 'north_west', 'north_east'],
                'actions': 'height_steps changes all existing roofs in a sector by -8, 0 or +8 m, clipped to minimum 8 m. cool_sectors raises only open-ground albedo from 0.2 to 0.6.',
                'constraints': {k: self.cfg[k] for k in ('construction_budget', 'volume_ratio_min', 'volume_ratio_max',
                                'max_sector_warming_c', 'max_stagnant_increase', 'stagnant_speed_m_s')},
                'cost_rule': '1 per nonzero height step plus 2 per cool sector; at most 2 cool sectors.',
                'sector_baseline_roof_height_sums_m': [float(self.roof[self.sector == i].sum()) for i in range(4)],
                'sector_building_cells': [int(((self.sector == i) & (self.roof > 0)).sum()) for i in range(4)],
                'sector_receptor_cells': [int(((self.sector == i) & self.receptor).sum()) for i in range(4)],
                'development_weather': self.cfg['development_weather'],
                'rotation_convention': 'Arrays have row-positive north; np.rot90 quarter turns 0,1,2,3 correspond to inflow from west,south,east,north.',
                'scope': self.cfg['scope'], 'baseline': self.evaluate(BASE)}
