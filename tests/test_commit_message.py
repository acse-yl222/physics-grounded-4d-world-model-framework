"""Pull request titles and commit messages follow the format documented in AGENTS.md."""

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/check_commit_message.py"
spec = importlib.util.spec_from_file_location("commit_message", SCRIPT)
commit_message = importlib.util.module_from_spec(spec)
spec.loader.exec_module(commit_message)

BODY = "\n\n- What changed and why.\n\nCo-Authored-By: Someone <someone@example.com>"


class SubjectTests(unittest.TestCase):
    def test_accepts_documented_forms(self):
        for subject in [
            "fix(traffic)!: anchor Jacobi predictions to the observed position",
            "feat(geometry): georeference Delhi Karol Bagh with OSM context buildings",
            "fix(viewer)!: show no traffic outside the recorded legacy SUMO sample",
            "ci: run the whole test suite in the CPU domain job",
            "docs: describe the PR title format",
            "chore(scenes): refresh the South Kensington inputs",
            "fix(uav): GLB stations outside the height map are rejected",
        ]:
            with self.subTest(subject=subject):
                self.assertEqual(commit_message.subject_problems(subject), [])

    def test_rejects_subjects_outside_the_format(self):
        for subject, problem in [
            ("Mask missing future traffic frames", "<type>(<scope>)"),
            ("E2E 1/4: run browser smoke tests", "<type>(<scope>)"),
            ("fix: mask missing future frames", "needs a scope"),
            ("fix(trafic): mask missing future frames", "unknown scope"),
            ("bugfix(traffic): mask missing future frames", "unknown type"),
            ("fix(traffic): Mask missing future frames", "lower case"),
            ("fix(traffic): mask missing future frames.", "full stop"),
            ("fix(traffic):  mask missing future frames", "<type>(<scope>)"),
            ("fix(traffic): " + "x" * 59, "72 characters"),
        ]:
            with self.subTest(subject=subject):
                found = commit_message.subject_problems(subject)
                self.assertTrue(any(problem in p for p in found), found)


class MessageTests(unittest.TestCase):
    def test_accepts_subject_body_and_trailers(self):
        self.assertEqual(
            commit_message.message_problems("fix(uav): reject bad stations" + BODY), []
        )
        self.assertEqual(commit_message.message_problems("ci: pin the checkout action"), [])

    def test_requires_a_blank_second_line(self):
        found = commit_message.message_problems("fix(uav): reject bad stations\nbody")
        self.assertTrue(any("second line" in p for p in found), found)

    def test_checks_the_subject(self):
        found = commit_message.message_problems("Reject bad stations" + BODY)
        self.assertTrue(any("<type>(<scope>)" in p for p in found), found)

    def test_git_revert_subjects_are_accepted(self):
        message = 'Revert "fix(uav): reject bad stations"\n\nThis reverts commit 0123abc.'
        self.assertEqual(commit_message.message_problems(message), [])

    def test_autosquash_commits_are_local_only(self):
        message = "fixup! fix(uav): reject bad stations"
        self.assertTrue(commit_message.message_problems(message))
        self.assertEqual(commit_message.message_problems(message, allow_autosquash=True), [])

    def test_clean_drops_comments_and_the_verbose_diff(self):
        raw = (
            "\nfix(uav): reject bad stations\n\nBody.\n# Please enter the commit message\n"
            "# ------------------------ >8 ------------------------\ndiff --git a/x b/x\n"
        )
        self.assertEqual(commit_message.clean(raw), "fix(uav): reject bad stations\n\nBody.")


class CommandLineTests(unittest.TestCase):
    def run_main(self, argv, stdin=""):
        with mock.patch("sys.stdin", io.StringIO(stdin)), mock.patch("sys.stderr", io.StringIO()):
            return commit_message.main(argv)

    def test_title(self):
        self.assertEqual(self.run_main(["--title", "ci: check pull request titles"]), 0)
        self.assertEqual(self.run_main(["--title", "Check pull request titles"]), 1)

    def test_commits_skip_merges_and_report_bad_messages(self):
        def line(sha, message, parents=1):
            return json.dumps({"sha": sha, "message": message, "parents": parents}) + "\n"

        good = line("a" * 40, "fix(uav): reject bad stations" + BODY)
        merge = line("b" * 40, "Merge branch 'main' into fix", parents=2)
        self.assertEqual(self.run_main(["--commits"], good + merge), 0)
        self.assertEqual(self.run_main(["--commits"], good + line("c" * 40, "Fix stations")), 1)
        self.assertEqual(self.run_main(["--commits"], ""), 1)

    def test_hook_checks_the_message_file_and_skips_merges(self):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

            def git(*args):
                subprocess.run(
                    ["git", *args], cwd=directory, env=env, check=True, capture_output=True
                )

            def hook(message):
                path = Path(directory, "MESSAGE")
                path.write_text(message)
                command = [sys.executable, str(SCRIPT), "--hook", str(path)]
                return subprocess.run(
                    command, cwd=directory, env=env, capture_output=True, check=False
                ).returncode

            git("init", "-q")
            git(
                "-c",
                "user.name=t",
                "-c",
                "user.email=t@example.com",
                "commit",
                "-q",
                "--allow-empty",
                "-m",
                "x",
            )
            self.assertEqual(hook("fix(uav): reject bad stations\n# comment\n"), 0)
            self.assertEqual(hook("fixup! fix(uav): reject bad stations\n"), 0)
            self.assertEqual(hook("Fix stations\n"), 1)
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=directory,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            Path(directory, ".git/MERGE_HEAD").write_text(head.stdout)
            self.assertEqual(hook("Merge branch 'main' into fix\n"), 0)


class DocumentationTests(unittest.TestCase):
    def test_agents_md_documents_every_type_scope_and_the_hook(self):
        agents = (ROOT / "AGENTS.md").read_text()
        for name in [*commit_message.TYPES, *commit_message.SCOPES, "make hooks"]:
            with self.subTest(name=name):
                self.assertIn(f"`{name}`", agents)

    def test_hook_is_executable_and_enabled_by_make(self):
        self.assertTrue(os.access(ROOT / "tools/git-hooks/commit-msg", os.X_OK))
        self.assertIn("core.hooksPath tools/git-hooks", (ROOT / "Makefile").read_text())


if __name__ == "__main__":
    unittest.main()
