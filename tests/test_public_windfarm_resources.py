import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('public_build',Path(__file__).resolve().parents[1]/'tools/build_public_site.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ResourceSelectionTests(unittest.TestCase):
    def catalog(self,version):
        return {'resources_url':'https://example.test/resources/','scenes':[{'scene_id':'windfarm',
            'resource_ids':['windfarm_geometry_published_v1','windfarm_runs_'+version]}]}
    def test_movie_version_follows_catalogue(self):
        result=module.windfarm_resources(self.catalog('urans_10ms_v2'))
        self.assertTrue(result['data_base'].endswith('/runs/urans_10ms_v2/'))
        self.assertTrue(result['model'].endswith('/geometry/published_v1/region.glb'))
    def test_ambiguous_or_escaping_versions_are_rejected(self):
        bad=self.catalog('published_movie_v1');bad['scenes'][0]['resource_ids'].append('windfarm_runs_other')
        for catalog in (bad,self.catalog('../other')):
            with self.assertRaises(ValueError):module.windfarm_resources(catalog)
