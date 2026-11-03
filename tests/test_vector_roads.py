import importlib.util
import json
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

AVAILABLE = all(importlib.util.find_spec(k) for k in ('shapely','mapbox_earcut','numpy'))

@unittest.skipUnless(AVAILABLE, 'Install tools/requirements-vector-roads.txt')
class VectorRoadTests(unittest.TestCase):
    def fixture(self, root):
        source=root/'source';source.mkdir()
        part={'edges':[{'id':'e','lanes':[0]}], 'lanes':[{'id':'lane','edge':0,'width':4.,'shape':[[0,0,10],[10,0,20]]}], 'connections':[], 'junctions':[]}
        payload=json.dumps(part).encode();(source/'part.json').write_bytes(payload)
        index={'counts':{k:len(v) for k,v in part.items()},'chunks':[{'asset':'part.json','sha256':hashlib.sha256(payload).hexdigest()}],'provenance':{'fixture':True}}
        (source/'road_network.json').write_text(json.dumps(index))
        return source
    def exporter(self):
        spec=importlib.util.spec_from_file_location('vector_roads',Path(__file__).resolve().parents[1]/'src/visualization/export/vector_roads.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module.export
    def test_width_and_flattening_are_exact(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=self.fixture(root);out=root/'out';self.exporter()(source,out)
            data=(out/'roads.glb').read_bytes();length=struct.unpack_from('<I',data,12)[0];g=json.loads(data[20:20+length])
            primitive=g['meshes'][0]['primitives'][0];a=g['accessors'][primitive['attributes']['POSITION']]
            self.assertEqual([a['min'][0],a['max'][0]],[0,10]);self.assertEqual([a['min'][2],a['max'][2]],[-2,2])
            self.assertAlmostEqual(a['min'][1],.025,places=6);self.assertAlmostEqual(a['max'][1],.025,places=6)
            self.assertEqual((source/'part.json').read_bytes(),(out/'part.json').read_bytes())
            self.assertEqual(struct.unpack_from('<I',data,8)[0],len(data))
    def test_source_checksum_is_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=self.fixture(root);(source/'part.json').write_text('{}')
            with self.assertRaises(AssertionError):self.exporter()(source,root/'out')

if __name__=='__main__':unittest.main()
