import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location('papirus_symbolic', Path(__file__).resolve().parent.parent / 'papirus-symbolic.py')
ps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ps)


class RefreshCache(unittest.TestCase):
    def test_missing_tool_is_reported_not_fatal(self):
        err = io.StringIO()
        with mock.patch.object(ps.shutil, 'which', return_value=None), redirect_stderr(err):
            self.assertFalse(ps.refresh_cache(Path('/nowhere')))
        self.assertIn('no icon cache', err.getvalue())

    def test_failing_tool_is_an_error(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(ps.shutil, 'which', return_value='/bin/false'):
            with self.assertRaises(ps.subprocess.CalledProcessError):
                ps.refresh_cache(Path(d))

    def test_tool_is_run(self):
        with mock.patch.object(ps.shutil, 'which', return_value='/usr/bin/tool'), \
                mock.patch.object(ps.subprocess, 'run') as run:
            self.assertTrue(ps.refresh_cache(Path('/t')))
        run.assert_called_once_with(['/usr/bin/tool', '-q', '-f', '/t'], check=True)

    def test_main_builds_theme_without_cache_tool(self):
        with tempfile.TemporaryDirectory() as d:
            pap = Path(d) / 'Papirus'
            (pap / '16x16/symbolic/actions').mkdir(parents=True)
            (pap / 'index.theme').write_text(
                '[Icon Theme]\nName=Papirus\nDirectories=16x16/symbolic/actions,16x16/apps\n\n'
                '[16x16/symbolic/actions]\nSize=16\n\n[16x16/apps]\nSize=16\n')
            with mock.patch.object(ps.shutil, 'which', return_value=None), redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                self.assertEqual(ps.main(['x', d]), 0)
            self.assertTrue((Path(d) / 'Papirus-Symbolic/index.theme').is_file())
            self.assertTrue((Path(d) / 'Papirus-Symbolic/16x16/symbolic').is_symlink())


if __name__ == '__main__':
    unittest.main()
