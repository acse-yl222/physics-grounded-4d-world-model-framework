"""Check pull request titles and commit messages against the format in AGENTS.md.

--title TITLE        a pull request title
--hook FILE          a commit message file, from the commit-msg hook (`make hooks`)
--commits            JSON lines {"sha", "message", "parents"} on stdin, as CI sends them
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TYPES = ("feat", "fix", "perf", "refactor", "test", "docs", "ci", "build", "chore")
SCOPES = (
    "traffic",
    "uav",
    "flow",
    "geometry",
    "birds",
    "pipeline",
    "protocol",
    "cli",
    "viewer",
    "scenes",
)
SCOPE_OPTIONAL = ("ci", "docs", "build", "chore")
MAX_LENGTH = 72
SUBJECT = re.compile(r"(?P<type>\w+)(?:\((?P<scope>\w+)\))?!?: (?P<summary>\S.*)")
AUTOSQUASH = ("fixup! ", "squash! ", "amend! ")
SCISSORS = "# ------------------------ >8 ------------------------"


def subject_problems(subject):
    match = SUBJECT.fullmatch(subject)
    if not match:
        return ["expected '<type>(<scope>)!: <summary>', for example 'fix(traffic): ...'"]
    found = []
    kind, scope, summary = match["type"], match["scope"], match["summary"]
    if kind not in TYPES:
        found.append(f"unknown type '{kind}'; use one of {', '.join(TYPES)}")
    if scope is None and kind not in SCOPE_OPTIONAL:
        found.append(f"'{kind}' needs a scope: {', '.join(SCOPES)}")
    if scope is not None and scope not in SCOPES:
        found.append(f"unknown scope '{scope}'; use one of {', '.join(SCOPES)}")
    if re.match(r"[A-Z][a-z]", summary):
        found.append("start the summary in lower case unless it begins with a proper noun")
    if summary.endswith("."):
        found.append("drop the trailing full stop")
    if len(subject) > MAX_LENGTH:
        found.append(f"{len(subject)} characters; keep it within {MAX_LENGTH} characters")
    return found


def message_problems(message, allow_autosquash=False):
    lines = message.strip("\n").splitlines() or [""]
    subject = lines[0]
    if subject.startswith('Revert "'):
        return []
    if subject.startswith(AUTOSQUASH):
        if allow_autosquash:
            return []
        return ["squash fixup!/squash!/amend! commits into the commit they change before pushing"]
    found = subject_problems(subject)
    if len(lines) > 1 and lines[1].strip():
        found.append("leave the second line blank between the subject and the body")
    return found


def clean(message):
    """Drop git's comment lines and the verbose diff below the scissors line."""
    lines = []
    for line in message.splitlines():
        if line == SCISSORS:
            break
        if not line.startswith("#"):
            lines.append(line.rstrip())
    return "\n".join(lines).strip("\n")


def merging():
    result = subprocess.run(
        ["git", "rev-parse", "--git-path", "MERGE_HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and Path(result.stdout.strip()).exists()


def main(argv):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--title")
    source.add_argument("--hook", type=Path)
    source.add_argument("--commits", action="store_true")
    args = parser.parse_args(argv)
    if args.title is not None:
        reports = [("PR title", subject_problems(args.title))]
    elif args.hook is not None:
        if merging():
            return 0
        message = clean(args.hook.read_text())
        reports = [("commit message", message_problems(message, allow_autosquash=True))]
    else:
        commits = [json.loads(line) for line in sys.stdin if line.strip()]
        if not commits:
            print("no commits to check", file=sys.stderr)
            return 1
        reports = [
            (
                f"commit {c['sha'][:9]} {c['message'].splitlines()[0]!r}",
                message_problems(c["message"]),
            )
            for c in commits
            if c["parents"] < 2
        ]
    failed = False
    for label, found in reports:
        for problem in found:
            print(f"{label}: {problem}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
