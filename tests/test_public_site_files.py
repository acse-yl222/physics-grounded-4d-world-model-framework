"""The public site build must copy every legacy 3D module that a copied module imports."""

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWER_3D = ROOT / "src/visualization/legacy/viewer/3d"
# Already on the pages branch and not overlaid by the build; edits to them are not published.
PUBLISHED_ONLY = {"proxy.js", "tile.js", "expansion.js", "transport.js", "traffic.js"}


def copied_3d_modules():
    """Names in tools/build_public_site.py that are copied into viewer/3d."""
    tree = ast.parse((ROOT / "tools/build_public_site.py").read_text())
    names = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.For)
            and isinstance(node.iter, (ast.Tuple, ast.List))
            and "src/visualization/legacy/viewer/3d" in ast.unparse(node.body[0])
        ):
            names |= {e.value for e in node.iter.elts if isinstance(e, ast.Constant)}
    return names


class PublicSiteFilesTests(unittest.TestCase):
    def test_local_imports_of_copied_modules_are_copied(self):
        copied = copied_3d_modules()
        self.assertIn("replay.js", copied)
        for name in sorted(n for n in copied if n.endswith((".js", ".mjs"))):
            source = (VIEWER_3D / name).read_text()
            for dep in re.findall(r"""from\s+['"]\./([^'"]+)['"]""", source):
                with self.subTest(module=name, imports=dep):
                    self.assertTrue((VIEWER_3D / dep).is_file())
                    self.assertIn(dep, copied | PUBLISHED_ONLY)


if __name__ == "__main__":
    unittest.main()
