"""Coordinate, time, input-isolation and settings checks for shared city tools."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from common.storage import Storage
from common.city import field_spec,sample_field
from common.city_tools import call
from traffic.sumo_pipeline import lonlat_to_scene,scene_to_lonlat,validate_settings,clip_segment
from urban_flow.physics.city_diurnal import block_mean,building_columns


class CityTests(unittest.TestCase):
    def test_thermal_ground_is_not_artificially_solid(self):
        h=np.zeros((8,8));footprint=np.zeros((8,8),bool)
        h[:4,:4]=12;footprint[:4,:4]=True
        solid=building_columns(h,footprint)
        self.assertEqual(solid[:,0,0].tolist(),[True,True,False,False,False,False,False,False])
        self.assertFalse(solid[:,:,1].any())

    def test_clip_crossing_road_without_connecting_disjoint_segments(self):
        bounds={'min':[0,0,0],'max':[10,10,10]}
        np.testing.assert_allclose(clip_segment([-5,5],[15,5],bounds),[[0,5],[10,5]])
        self.assertIsNone(clip_segment([-5,11],[15,11],bounds))
        np.testing.assert_allclose(clip_segment([5,5],[5,15],bounds),[[5,5],[5,10]])

    def test_geographic_roundtrip_preserves_city_specific_alignment(self):
        root=Path(__file__).resolve().parents[1]
        for scene in ('south_ken','white_city'):
            t=json.loads((root/'project'/scene/'configs/traffic.json').read_text())['transform']
            points=np.array([[0.,0.],[-1400.,1000.],[1200.,-1800.]])
            np.testing.assert_allclose(lonlat_to_scene(scene_to_lonlat(points,t),t),points,atol=1e-8)
            np.testing.assert_allclose(lonlat_to_scene([[t['lon0'],t['lat0']]],t)[0],t['t'],atol=1e-9)
        self.assertGreater(abs(t['R'][0][1]),.03) # White City's recorded rotation must survive.

    def test_field_uses_recorded_time_and_physical_height_not_display_lift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);storage=Storage(root,root,root/'cache');base=storage.run('south_ken','legacy_web');(base/'physics').mkdir(parents=True)
            array=np.array([[[1.,2.],[3.,4.]],[[5.,6.],[7.,8.]]],dtype='<f4');np.save(base/'physics/temp.npy',array)
            (base/'scene.json').write_text(json.dumps({'grid':{'x0':-10,'z_south':20},'layers':{'temp':{'file':'temp.npy','cell_m':2,'y':.6,'t0_s':1000}}}))
            (base/'physics/manifest.json').write_text(json.dumps({'arrays':{'temp.npy':{'shape':[2,2,2],'time_s':[0,10],'layer_m':[12,16]}}}))
            result=sample_field(storage,'south_ken','temperature',-9,-19,5)
            self.assertEqual(result['value'],3.)
            self.assertEqual(result['sample_height_m'],14.)
            for x,y,t in [(-11,-19,5),(-9,-19,11),(-9,-19,-1),(float('nan'),-19,5)]:
                with self.assertRaises(ValueError):sample_field(storage,'south_ken','temperature',x,y,t)

    def test_solar_local_clock_uses_london_dst(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);storage=Storage(root,root,root/'cache');base=storage.run('south_ken','legacy_web');(base/'physics').mkdir(parents=True)
            np.save(base/'physics/sun.npy',np.ones((2,1,1),dtype='<f4'))
            (base/'scene.json').write_text(json.dumps({'grid':{'x0':0,'z_south':0},'layers':{'solar':{'cell_m':4,'dates':{'20260621':{'ghi':'sun.npy'}}}}}))
            (base/'physics/manifest.json').write_text(json.dumps({'arrays':{'sun.npy':{'shape':[2,1,1],'time_local':['10:00','10:10']}}}))
            spec=field_spec(storage,'south_ken','solar')
            self.assertEqual(spec['epoch'],'2026-06-21T09:00:00+00:00');self.assertEqual(spec['samples'],[0.,600.])

    def test_thermal_coarsening_preserves_area_mean(self):
        values=np.arange(128,dtype=float).reshape(2,8,8)
        result=block_mean(values,4,4)
        np.testing.assert_allclose(result.mean(axis=(-1,-2)),values.mean(axis=(-1,-2)))
        with self.assertRaises(ValueError):block_mean(values,3,3)

    def test_traffic_rejects_invalid_or_mislabelled_experiments(self):
        root=Path(__file__).resolve().parents[1]
        cfg=json.loads((root/'project/south_ken/configs/traffic.json').read_text());validate_settings(cfg)
        for factor in (0,-1,float('nan'),3):
            bad=copy.deepcopy(cfg);bad['intervention']['speed_factor']=factor
            with self.assertRaises(ValueError):validate_settings(bad)
        bad=copy.deepcopy(cfg);bad['demand']['calibration_status']='measured'
        with self.assertRaises(ValueError):validate_settings(bad)

    def test_agent_tool_rejects_unknown_scene_and_arguments(self):
        with self.assertRaises(ValueError):call(None,'unknown','city.inspect',{})
        with self.assertRaises(ValueError):call(None,'white_city','city.inspect',{'arbitrary':1})


if __name__=='__main__':unittest.main()
