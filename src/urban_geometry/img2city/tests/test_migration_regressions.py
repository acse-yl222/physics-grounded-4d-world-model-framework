"""Regressions found by comparing the extracted package to the thesis repo.

Model calls and Blender are mocked here; real renderer smoke tests are separate.
"""
import ast
from io import BytesIO
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image

from img2city import kit
from img2city.building import generate, typology
from img2city.webapp import photo


def test_learning_gate_uses_current_interpreter_and_preserves_paths(monkeypatch):
    import subprocess
    import sys
    from img2city.library import grow
    run = Mock(side_effect=subprocess.CalledProcessError(1, "stage"))
    monkeypatch.setattr(grow.subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        grow._stage("city.generate", "--out", "/tmp/area with spaces")
    assert run.call_args.args[0] == [sys.executable, "-m", "img2city.city.generate",
                                     "--out", "/tmp/area with spaces"]
    assert run.call_args.kwargs["check"] is True


def _kit_function(path, name, **namespace):
    tree = ast.parse(path.read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


@pytest.mark.parametrize("span,expected", [(1.0, 26.5), (25.6, 26.5), ([0, 1], 26.5), ([0.1, 0.9], 21.38)])
def test_facade_band_legacy_units_stay_on_facade(span, expected):
    boxes = []
    def box(name, center, size, material):
        boxes.append((center, size))
        return name
    build = _kit_function(kit.PARTS_LEARNED_PY, "facade_band", box=box)
    build({"length": 25.6, "width": 12, "span": span,
           "sides": ["-y"], "railing": False}, 0)
    assert boxes[0][0][1] < 0  # front remains the -y face
    assert boxes[0][1][0] == pytest.approx(expected)


@pytest.mark.parametrize("mass_override", [False, True])
def test_tower_height_is_not_truncated_at_40_floors(mass_override):
    build = _kit_function(kit.COMPONENTS_PY, "_build_building",
                          assemble=lambda spec: spec["parts"], BUILDERS={})
    desc = {"footprint": [30, 20], "floor_h": 3.5, "floors": 63}
    if mass_override:
        desc["floors"] = 6
        desc["masses"] = [{"x": [0, 1], "y": [0, 1], "floors": 63}]
    block = next(p for p in build(desc) if p["type"] == "block")
    assert block["size"][2] == 220.5
    assert block["floors"] == 63
    from img2city.building.facade_project import _front_masses
    masonry = dict(desc, facade="masonry")
    if mass_override:
        masonry["masses"] = [dict(m, facade="masonry") for m in desc["masses"]]
    assert _front_masses(masonry)[0]["h"] == block["size"][2]


def test_typology_accepts_photo_without_survey_facts(tmp_path, monkeypatch):
    from img2city.agent import llm
    from img2city.imagery import rescue_imagery
    (tmp_path / "streetview.png").write_bytes(b"mocked image")
    monkeypatch.setattr(rescue_imagery, "unusable_image", lambda p: False)
    call = Mock(return_value=('{"cards": [], "none_fits": true}', {}, 0))
    monkeypatch.setattr(llm, "vision_call", call)
    typology.pick({"name": None}, str(tmp_path))
    assert "no footprint, height or OSM type" in call.call_args.args[1]
    assert (tmp_path / "typology.json").exists()


def test_photo_agent_repair_keeps_card_dialect(monkeypatch):
    code = json.dumps({"footprint": [20, 12]})
    call = Mock(side_effect=[("not json", {"prompt_tokens": 2, "completion_tokens": 3}),
                             (code, {"prompt_tokens": 5, "completion_tokens": 7})])
    monkeypatch.setattr(generate, "gen_spec", call)
    monkeypatch.setattr(typology, "card_tags", lambda cards: {"paris"})
    desc, meta = photo.spec_from_photo("photo.png", {"cards": ["haussmann"]})
    assert desc["footprint"] == [20, 12]
    assert meta["tokens"] == 17
    assert all(c.kwargs["tags"] == {"paris"} for c in call.call_args_list)
    assert call.call_args.args[3]  # validation error reached the repair call


def test_unusable_photo_never_reaches_builder(tmp_path, monkeypatch):
    monkeypatch.setattr(photo, "UPLOADS", tmp_path)
    monkeypatch.setattr(photo, "classify", lambda p: {"cards": []})
    monkeypatch.setattr(generate, "gen_spec", Mock(return_value=(
        '{"unusable":"blurred"}', {"prompt_tokens": 1, "completion_tokens": 1})))
    build = Mock()
    monkeypatch.setattr(photo, "_build_glb", build)
    buf = BytesIO(); Image.new("RGB", (8, 8)).save(buf, "JPEG")
    with pytest.raises(RuntimeError, match="blurred"):
        photo.create(buf.getvalue(), ".jpg")
    build.assert_not_called()


def test_upload_normalizes_image_and_builds_agent_spec(tmp_path, monkeypatch):
    monkeypatch.setattr(photo, "UPLOADS", tmp_path)
    monkeypatch.setattr(photo, "classify", lambda p: {"cards": []})
    desc = {"footprint": [20, 12]}
    write_spec = Mock(return_value=(desc, {"tags": []}))
    monkeypatch.setattr(photo, "spec_from_photo", write_spec)
    build = Mock()
    monkeypatch.setattr(photo, "_build_glb", build)
    buf = BytesIO(); Image.new("RGBA", (8, 8)).save(buf, "PNG")
    pid = photo.create(buf.getvalue())
    img = tmp_path / pid / "streetview.png"
    assert Image.open(img).mode == "RGB"
    assert write_spec.call_args.args[0] == img
    assert build.call_args.args[0] is desc
    assert photo.info(pid)["desc"] == desc


@pytest.mark.parametrize("cards,tags", [(["test"], "paris"), ([], "")])
def test_photo_refinement_propagates_tags(tmp_path, monkeypatch, cards, tags):
    monkeypatch.setattr(photo, "UPLOADS", tmp_path)
    p = tmp_path / "upload"; p.mkdir()
    (p / "streetview.png").write_bytes(b"mocked image")
    (p / "typology.json").write_text(json.dumps({"cards": cards}))
    monkeypatch.setattr(typology, "card_tags", lambda c: {"paris"} if c else set())
    monkeypatch.setattr(photo.jobs, "launch_blender", lambda: True)
    job = SimpleNamespace(_run=Mock())
    monkeypatch.setattr(photo.jobs, "create", lambda *a, **kw: job)
    photo.start_refine("upload")
    cmd = job._run.call_args.args[0]
    assert cmd[1:3] == ["-m", "img2city.building.generate"]
    assert cmd[cmd.index("--tags") + 1] == tags


@pytest.mark.parametrize("btype,has_spec,expect_shed", [
    ("train_station", True, False), ("train_station", False, True),
    ("commercial", False, False), ("roof", True, False)])
def test_scene_assembly_keeps_agent_geometry(tmp_path, monkeypatch, btype, has_spec, expect_shed):
    from img2city.city import generate as city
    from img2city.scene import assets
    from img2city.building import facade_colors, texture_assets
    # Isolate the orchestration: no scene cache fetching or socket execution.
    monkeypatch.setattr(assets, "load_or_build", Mock(side_effect=RuntimeError("offline")))
    monkeypatch.setattr(facade_colors, "colors_for", lambda *a: None)
    monkeypatch.setattr(texture_assets, "run_all", lambda *a: {})
    monkeypatch.setattr(city, "_send", lambda code, **kw: code)
    monkeypatch.setattr(city, "load_components_src", lambda: "")
    monkeypatch.setattr(city, "BUILD_SCENE", "LOD1=%s\n")
    monkeypatch.setattr(city, "STATION_BUILD", "SHED=%s\n")
    monkeypatch.setattr(city, "CANOPY_BUILD", "CANOPY=%s\n")
    monkeypatch.setattr(city, "AGENT_CHUNK", "AGENT=%s\n")
    meta = {"id": 1, "btype": btype, "func": "station", "height": 8,
            "area_m2": 200, "pts": [[0, 0], [20, 0], [20, 10], [0, 10]]}
    entry = {"id": 1, "desc": {"footprint": [20, 10]}, "rot": 0, "cx": 10, "cy": 5}
    code = city.assemble([meta], {1: entry} if has_spec else {}, str(tmp_path))
    assert ("SHED=" in code) == expect_shed
    assert ("AGENT=" in code) == has_spec
    if has_spec:
        assert "CANOPY=" not in code


def test_open_structure_does_not_invent_default_solid_mass():
    build = _kit_function(kit.COMPONENTS_PY, "_build_building",
                         assemble=lambda spec: spec["parts"], BUILDERS={"platform_canopy": object()})
    part = {"type": "platform_canopy", "length": 30, "width": 12}
    pieces = build({"footprint": [30, 12], "masses": [], "extra_parts": [part], "plinth": False})
    assert any(p["type"] == "platform_canopy" for p in pieces)
    assert not any(p["type"] == "block" for p in pieces)
    assert any(p["type"] == "block" for p in build({"footprint": [30, 12]}))


def test_empty_mass_validation_requires_explicit_structure():
    from img2city.building.generate import validate_desc
    spec = {"footprint": [30, 12], "masses": [], "extra_parts": [{"type": "platform_canopy"}]}
    assert not validate_desc(json.dumps(spec))[1]
    spec["extra_parts"] = []
    assert validate_desc(json.dumps(spec))[1]
