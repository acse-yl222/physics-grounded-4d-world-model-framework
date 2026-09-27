import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from common.storage import Storage
from common.runs import promote


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'
        self.root.mkdir()
        (self.root / 'AGENTS.md').write_text('test repository')
        (self.root / 'schemas').mkdir()
        shutil.copy(ROOT / 'schemas/run-manifest-v1.schema.json', self.root / 'schemas')

    def configure(self, **settings):
        (self.root / 'storage.local.json').write_text(json.dumps(settings))

    def fixture(self):
        path = self.root / 'cache/south_ken/contract_demo/synthetic_v1'
        shutil.copytree(ROOT / 'examples/contract-v1', path)
        return path

    def test_default_and_alias(self):
        storage = Storage.load(self.root)
        self.assertEqual(storage.metadata('core008'), self.root / 'project/south_ken')
        self.assertEqual(storage.assets('white_city', 'input'), self.root / 'project/white_city/input')
        self.assertFalse((self.root / 'project').exists())

    def test_external_data_keeps_metadata_local(self):
        data = Path(self.tmp.name) / 'disk'
        self.configure(data_root=str(data))
        storage = Storage.load(self.root)
        self.assertEqual(storage.assets('south_ken', 'runs'), data / 'project/south_ken/runs')
        self.assertEqual(storage.metadata('south_ken'), self.root / 'project/south_ken')

    def test_reject_relative_storage(self):
        self.configure(data_root='somewhere')
        with self.assertRaises(ValueError): Storage.load(self.root)

    def test_reject_cache_containing_repository(self):
        self.configure(cache_root=self.tmp.name)
        with self.assertRaises(ValueError): Storage.load(self.root)

    def test_reject_cache_in_retained_data(self):
        self.configure(cache_root=str(self.root / 'project/white_city/runs/cache'))
        with self.assertRaises(ValueError): Storage.load(self.root)

    def test_reject_path_escape(self):
        storage = Storage.load(self.root)
        with self.assertRaises(ValueError): storage.run('south_ken', '../../outside')
        with self.assertRaises(ValueError): storage.metadata('../white_city')

    def test_reject_escaping_symlink(self):
        (self.root / 'project').mkdir()
        (self.root / 'project/south_ken').symlink_to(Path(self.tmp.name) / 'external')
        with self.assertRaises(ValueError): Storage.load(self.root).assets('south_ken', 'runs')

    def test_retain_copies_assets_without_mutating_trial(self):
        source = self.fixture()
        (source / 'scratch.tmp').write_text('disposable')
        result = promote(Storage.load(self.root), source)
        self.assertTrue((result / 'manifest.json').is_file())
        self.assertTrue((source / 'data/vector_field.json').is_file())
        self.assertFalse((result / 'scratch.tmp').exists())
        self.assertEqual((result / 'data/mesh.json').read_bytes(), (source / 'data/mesh.json').read_bytes())

    def test_cannot_overwrite_retained_run(self):
        source = self.fixture()
        storage = Storage.load(self.root)
        result = promote(storage, source)
        before = (result / 'manifest.json').read_bytes()
        with self.assertRaises(FileExistsError): promote(storage, source)
        self.assertEqual((result / 'manifest.json').read_bytes(), before)
        self.assertFalse((result.parent / '.synthetic_v1.lock').exists())

    def test_invalid_trial_does_not_create_retained_run(self):
        source = self.fixture()
        (source / 'data/mesh.json').unlink()
        storage = Storage.load(self.root)
        with self.assertRaises(ValueError): promote(storage, source)
        self.assertFalse(storage.run('south_ken', 'synthetic_v1').exists())

    def test_running_trial_is_not_promoted(self):
        source = self.fixture()
        path = source / 'manifest.json'
        manifest = json.loads(path.read_text())
        manifest['status'] = 'running'
        path.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError): promote(Storage.load(self.root), source)

    def test_lock_blocks_concurrent_writer(self):
        source = self.fixture()
        storage = Storage.load(self.root)
        destination = storage.run('south_ken', 'synthetic_v1')
        destination.parent.mkdir(parents=True)
        lock = destination.parent / '.synthetic_v1.lock'
        lock.write_text('another writer')
        with self.assertRaises(FileExistsError): promote(storage, source)
        self.assertEqual(lock.read_text(), 'another writer')


if __name__ == '__main__':
    unittest.main()
