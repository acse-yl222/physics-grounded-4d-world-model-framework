"""Spec-document layer: validated-output checking (validate_desc) and the
polygon-path parameter surface (poly_params) -- the contracts between the
agent's JSON and the Blender builders."""
import json

import pytest

gen = pytest.importorskip("img2city.building.generate")
cg = pytest.importorskip("img2city.city.generate")

GOOD = {
    "footprint": [30.0, 12.0],
    "floors": 5,
    "floor_h": 3.2,
    "facade": "masonry",
    "plinth": False,
}


def test_validate_desc_accepts_minimal_spec():
    desc, errs = gen.validate_desc(json.dumps(GOOD))
    assert desc is not None
    assert errs == [] or not errs


def test_validate_desc_rejects_malformed_json():
    desc, errs = gen.validate_desc("this is not json at all")
    assert errs


def test_validate_desc_flags_bad_footprint():
    bad = dict(GOOD, footprint=[-5, 0])
    desc, errs = gen.validate_desc(json.dumps(bad))
    assert errs, "negative footprint must be rejected"


def test_poly_params_forwards_the_poly_surface():
    spec = {
        "footprint": [30, 12],
        "floors": 6,
        "floor_h": 3.0,
        "masses": [{"x": [0, 1], "y": [0, 1], "floors": 6,
                    "facade": "masonry", "wall": "stone"}],
        "terrace": {"roof_form": "mansard", "roof_tone": "light",
                    "dormers": True, "shopfront": True},
        "arch_windows": True,
        "arch_row": 2,
        "balustrade": True,
    }
    p = cg.poly_params(spec)
    assert p["floors"] == 6
    assert p["floor_h"] == 3.0
    assert p["wall"] == "stone"
    assert p["roof_form"] == "mansard"
    assert p["roof_tone"] == "light"
    assert p["dormers"] is True
    assert p["shopfront"] is True
    assert p["balustrade"] is True


def test_poly_params_defaults_are_safe():
    p = cg.poly_params({"footprint": [20, 10]})
    assert p["floors"] >= 1
    assert p["floor_h"] > 0
    assert isinstance(p["wall"], str)


def test_poly_learning_extensions_build_in_declared_frame(monkeypatch):
    import sys
    from types import SimpleNamespace
    frame={'cx':20,'cy':30,'rotation_rad':.5}
    extra={'type':'learned_window'}
    params=cg.poly_params({'extra_parts':[extra],'extra_parts_frame':frame})
    class Transform:
        def __init__(self,value):self.value=value
        def __matmul__(self,other):return Transform((self.value,other.value))
    matrix=SimpleNamespace(Translation=lambda v:Transform(v),Rotation=lambda *v:Transform(v))
    monkeypatch.setitem(sys.modules,'mathutils',SimpleNamespace(Matrix=matrix))
    obj=SimpleNamespace(matrix_world=Transform('original'))
    seen=[]
    def part(p,i):seen.append((p,i));return [obj]
    namespace={'ensure_materials':lambda:None,'polygon_terrace':lambda *a:None,
               'BUILDERS':{'learned_window':part}}
    exec(cg.POLY_BUILD % json.dumps(params),namespace)
    assert seen==[(extra,0)]
    assert obj.matrix_world.value==(((20,30,0),(.5,4,'Z')),'original')
    assert cg.poly_params({'extra_parts':[extra]})['framed_extra_parts'] is None
