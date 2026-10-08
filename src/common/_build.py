"""Include canonical schemas and static viewers without duplicating their sources."""
from pathlib import Path
import shutil
from setuptools.command.build_py import build_py


class BuildPy(build_py):
    def run(self):
        super().run()
        root = Path(__file__).resolve().parents[2]
        resources = Path(self.build_lib) / 'common/resources'
        for relative in ('schemas', 'examples', 'src/visualization'):
            shutil.copytree(
                root / relative, resources / relative, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('__pycache__', '*.py', '*.pyc'),
            )
        shutil.copy2(root / 'index.html', resources / 'index.html')
