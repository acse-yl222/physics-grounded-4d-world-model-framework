"""Agent interpretation of cached references, without inventing camera metadata."""
from pathlib import Path
import hashlib
import json
from img2city import config


def audit(meta, bdir, model=config.VISION_MODEL):
    from img2city.city.quality import _ask, _write
    bdir = Path(bdir)
    images = [bdir / name for name in ('streetview.png', 'satellite.png')]
    if not all(p.is_file() for p in images):
        raise ValueError('street and satellite references are required')
    if (bdir / 'target_satellite.png').exists():
        images.append(bdir / 'target_satellite.png')
    pano = json.loads((bdir / 'pano.json').read_text())
    result, usage = _ask(
        'Audit reference evidence for Img2City before geometry generation. '
        'Image 1 is Google street imagery; image 2 is satellite context. '
        'When image 3 is supplied, its red outline identifies the EXACT target footprint. '
        'Identify which visible structures belong to the supplied OSM footprint, '
        'distinguish the target from adjacent buildings/platforms, and disclose ambiguity. '
        'Do not guess photographic camera parameters. The cached pano record is not '
        'proof of a matched camera. Give reference-supported structural guidance, not geometry code. '
        'Return JSON with identity="supported|uncertain|wrong", useful_evidence=[strings], '
        'limitations=[strings], refinement_guidance=[strings]. '
        'Do not demand trains, tracks or whole station facilities outside the target footprint '
        'as if they were missing parts of this one building.',
        {'target': meta, 'pano_record': pano,
         'camera_note': 'Legacy rendering uses heuristic aim and may move camera. '
                        'No verified match to the cached image is established.'},
        [str(p) for p in images], model)
    if result.get('identity') not in ('supported', 'uncertain', 'wrong'):
        raise ValueError('invalid reference identity verdict')
    for key in ('useful_evidence', 'limitations', 'refinement_guidance'):
        if not isinstance(result.get(key), list) or not all(isinstance(x, str) for x in result[key]):
            raise ValueError('invalid reference audit field: ' + key)
    result.update(model=model, camera_verified=False, usage=usage,
                  images={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in images})
    _write(bdir / 'reference_audit.json', result)
    return result


def context(bdir):
    """Only use an audit while its actual reference files remain unchanged."""
    bdir = Path(bdir)
    path = bdir / 'reference_audit.json'
    if not path.exists():
        return None
    result = json.loads(path.read_text())
    for name, expected in result['images'].items():
        if hashlib.sha256((bdir / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Reference audit is stale; audit new images first')
    return result
