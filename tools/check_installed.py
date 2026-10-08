"""Check a wheel installation from any directory, without an editable checkout."""
import functools
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tarfile
import tempfile
import threading
import urllib.request

import common
from common.catalog import schema_check
from common.cli import main
from common.locations import resource_path
from common.provenance import snapshot_sources
from common.server import ViewerHandler
from common.storage import Storage


def check():
    if Path(common.__file__).resolve().parent.parent.name == 'src':
        raise RuntimeError('Run with a wheel installation, not PYTHONPATH or an editable checkout')
    manifest = resource_path('examples/contract-v1/manifest.json')
    if main(['validate', str(manifest)]) != 0:
        raise RuntimeError('Installed contract validation failed')
    document = json.loads(manifest.read_text())
    schema_check({'schema_version': '1.1.0', 'scene_id': 'south_ken', 'title': 'Wheel test',
                  'spatial': document['spatial'], 'inputs': [], 'default_view': 'default'}, 'project-v1.schema.json')
    with tempfile.TemporaryDirectory() as directory:
        storage = Storage.load(directory)
        archive = Path(directory) / 'source.tar.gz'
        snapshot_sources(storage.root, archive)
        with tarfile.open(archive) as handle:
            names = handle.getnames()
            if 'src/common/cli.py' not in names or any('site-packages' in name for name in names):
                raise RuntimeError('Source snapshot includes the wrong installation tree')
            owned = ('src/common/', 'src/urban_geometry/', 'src/urban_flow/',
                     'src/traffic/', 'src/uav_routing/', 'src/visualization/', 'schemas/')
            if any(not name.startswith(owned) and name not in ('AGENTS.md', 'pyproject.toml') for name in names):
                raise RuntimeError('Source snapshot contains unrelated dependency packages')
            if 'src/visualization/widgets/index.mjs' not in names:
                raise RuntimeError('Source snapshot lost the installed viewer code')
        server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(ViewerHandler, storage=storage))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}'
            for path in ('/', '/src/visualization/viewer/', '/src/visualization/viewer/main.mjs',
                         '/src/visualization/vendor/three/build/three.module.js',
                         '/examples/contract-v1/manifest.json', '/schemas/run-manifest-v1.schema.json'):
                with urllib.request.urlopen(base + path, timeout=10) as response:
                    if response.status != 200 or not response.read():
                        raise RuntimeError(f'Installed resource missing: {path}')
            with urllib.request.urlopen(base + '/project/index.json', timeout=10) as response:
                if json.load(response) != {'default': None, 'scenes': []}:
                    raise RuntimeError('Empty workspace catalogue is incorrect')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
    print('Installed schemas, source ownership and static viewer: PASS')


if __name__ == '__main__':
    check()
