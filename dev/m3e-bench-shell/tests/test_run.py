"""run.sh and its guards.

Fast tests use a stub nested.sh (a fake extensions repository, M3E_EXTENSIONS_REPO): no Shell is started. Slow tests
(real nested Shells, ~30 s each) only with M3E_BENCH_SHELL_SLOW=1 (`run.sh --self-test`).
"""
import os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH_SHELL = HERE.parent
REPO = BENCH_SHELL.parent.parent
RUN = BENCH_SHELL / "run.sh"
UUID = "m3e-bench-style@maximeallanic.github.io"
EXTENSION = BENCH_SHELL / UUID
sys.path.insert(0, str(BENCH_SHELL))
import report_shell  # noqa: E402

SLOW = os.environ.get("M3E_BENCH_SHELL_SLOW") == "1"
BASE_THEME = Path(os.environ.get("M3E_BASE_THEME") or Path.home() / ".themes" / "Material-Gnome")

# Stub of nested.sh: records its arguments (one per line, "--" between invocations) and fakes the nested Shell's files.
STUB = r"""#!/usr/bin/env bash
out=''; args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do [[ "${args[i]}" == --out ]] && out="${args[i+1]}"; done
{ printf '%s\n' "$@"; echo --; } >> "$STUB_LOG"
mkdir -p "$out"
printf '%s\n' "${STUB_SHELL_LOG:-}" > "$out/shell.log"
exit "${STUB_EXIT:-0}"
"""


class TestRunStatic(unittest.TestCase):
    def setUp(self):
        self.text = RUN.read_text(encoding="utf-8")

    def test_no_hardcoded_seed(self):
        # The seed is fallback_color of theme/matugen/palette.json (render_theme.py): never a literal in run.sh.
        self.assertIsNone(re.search(r"#[0-9a-fA-F]{6}\b", self.text))

    def test_only_the_nested_launcher_starts_a_shell(self):
        code = [l for l in self.text.splitlines() if not l.lstrip().startswith("#")]
        self.assertFalse([l for l in code if re.search(r"gnome-shell\s+--|mutter|dbus-run-session", l)])
        self.assertTrue(any('"$NESTED_SH"' in l for l in code))
        self.assertIn("nested-launcher.sh", self.text)

    def test_no_private_state(self):
        self.assertNotIn("~/.cache", self.text)
        self.assertNotIn("/home/", self.text)
        self.assertNotIn(Path.home().name, self.text)
        self.assertIsNone(re.search(r"--initial|lance\.sh", self.text))

    def test_css_error_pattern(self):
        pattern = re.search(r'^CSS_ERROR_PATTERN="(.*)"$', self.text, re.M).group(1)
        lines = [
            "parsing error: 7:27:could not recognize next production",
            "(gnome-shell:529899): St-WARNING **: 13:45:04.267: Error parsing stylesheet "
            "'file:///tmp/x/sheets/candidate-dark.css'; errcode:15",
            "(gnome-shell:547597): St-WARNING **: 13:49:13.481: Ignoring length property that isn't a number "
            "at line 4635, col 10",
        ]
        for line in lines:
            self.assertTrue(re.search(pattern, line), line)
        self.assertFalse(re.search(pattern, "libmutter-Message: 13:44:16.916: Using Wayland display name 'm3e-bench-1'"))

    def test_locale_is_a_parameter(self):
        self.assertIn("--locale", self.text)
        self.assertIn('"$LOCALE"', self.text)
        launcher = (REPO / "dev" / "m3e-bench" / "nested-launcher.sh").read_text(encoding="utf-8")
        self.assertIn("M3E_BENCH_LOCALE:-C.UTF-8", launcher)

    def test_report_requires_both_modes(self):
        with tempfile.TemporaryDirectory() as d:
            for present in ("dark", "light"):
                for m in ("dark", "light"):
                    shutil.rmtree(Path(d) / m, ignore_errors=True)
                (Path(d) / present).mkdir()
                (Path(d) / present / "measurements.json").write_text("[]", encoding="utf-8")
                r = subprocess.run([sys.executable, str(BENCH_SHELL / "report_shell.py"), d],
                                   capture_output=True, text=True)
                self.assertNotEqual(r.returncode, 0, present)
                self.assertIn("light" if present == "dark" else "dark", r.stderr)
            for m in ("dark", "light"):
                (Path(d) / m).mkdir(exist_ok=True)
                (Path(d) / m / "measurements.json").write_text("[]", encoding="utf-8")
            self.assertEqual(report_shell.main([d]), 0)


