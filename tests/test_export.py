import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from common.storage import Storage
from common.export import package_export
from common.runs import promote_bundle
from common.catalog import view


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        (self.root/'AGENTS.md').write_text('fixture');shutil.copytree(ROOT/'schemas',self.root/'schemas')
        self.source=self.root/'cache/trial/export';(self.source/'models').mkdir(parents=True);(self.source/'physics').mkdir()
        payload=json.dumps({'asset':{'version':'2.0'},'scenes':[{'nodes':[]}],'scene':0}).encode();payload+=b' '*((-len(payload))%4)
        (self.source/'models/city.glb').write_bytes(struct.pack('<4sII',b'glTF',2,20+len(payload))+struct.pack('<I4s',len(payload),b'JSON')+payload)
        np.save(self.source/'physics/wind.npy',np.ones((2,3,4,4),dtype='<f4'))
        (self.source/'physics/manifest.json').write_text(json.dumps({'arrays':{'wind.npy':{'time_s':[0,1]}}}))
        (self.source/'scene.json').write_text(json.dumps({'title':'Test','grid':{'x0':0,'z_south':0,'cols':4,'rows':4,'cell_m':1},'model':{'url':'models/city.glb'},'layers':{'wind':{'file':'wind.npy','cell_m':1,'y':2}}}))
        self.config={'scene':'test','georeference':{'latitude_deg':0,'longitude_deg':0,'terrain':'synthetic'},'domain':{'wind_layers':4}}
        self.storage=Storage.load(self.root)
    def test_trial_export_retain_and_register_view(self):
        bundle=package_export(self.storage,self.source,self.config,'trial_01')
        result=promote_bundle(self.storage,bundle)
        document,runs=view(self.storage,'test','run_trial_01')
        self.assertEqual(set(runs),{'trial_01_geometry','trial_01_wind'})
        self.assertTrue(result.is_file());self.assertTrue((bundle/'bundle.json').is_file())
        for run in runs:
            self.assertTrue((self.storage.run('test',run)/'provenance/source_snapshot.tar.gz').is_file())
        self.assertEqual(json.loads((self.root/'project/index.json').read_text())['default'],'test')
    def test_solar_date_is_a_valid_identifier_and_preserves_epoch(self):
        np.save(self.source/'physics/solar.npy',np.ones((2,4,4),dtype='<f4'))
        p=self.source/'physics/manifest.json';d=json.loads(p.read_text());d['arrays']['solar.npy']={'time_utc':['2026-06-21T10:00:00Z','2026-06-21T10:10:00Z']};p.write_text(json.dumps(d))
        p=self.source/'scene.json';d=json.loads(p.read_text());d['layers']['solar']={'cell_m':1,'dates':{'2026-06-21':{'ghi':'solar.npy'}}};p.write_text(json.dumps(d))
        bundle=package_export(self.storage,self.source,self.config,'solar_trial')
        m=json.loads((bundle/'solar_trial_solar_2026_06_21/manifest.json').read_text())
        self.assertEqual(m['time'],{'unit':'s','samples':[0,600],'epoch':'2026-06-21T10:00:00Z'})
        promote_bundle(self.storage,bundle)
    def test_does_not_replace_retained_view(self):
        bundle=package_export(self.storage,self.source,self.config,'trial_02');path=promote_bundle(self.storage,bundle);before=path.read_bytes()
        with self.assertRaises(FileExistsError):promote_bundle(self.storage,bundle)
        self.assertEqual(path.read_bytes(),before)
    def test_physical_height_and_obstacle_mask_survive_city_export(self):
        mask=np.zeros((2,4,4),dtype=bool);mask[1,1,2]=True
        np.save(self.source/'physics/solid.npy',mask)
        path=self.source/'physics/manifest.json';document=json.loads(path.read_text())
        document['arrays']['wind.npy']['layer_m']=[8,16];path.write_text(json.dumps(document))
        path=self.source/'scene.json';document=json.loads(path.read_text())
        document['masks']={'solid_wind':{'file':'solid.npy','layer':1}};path.write_text(json.dumps(document))
        bundle=package_export(self.storage,self.source,self.config,'mask_trial')
        manifest=json.loads((bundle/'mask_trial_wind/manifest.json').read_text())
        encoding=manifest['layers'][0]['encoding']
        self.assertEqual(encoding['origin_m'][2],12)
        self.assertEqual(encoding['mask_semantics'],'invalid_nonzero')
        np.testing.assert_array_equal(np.load(bundle/'mask_trial_wind'/encoding['mask_asset']),mask[1])
        promote_bundle(self.storage,bundle)
    def test_invalid_bundle_does_not_expose_runs(self):
        bundle=package_export(self.storage,self.source,self.config,'trial_03');file=bundle/'bundle.json';data=json.loads(file.read_text());data['view']['layers'][0]['layer_id']='missing';file.write_text(json.dumps(data))
        with self.assertRaises(ValueError):promote_bundle(self.storage,bundle)
        self.assertFalse(self.storage.run('test','trial_03_wind').exists())

if __name__=='__main__':unittest.main()
