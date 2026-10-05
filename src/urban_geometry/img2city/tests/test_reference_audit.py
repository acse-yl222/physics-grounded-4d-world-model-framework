import hashlib
import json
from unittest.mock import Mock
import pytest
from img2city.imagery import reference_audit as a
from img2city.city import quality


def refs(tmp_path):
    for name in ('streetview.png', 'satellite.png'):
        (tmp_path/name).write_bytes(b'test image')
    (tmp_path/'pano.json').write_text('[51, -0.17]')


def test_audit_never_invents_verified_camera(tmp_path, monkeypatch):
    refs(tmp_path)
    reply={'identity':'supported','useful_evidence':['open canopy'], 'limitations':['unknown viewpoint'],
           'refinement_guidance':['preserve open structure'], 'camera_verified':True}
    monkeypatch.setattr(quality,'_ask',Mock(return_value=(reply,{})))
    result=a.audit({'id':1},tmp_path,'test')
    assert result['camera_verified'] is False
    assert a.context(tmp_path)==result


def test_changed_reference_invalidates_audit(tmp_path):
    refs(tmp_path)
    (tmp_path/'reference_audit.json').write_text(json.dumps({'images':{'streetview.png':hashlib.sha256(b'test image').hexdigest()}}))
    (tmp_path/'streetview.png').write_bytes(b'different photo')
    with pytest.raises(ValueError,match='stale'):
        a.context(tmp_path)


def test_malformed_audit_rejected(tmp_path, monkeypatch):
    refs(tmp_path)
    monkeypatch.setattr(quality,'_ask',Mock(return_value=({'identity':'yes'},{})))
    with pytest.raises(ValueError,match='identity'):
        a.audit({'id':1},tmp_path,'test')
    assert not (tmp_path/'reference_audit.json').exists()


def test_recorded_camera_preserves_heading_pitch_and_fov(tmp_path):
    from img2city.imagery.camera import recorded_pose
    refs(tmp_path)
    data={'lat':51,'lng':0,'heading':90,'pitch':0,'fov':90,
          'image_sha256':hashlib.sha256(b'test image').hexdigest()}
    (tmp_path/'image_camera.json').write_text(json.dumps(data))
    p=recorded_pose(tmp_path,{'lat0':51,'lon0':0},0,(0,0),False)
    assert p['location']==[0,0,2.5]
    assert p['target']==pytest.approx([10,0,2.5])
    assert p['lens_mm']==pytest.approx(18)
    assert p['height_assumed']
    (tmp_path/'streetview.png').write_bytes(b'changed')
    with pytest.raises(ValueError,match='does not match'):
        recorded_pose(tmp_path,{'lat0':51,'lon0':0},0,(0,0),False)


def test_static_map_pose_matches_center_extent_and_north(tmp_path):
    import math
    from img2city.imagery.camera import recorded_top
    refs(tmp_path)
    (tmp_path/'satellite_camera.json').write_text(json.dumps({'center':[51,0],'zoom':19,'logical_size':[640,640],
        'image_sha256':hashlib.sha256(b'test image').hexdigest()}))
    p=recorded_top(tmp_path,{'lat0':51,'lon0':0},math.pi/2,(0,0),False)
    assert p['center']==[0,0]
    assert p['rotation_z']==-math.pi/2
    assert p['span']==pytest.approx(156543.03392*math.cos(math.radians(51))/2**19*640)
