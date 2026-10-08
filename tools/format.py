"""Format owned, version-controlled files without touching data or snapshots.

The shared boundary is .prettierignore plus the repository's Git ignore rules.
Untracked, non-ignored source files are included so a new file is checked before
its first commit. Explicit filenames from pre-commit use the same boundary.
"""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PRETTIER_SUFFIXES = {".js", ".mjs", ".cjs", ".html", ".css", ".json", ".yaml", ".yml", ".md"}


def git_files(*options, root=ROOT):
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--deduplicate", *options],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    return set(os.fsdecode(result.stdout).split("\0")) - {""}


def selected_files(paths=(), root=ROOT):
    candidates = git_files("--exclude-standard", root=root)
    excluded = git_files(
        "--ignored", "--exclude-standard", "--exclude-from=.prettierignore", root=root
    )
    candidates -= excluded
    if paths:
        requested = set()
        for name in paths:
            path = Path(name)
            if not path.is_absolute():
                path = root / path
            try:
                requested.add(path.absolute().relative_to(root).as_posix())
            except ValueError:
                raise ValueError(f"File is outside the repository: {name}") from None
        candidates &= requested
    return sorted(
        name for name in candidates if (root / name).is_file() and not (root / name).is_symlink()
    )


def formatter_groups(files):
    groups = {"ruff": [], "prettier": [], "taplo": [], "shfmt": []}
    for name in files:
        suffix = Path(name).suffix
        if suffix in {".py", ".pyi", ".ipynb"}:
            groups["ruff"].append(name)
        elif suffix in PRETTIER_SUFFIXES:
            groups["prettier"].append(name)
        elif suffix == ".toml":
            groups["taplo"].append(name)
        elif suffix in {".sh", ".command"}:
            groups["shfmt"].append(name)
    return groups


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Apply formatting")
    mode.add_argument("--check", action="store_true", help="Check formatting (the default)")
    parser.add_argument("files", nargs="*", help="Optional repository-relative filenames")
    args = parser.parse_args(argv)
    groups = formatter_groups(selected_files(args.files))
    executable_path = os.pathsep.join(
        (str(Path(sys.executable).parent), os.environ.get("PATH", ""))
    )
    shfmt = shutil.which("shfmt", path=executable_path) or "shfmt"
    commands = {
        "ruff": [sys.executable, "-m", "ruff", "format", *([] if args.write else ["--check"])],
        "prettier": [
            str(ROOT / "node_modules/.bin/prettier"),
            "--write" if args.write else "--check",
            "--ignore-path",
            ".prettierignore",
        ],
        "taplo": [
            str(ROOT / "node_modules/.bin/taplo"),
            "format",
            *([] if args.write else ["--check"]),
        ],
        "shfmt": [shfmt, "-i", "2", "-ci", "-w" if args.write else "-d"],
    }
    failed = False
    for tool, files in groups.items():
        if not files:
            continue
        print(f"{tool}: {len(files)} files", flush=True)
        for offset in range(0, len(files), 100):
            try:
                result = subprocess.run(
                    [*commands[tool], "--", *files[offset : offset + 100]], cwd=ROOT, check=False
                )
            except FileNotFoundError:
                print("Install tools/requirements-dev.txt and run npm ci first.", file=sys.stderr)
                return 1
            failed |= result.returncode != 0
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
