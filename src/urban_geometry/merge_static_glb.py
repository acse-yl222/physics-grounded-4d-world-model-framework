"""Losslessly package simple, untextured static GLBs in their shared coordinate frame."""
import argparse
import copy
import hashlib
import json
import shutil
import struct
from pathlib import Path


def read_header(path):
    with path.open('rb') as stream:
        magic, version, total = struct.unpack('<4sII', stream.read(12))
        assert magic == b'glTF' and version == 2 and total == path.stat().st_size
        length, kind = struct.unpack('<II', stream.read(8))
        assert kind == 0x4E4F534A
        document = json.loads(stream.read(length))
        binary_length, kind = struct.unpack('<II', stream.read(8))
        assert kind == 0x004E4942
        offset = stream.tell()
        assert offset + binary_length == total
    allowed = {'asset', 'scene', 'scenes', 'nodes', 'meshes', 'materials', 'accessors', 'bufferViews', 'buffers'}
    assert set(document) <= allowed
    assert len(document['buffers']) == len(document['scenes']) == 1
    assert 'uri' not in document['buffers'][0]
    assert all(set(node) <= {'name', 'mesh', 'extras'} for node in document['nodes'])
    assert all('sparse' not in accessor for accessor in document['accessors'])
    assert '"extensions"' not in json.dumps(document)
    return document, offset, binary_length


def merge(paths, output):
    if output.exists():
        raise FileExistsError(output)
    sources = [(path, *read_header(path)) for path in paths]
    result = {'asset': {'version': '2.0', 'generator': 'Lossless static GLB packaging'},
              'scene': 0, 'scenes': [{'nodes': []}], 'buffers': [{'byteLength': 0}]}
    arrays = ['nodes', 'meshes', 'materials', 'accessors', 'bufferViews']
    result.update({name: [] for name in arrays})
    binary_offset = 0
    for path, original, offset, length in sources:
        document = copy.deepcopy(original)
        shifts = {name: len(result[name]) for name in arrays}
        for view in document['bufferViews']:
            assert view['buffer'] == 0
            view['byteOffset'] = view.get('byteOffset', 0) + binary_offset
        for accessor in document['accessors']:
            accessor['bufferView'] += shifts['bufferViews']
        for mesh in document['meshes']:
            for primitive in mesh['primitives']:
                assert set(primitive) <= {'attributes', 'indices', 'material', 'mode'}
                primitive['attributes'] = {name: index + shifts['accessors'] for name, index in primitive['attributes'].items()}
                if 'indices' in primitive:
                    primitive['indices'] += shifts['accessors']
                if 'material' in primitive:
                    primitive['material'] += shifts['materials']
        for node in document['nodes']:
            if 'mesh' in node:
                node['mesh'] += shifts['meshes']
        result['scenes'][0]['nodes'].extend(index + shifts['nodes'] for index in document['scenes'][0]['nodes'])
        for name in arrays:
            result[name].extend(document[name])
        binary_offset += length
    result['buffers'][0]['byteLength'] = binary_offset
    encoded = json.dumps(result, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    total = 12 + 8 + len(encoded) + 8 + binary_offset
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as destination:
        destination.write(struct.pack('<4sII', b'glTF', 2, total))
        destination.write(struct.pack('<II', len(encoded), 0x4E4F534A))
        destination.write(encoded)
        destination.write(struct.pack('<II', binary_offset, 0x004E4942))
        for path, document, offset, length in sources:
            with path.open('rb') as source:
                source.seek(offset)
                shutil.copyfileobj(source, destination, 1024 * 1024)
    reread, offset, length = read_header(output)
    assert reread == result and length == binary_offset
    with output.open('rb') as stream:
        stream.seek(offset)
        for path, document, source_offset, source_length in sources:
            with path.open('rb') as source:
                source.seek(source_offset)
                remaining = source_length
                while remaining:
                    count = min(remaining, 1024 * 1024)
                    assert stream.read(count) == source.read(count)
                    remaining -= count
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'asset': str(output), 'bytes': total, 'sha256': digest,
            'source_assets': [str(path) for path in paths], 'binary_payloads_identical': True,
            'nodes': len(result['nodes']), 'compression': 'none', 'coordinates_changed': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('inputs', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = merge(args.inputs, args.output)
    args.output.with_suffix('.verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
