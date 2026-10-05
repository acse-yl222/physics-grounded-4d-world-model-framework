"""Static-artefact integrity: the bilingual UI dictionary and the learned-parts
registry (every registered part must exist; no shadowing of core names)."""
import ast
import os
import re


from img2city import kit
from img2city.config import PACKAGE_DIR

UI_DIR = os.path.join(PACKAGE_DIR, "webapp", "ui")


def test_i18n_dictionary_entries_are_nonempty_english():
    src = open(os.path.join(UI_DIR, "js", "i18n.js")).read()
    entries = re.findall(r"'([\w.]+)':\s*'((?:[^'\\]|\\.)*)'", src)
    assert len(entries) > 60, "dictionary should be substantial"
    for key, text in entries:
        assert text.strip(), key
        assert not re.search(r"[\u4e00-\u9fff]", text), f"Chinese in {key}"


def _top_level_functions(path):
    tree = ast.parse(open(path).read())
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}


def test_registered_learned_parts_are_defined():
    lp = str(kit.PARTS_LEARNED_PY)
    src = open(lp).read()
    registered = set()
    for m in re.finditer(r"PARTS_LEARNED\s*=\s*\{(.*?)\}", src, re.S):
        registered |= set(re.findall(r'"(\w+)"\s*:', m.group(1)))
    defined = _top_level_functions(lp)
    missing = registered - defined
    assert not missing, f"registered but undefined: {missing}"


def test_learned_parts_do_not_shadow_core_kit():
    # gate-0's isolation property: concatenation order would let a learned def
    # silently shadow a core part of the same name
    core = _top_level_functions(str(kit.COMPONENTS_PY))
    learned = _top_level_functions(str(kit.PARTS_LEARNED_PY))
    clashes = core & learned
    assert not clashes, f"learned parts shadow core kit names: {clashes}"
