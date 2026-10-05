"""The Blender-side parts kit as seen from the host (source text only: no bpy)
and the library tooling that audits / mines it."""
import ast
import json
import re
import textwrap


from img2city import kit
from img2city.library import audit, learn


def _top_funcs(path):
    return {n.name for n in ast.parse(open(path).read()).body
            if isinstance(n, ast.FunctionDef)}


# ---------------- kit source blob

def test_kit_src_compiles_with_vendor_prefix_and_core_first():
    src = kit.load_kit_src()
    compile(src, "kit_src", "exec")
    assert src.startswith("_VENDOR_DIR = ")
    assert str(kit.VENDOR_DIR) in src.splitlines()[0]
    core = kit.COMPONENTS_PY.read_text()
    learned = kit.PARTS_LEARNED_PY.read_text()
    assert src.index(core[:200]) < src.index(learned[:200]), "learned parts after core"
    assert set(kit.kit_sources()) == {str(kit.COMPONENTS_PY), str(kit.PARTS_LEARNED_PY)}


def test_kit_source_never_imports_the_host_package():
    for p in kit.kit_sources():
        for node in ast.walk(ast.parse(open(p).read())):
            if isinstance(node, ast.Import):
                assert not any(a.name.startswith("img2city") for a in node.names), p
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("img2city"), p


def test_learned_parts_do_not_shadow_core_parts():
    core, learned = _top_funcs(kit.COMPONENTS_PY), _top_funcs(kit.PARTS_LEARNED_PY)
    assert "build_building" in core
    assert not (core & learned), f"gate 0 violated: {sorted(core & learned)}"


def test_every_registered_learned_part_is_defined():
    reg = audit.registry_names(str(kit.PARTS_LEARNED_PY), "PARTS_LEARNED")
    defined = _top_funcs(kit.PARTS_LEARNED_PY)
    assert reg, "no PARTS_LEARNED registry found"
    assert reg <= defined, f"registered but undefined: {sorted(reg - defined)}"


def test_spec_dialect_lines_reference_registered_parts():
    entries = json.load(open(kit.SPEC_DIALECT_JSON))
    reg = audit.registry_names(str(kit.PARTS_LEARNED_PY), "PARTS_LEARNED")
    assert isinstance(entries, list) and entries
    for e in entries:
        assert {"region", "cluster", "line"} <= set(e)
        names = re.findall(r"(\w+)\s*:\s*\{", e["line"])
        assert names, e["line"][:60]
        assert set(names) <= reg, f"dialect names not registered: {set(names) - reg}"


# ---------------- library.audit on a synthetic file

def test_audit_parses_params_registry_and_helpers(tmp_path):
    p = tmp_path / "parts.py"
    p.write_text(textwrap.dedent('''
        def helper(x):
            return x
        def bay_window(p, i):
            """A bay window."""
            w = p.get("width", 1.5)
            n = p.get("count", 3)
            q = p.get("weird", [1, 2])
            return w, n, q
        PARTS_LEARNED = {"bay_window": bay_window}
        PARTS_LEARNED = {"other": helper}
    '''))
    reg = audit.registry_names(str(p), "PARTS_LEARNED")
    assert reg == {"bay_window", "other"}, "every re-assigned block is read"
    parts = audit.parse_parts(str(p), reg)
    assert set(parts) == {"helper", "bay_window"}
    bw = parts["bay_window"]
    assert bw["doc"] == "A bay window."
    assert dict(bw["params"]) == {"width": 1.5, "count": 3, "weird": [1, 2]}
    assert bw["registered"] and not parts["helper"]["registered"]
    assert bw["lines"][0] < bw["lines"][1]


def test_dialect_provenance_maps_part_to_region_and_cluster():
    prov = audit.dialect_provenance()
    assert prov
    for name, (region, cluster) in prov.items():
        assert isinstance(name, str) and region and cluster


# ---------------- library.learn vocabulary mining

def test_terms_keeps_salient_words_and_adjacent_pairs():
    t = learn._terms("Exposed CONCRETE frame, with a bay-window!")
    assert {"exposed", "concrete", "frame", "bay", "window"} <= t
    assert {"exposed concrete", "concrete frame", "bay window"} <= t
    assert "a" not in t and "with" not in t
    assert learn._terms("") == set() and learn._terms(None) == set()
