"""Workspace relocation must not change code, resources, or input ownership."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from common.cli import main
from common.layout import agent_src
from common.locations import code_path, resource_path, workspace_root
from common.runtime import source_path
from common.storage import Storage


class LocationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / 'workspace'
        self.workspace.mkdir()
        self.data = Path(self.tmp.name) / 'data'
        self.cache = Path(self.tmp.name) / 'scratch'
        (self.workspace / 'storage.local.json').write_text(json.dumps({
            'data_root': str(self.data), 'cache_root': str(self.cache),
        }))
        self.env = patch.dict(os.environ, {'P4D_ROOT': str(self.workspace)}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_explicit_workspace_precedes_environment(self):
        other = Path(self.tmp.name) / 'other'
        other.mkdir()
        self.assertEqual(Storage.load(other).root, other)

    def test_p4d_root_precedes_legacy_alias(self):
        with patch.dict(os.environ, {'UWM_ROOT': '/missing/legacy'}):
            self.assertEqual(workspace_root(), self.workspace)

    def test_source_fallback_uses_configured_data_root(self):
        self.assertEqual(source_path('legacy_output', 'grid.npy'),
                         self.data / 'project/windfarm/input/legacy_output/grid.npy')
        self.assertEqual(source_path('legacy_output', 'grid.npy', scene='core008'),
                         self.data / 'project/south_ken/input/legacy_output/grid.npy')
        self.assertFalse(self.data.exists())

    def test_source_override_and_environment_precedence(self):
        external = Path(self.tmp.name) / 'external'
        (self.workspace / 'sources.local.json').write_text(json.dumps({'legacy_output': str(external)}))
        self.assertEqual(source_path('legacy_output', 'x.npy'), external / 'x.npy')
        with patch.dict(os.environ, {'UWM_SOURCE_LEGACY_OUTPUT': str(self.data)}):
            self.assertEqual(source_path('legacy_output', 'x.npy'), self.data / 'x.npy')

    def test_invalid_sources_are_reported_and_cannot_escape(self):
        for invalid in ([], {'legacy_output': 42}, {'legacy_output': 'relative'}):
            (self.workspace / 'sources.local.json').write_text(json.dumps(invalid))
            with self.assertRaises(ValueError):
                source_path('legacy_output')
        (self.workspace / 'sources.local.json').unlink()
        with self.assertRaises(ValueError):
            source_path('legacy_output', '../../../outside')
        with self.assertRaises(ValueError):
            source_path('../outside')

    def test_code_and_schemas_do_not_follow_workspace(self):
        self.assertEqual(agent_src(), ROOT / 'src/urban_geometry/agent')
        self.assertEqual(code_path('src/common/cli.py'), ROOT / 'src/common/cli.py')
        self.assertEqual(resource_path('schemas/run-manifest-v1.schema.json'), ROOT / 'schemas/run-manifest-v1.schema.json')
        with self.assertRaises(ValueError):
            code_path('src/../private')

    def test_validation_needs_no_workspace_or_workspace_schema(self):
        with patch.dict(os.environ, {'P4D_ROOT': '/nonexistent'}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['validate', str(ROOT / 'examples/contract-v1/manifest.json')]), 0)

    def test_explicit_empty_workspace_lists_no_scenes(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['--root', str(self.workspace), 'scenes']), 0)
        self.assertEqual(json.loads(output.getvalue()), [])


if __name__ == '__main__':
    unittest.main()
