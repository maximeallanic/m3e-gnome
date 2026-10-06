import importlib.machinery
import importlib.util
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path

BIN = Path(__file__).resolve().parents[1]


def load(name):
    loader = importlib.machinery.SourceFileLoader(name.replace('-', '_'), str(BIN / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


sync = load('material-sync')
tab = load('ptyxis-active-tab')


class SyncTest(unittest.TestCase):
    def test_missing_tool_is_a_failed_run_not_a_crash(self):
        r = sync.run(['definitely-not-installed-tool-xyz'])
        self.assertEqual(r.returncode, 127)

    def test_hanabi_can_be_disabled(self):
        with mock.patch.dict(os.environ, {'MATERIAL_SYNC_HANABI': '0'}), \
                mock.patch.object(sync, 'gget', side_effect=AssertionError('must not be read')):
            self.assertIsNone(sync.hanabi_image())

    def test_hanabi_absent_is_silent(self):
        with mock.patch.object(sync, 'gget', return_value=['other@ext']):
            self.assertIsNone(sync.hanabi_image())

    def test_matugen_files_live_in_our_own_directory(self):
        self.assertEqual(sync.MATUGEN_CONFIG.parts[-3:], ('m3e-gnome', 'matugen', 'config.toml'))
        self.assertEqual(sync.PALETTE_CONFIG.parts[-3:], ('m3e-gnome', 'matugen', 'palette.json'))

    def test_gvariant(self):
        self.assertEqual(sync.gvariant("'prefer-dark'\n"), 'prefer-dark')
        self.assertEqual(sync.gvariant("['a@b', 'c']"), ['a@b', 'c'])
        self.assertEqual(sync.gvariant('@as []'), [])
        self.assertEqual(sync.gvariant(''), '')
        self.assertEqual(sync.gvariant('"it\'s"'), "it's")

    def test_uri_to_path(self):
        self.assertEqual(sync.uri_to_path('file:///home/u/My%20Pics/a%C3%A9.jpg'), Path('/home/u/My Pics/aé.jpg'))
        self.assertEqual(sync.uri_to_path('/plain/path.png'), Path('/plain/path.png'))

    def test_closest_image(self):
        video = Path('/w/forest-long.mp4')
        same = Path('/w/forest-long.jpg')
        near = Path('/w/forest-lon.png')
        other = Path('/w/city.jpg')
        self.assertEqual(sync.closest_image(video, [other, same, near]), same)
        self.assertEqual(sync.closest_image(video, [other, near]), near)
        self.assertIsNone(sync.closest_image(video, [other]))
        # non-Latin names and Unicode normalisation (NFD vs NFC) are compared on equal terms
        self.assertEqual(sync.closest_image(Path('/w/森林の朝.mp4'), [Path('/w/森林の朝.jpg')]), Path('/w/森林の朝.jpg'))
        self.assertEqual(sync.closest_image(Path('/w/café.mp4'), [Path('/w/café.jpg')]), Path('/w/café.jpg'))


PALETTE = """[Palette]
Name=X

[Dark]
Foreground=#ffffff
Background=#000000

[Light]
Foreground=#111111
Background=#eeeeee
"""


class TabTest(unittest.TestCase):
    def test_faces(self):
        self.assertEqual(tab.faces(PALETTE), {'dark': ('#000000', '#ffffff'), 'light': ('#eeeeee', '#111111')})

    def test_faces_single_and_invalid(self):
        one = '[Palette]\nBackground=#101010\nForeground=#f0f0f0\n'
        self.assertEqual(tab.faces(one), {'dark': ('#101010', '#f0f0f0'), 'light': ('#101010', '#f0f0f0')})
        self.assertEqual(tab.faces('[Dark]\nBackground=red\nForeground=#fff\n'), {})

    def test_stylesheet(self):
        css = tab.stylesheet('X', tab.faces(PALETTE))
        self.assertIn('@media (prefers-color-scheme: dark)', css)
        self.assertIn('--surface: #eeeeee;', css)
        self.assertNotIn('--surface', tab.stylesheet('material', {}))

    def test_main_writes_once(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'sub' / 'tab.css'
            self.assertEqual(tab.main(['--palette', 'Material', '--output', str(out)]), 0)
            self.assertTrue(out.is_file())
            self.assertEqual(tab.main(['--palette', 'bad;name', '--output', str(out)]), 2)


if __name__ == '__main__':
    unittest.main()