class TestRunArguments(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(["bash", str(RUN), *args], capture_output=True, text=True, timeout=60)

    def test_unknown_option(self):
        r = self._run("--nope")
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown option", r.stderr)

    def test_initial_mode_is_gone(self):
        self.assertEqual(self._run("--initial").returncode, 2)

    def test_batch_expects_a_number(self):
        r = self._run("--batch", "x")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--batch expects a number", r.stderr)

    def test_candidate_must_exist(self):
        r = self._run("--candidate", "/nonexistent/candidate.css")
        self.assertEqual(r.returncode, 2)
        self.assertIn("candidate sheet not found", r.stderr)


@unittest.skipUnless(BASE_THEME.is_dir() and shutil.which("matugen") and EXTENSION.is_dir(),
                     "needs the base theme, matugen and the bench extension")
class TestRunWithStubLauncher(unittest.TestCase):
    """Whole run.sh with a stub nested.sh: palettes, extension copy, static check, launcher options, report."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d)
        fake = self.d / "extensions-repo" / "tests" / "bench"
        shared = fake / "bench-extension" / "m3e-bench@maximeallanic.github.io"
        shared.mkdir(parents=True)
        for name in ("logind-guard.js", "tools.js"):
            (shared / name).write_text(f"// stub {name}\n", encoding="utf-8")
        (fake / "nested.sh").write_text(STUB, encoding="utf-8")
        self.log = self.d / "stub.log"
        self.out = self.d / "out"
        self.env = {**os.environ, "M3E_EXTENSIONS_REPO": str(self.d / "extensions-repo"), "STUB_LOG": str(self.log),
                    "M3E_BASE_THEME": str(BASE_THEME)}
        self.env.pop("M3E_BENCH_LOCALE", None)

    def _run(self, *args, **env):
        return subprocess.run(["bash", str(RUN), "--out", str(self.out), *args], capture_output=True, text=True,
                              timeout=300, env={**self.env, **env})

    def _invocations(self):
        return [inv.split("\n") for inv in self.log.read_text(encoding="utf-8").split("--\n") if inv.strip()]

    def test_two_nested_shells_user_and_gdm(self):
        r = self._run("--surfaces", "bar,menu,login")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        user, gdm = self._invocations()
        self.assertEqual(user[user.index("--mode") + 1], "user")
        self.assertEqual(user[user.index("--scenarios") + 1], "bar:dark,bar:light,menu:dark,menu:light")
        self.assertEqual(gdm[gdm.index("--mode") + 1], "gdm")
        self.assertEqual(gdm[gdm.index("--scenarios") + 1], "login:dark,login:light")
        self.assertEqual(user[user.index("--out") + 1], str(self.out / "nested"))
        self.assertEqual(gdm[gdm.index("--out") + 1], str(self.out / "nested-gdm"))
        self.assertIn(f"M3E_BENCH_STYLE_OUT={self.out}", user)
        self.assertEqual(user[user.index("--extension") + 1], str(self.out / "extension" / UUID))
        self.assertTrue((self.out / "report.html").exists())

    def test_default_locale_and_override(self):
        self._run("--surfaces", "bar")
        inv = self._invocations()[0]
        self.assertEqual(inv[inv.index("--locale") + 1], "C.UTF-8")
        self.log.unlink()
        self.out = self.d / "out2"
        self._run("--surfaces", "bar", M3E_BENCH_LOCALE="ja_JP.UTF-8")
        inv = self._invocations()[0]
        self.assertEqual(inv[inv.index("--locale") + 1], "ja_JP.UTF-8")
        self.log.unlink()
        self.out = self.d / "out3"
        self._run("--surfaces", "bar", "--locale", "ar_EG.UTF-8")
        inv = self._invocations()[0]
        self.assertEqual(inv[inv.index("--locale") + 1], "ar_EG.UTF-8")

    def test_extension_copy_and_sheets(self):
        self._run("--surfaces", "bar")
        ext = self.out / "extension" / UUID
        for name in ("logind-guard.js", "tools.js", "metadata.json", "extension.js", "surfaces/index.js"):
            self.assertTrue((ext / name).exists(), name)
        for mode in ("dark", "light"):
            self.assertEqual((ext / "sheets" / f"candidate-{mode}.css").read_bytes(),
                             (self.out / mode / "gnome-shell.css").read_bytes())
            self.assertEqual((ext / "sheets" / f"stock-{mode}.css").read_bytes(),
                             (REPO / "dev" / "reference" / "shell-stock" / f"gnome-shell-{mode}.css").read_bytes())
            self.assertGreater((self.out / mode / "colors.css").stat().st_size, 0)

    def test_candidate_sheet_imposed(self):
        sheet = self.d / "mine.css"
        sheet.write_text("#panel { height: 36px; }\n", encoding="utf-8")
        r = self._run("--surfaces", "bar", "--candidate", str(sheet))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for mode in ("dark", "light"):
            self.assertEqual((self.out / "extension" / UUID / "sheets" / f"candidate-{mode}.css").read_text(),
                             sheet.read_text())

    def test_broken_sheet_fails_static_check(self):
        sheet = self.d / "broken.css"
        sheet.write_text(".m3e-test { colour: red; }\n.m3e-test { width: 12qq; }\n", encoding="utf-8")
        r = self._run("--surfaces", "bar", "--candidate", str(sheet))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("property unknown to St: colour", r.stderr)
        self.assertIn("unit unknown to St: width: 12qq", r.stderr)

    def test_css_error_in_shell_log_fails(self):
        r = self._run("--surfaces", "bar",
                      STUB_SHELL_LOG="(gnome-shell:1): St-WARNING **: Error parsing stylesheet 'file:///x'; errcode:15")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("CSS parse errors in shell.log", r.stderr)
        self.assertIn("Error parsing stylesheet", (self.out / "css-errors-shell.txt").read_text())

    def test_guard_exit_codes_reported(self):
        r = self._run("--surfaces", "bar", STUB_EXIT="3")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("dconf guard triggered", r.stderr)
        self.out = self.d / "out4"
        r = self._run("--surfaces", "bar", STUB_EXIT="4")
        self.assertIn("XDG_RUNTIME_DIR guard triggered", r.stderr)

    def test_fake_remote_option_forwarded(self):
        self._run("--surfaces", "search", "--fake-remote")
        self.assertIn("M3E_BENCH_STYLE_FAKE_REMOTE=1", self._invocations()[0])


class TestNestedLauncherContract(unittest.TestCase):
    """What this bench relies on in nested.sh (owned by the extensions repository; its own tests are there)."""

    def setUp(self):
        launcher = REPO / "dev" / "m3e-bench" / "nested-launcher.sh"
        repo = os.environ.get("M3E_EXTENSIONS_REPO") or str(REPO.parent / "m3e-gnome-extensions")
        self.nested = Path(repo) / "tests" / "bench" / "nested.sh"
        if not self.nested.exists():
            self.skipTest(f"{self.nested} not found")
        self.assertTrue(launcher.exists())

    def test_external_search_providers_disabled(self):
        # The `search` surface must never reach a real D-Bus search provider: nested.sh's private dconf disables them.
        self.assertIn("[org/gnome/desktop/search-providers]\ndisable-external=true",
                      self.nested.read_text(encoding="utf-8"))

    def test_only_bench_env_forwarded(self):
        text = self.nested.read_text(encoding="utf-8")
        self.assertIn("M3E_BENCH_", text)
        self.assertIn("--env: only M3E_BENCH_*=... keys are accepted", text)

    def test_locale_option(self):
        self.assertIn("--locale", self.nested.read_text(encoding="utf-8"))


class TestLogindFromTheStart(unittest.TestCase):
    """The nested Shell cuts its link to the REAL logind session as soon as enable() runs, not only before a lock: a real
    Lock/Unlock would otherwise (un)lock it and write LockedHint on the real session. The guard itself is the shared
    logind-guard.js of the extensions repository's bench (copied by run.sh); static checks only, the behaviour is
    recorded in shell.log by the real run."""

    def test_enable_starts_the_guard_first(self):
        js = (EXTENSION / "extension.js").read_text(encoding="utf-8")
        body = js[js.index("    enable() {"):js.index("    disable() {")]
        code = [l.strip() for l in body.splitlines()[1:] if l.strip() and not l.strip().startswith("//")]
        self.assertTrue(code[0].startswith("startLogindGuard()"), code[0])
        self.assertIn("from './logind-guard.js'", js)

    def test_disable_stops_the_guard(self):
        js = (EXTENSION / "extension.js").read_text(encoding="utf-8")
        self.assertIn("stopLogindGuard();", js[js.index("    disable() {"):])

    def test_no_second_copy_of_the_guard(self):
        # logind-guard.js is copied from the extensions repository at run time, never duplicated in this bench.
        self.assertFalse((EXTENSION / "logind-guard.js").exists())
        self.assertFalse((EXTENSION / "tools.js").exists())
        self.assertIn("logind-guard.js tools.js", RUN.read_text(encoding="utf-8"))


@unittest.skipUnless(SLOW, "slow: M3E_BENCH_SHELL_SLOW=1 (run.sh --self-test)")
class TestRunSlow(unittest.TestCase):
    def _run(self, sheet, *extra):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "broken.css").write_text(sheet, encoding="utf-8")
        return subprocess.run(["bash", str(RUN), "--surfaces", "bar", *extra, "--candidate", str(self.d / "broken.css"),
                               "--out", str(self.d / "out")], capture_output=True, text=True, timeout=600)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_broken_sheet(self):
        # Unknown property and unit: St ignores them silently; the static check fails.
        r = self._run(".m3e-test { colour: red; }\n.m3e-test { width: 12qq; }\n")
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("property unknown to St: colour", r.stderr)
        self.assertIn("unit unknown to St: width: 12qq", r.stderr)
        # The Shell did run (captures of both modes): the failure comes from the sheet.
        for mode in ("dark", "light"):
            self.assertTrue((self.d / "out" / mode / "shell-bar-normal.png").exists(), mode)

    def test_syntax_error(self):
        # Syntax error: St drops the whole sheet and says so in shell.log (CSS_ERROR_PATTERN).
        r = self._run("#panel { height: 50px; }\n.m3e-test { color: red\n")
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("CSS parse errors in shell.log", r.stderr)
        self.assertIn("Error parsing stylesheet", (self.d / "out" / "css-errors-shell.txt").read_text())

    def test_remote_provider_guard(self):
        # Fake in-process "remote" provider added after the removal, like an asynchronous reload of the Shell: the
        # `search` scenario must fail (guard of the surface).
        self.d = Path(tempfile.mkdtemp())
        r = subprocess.run(["bash", str(RUN), "--surfaces", "search", "--fake-remote", "--out", str(self.d / "out")],
                           capture_output=True, text=True, timeout=600)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        for mode in ("dark", "light"):
            result = (self.d / "out" / "nested" / f"search:{mode}.json").read_text(encoding="utf-8")
            self.assertIn("fake-remote", result, mode)


if __name__ == "__main__":
    unittest.main()
