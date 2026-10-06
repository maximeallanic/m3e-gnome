"""Pure parts of render_theme.py (path mapping, sandboxed config, concatenation): temp files only, matugen and
material-palette are never run."""
import sys, tempfile, tomllib, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import render_theme  # noqa: E402

CONFIG = """
[config]
wallpaper_tool = "swww"

[templates.gtk3]
input_path  = "~/.themes/Material-Gnome/gtk-3.0/colors-template.css"
output_path = "~/.themes/Material-Gnome/gtk-3.0/colors.css"
post_hook   = "gsettings set org.gnome.desktop.interface gtk-theme x"

[templates.gtk4]
input_path  = "~/.themes/Material-Gnome/gtk-4.0/colors-template.css"
output_path = "~/.themes/Material-Gnome/gtk-4.0/colors.css"

[templates.shell-20-b]
input_path  = "~/.config/m3e-gnome/shell/20-b.css"
output_path = "~/.config/m3e-gnome/shell-out/20-b.css"
index = 2

[templates.shell-10-a]
input_path  = "~/.config/m3e-gnome/shell/10-a.css"
output_path = "~/.config/m3e-gnome/shell-out/10-a.css"
index = 1

[templates.m3e-extensions]
input_path  = "~/.config/m3e-gnome/m3e-extensions-template.css"
output_path = "~/.local/share/m3e-gnome/m3e-extensions.css"

[templates.ptyxis]
input_path  = "~/.config/m3e-gnome/overrides/ptyxis-material.palette"
output_path = "~/.local/share/org.gnome.Ptyxis/palettes/material.palette"
"""


class TestMapInput(unittest.TestCase):
    def setUp(self):
        self.root, self.base = Path("/repo/theme"), Path("/base/Material-Gnome")

    def test_shell_parts(self):
        self.assertEqual(render_theme.map_input("~/.config/m3e-gnome/shell/10-a.css", self.root, self.base),
                         self.root / "shell" / "m3e-shell" / "10-a.css")

    def test_overrides_and_extensions_template(self):
        self.assertEqual(render_theme.map_input("~/.config/m3e-gnome/overrides/x.css", self.root, self.base),
                         self.root / "overrides" / "x.css")
        self.assertEqual(render_theme.map_input("~/.config/m3e-gnome/m3e-extensions-template.css", self.root,
                                                self.base), self.root / "shell" / "m3e-extensions-template.css")

    def test_base_theme_is_read_only_input(self):
        self.assertEqual(render_theme.map_input("~/.themes/Material-Gnome/gtk-4.0/colors-template.css", self.root,
                                                self.base), self.base / "gtk-4.0" / "colors-template.css")

    def test_unknown_path_refused(self):
        with self.assertRaises(ValueError):
            render_theme.map_input("~/Documents/secret.css", self.root, self.base)


class TestSandboxConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.config = self.d / "config.toml"
        self.config.write_text(CONFIG, encoding="utf-8")
        self.out = self.d / "out"
        self.out.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def sandbox(self):
        return render_theme.sandbox_config(self.config, self.out, Path("/repo/theme"), Path("/base/Material-Gnome"))

    def test_keeps_only_colour_shell_and_extension_templates(self):
        text, outputs = self.sandbox()
        self.assertEqual({n for n, _ in outputs}, {"gtk3", "gtk4", "shell-20-b", "shell-10-a", "m3e-extensions"})

    def test_every_output_inside_out_and_no_hook(self):
        text, outputs = self.sandbox()
        c = tomllib.loads(text)
        self.assertNotIn("post_hook", text)
        self.assertNotIn("wallpaper_tool", text)
        for name, t in c["templates"].items():
            self.assertEqual(set(t), {"input_path", "output_path"}, name)
            self.assertIn(self.out.resolve(), Path(t["output_path"]).resolve().parents, name)
        by_name = dict(outputs)
        self.assertEqual(by_name["gtk3"], self.out / "colors-gtk3.css")
        self.assertEqual(by_name["gtk4"], self.out / "colors-gtk4.css")
        self.assertEqual(by_name["shell-10-a"], self.out / "shell" / "10-a.css")
        self.assertEqual(by_name["m3e-extensions"], self.out / "m3e-extensions.css")

    def test_inputs_are_mapped_to_the_repository(self):
        text, _ = self.sandbox()
        c = tomllib.loads(text)
        self.assertEqual(c["templates"]["shell-10-a"]["input_path"], "/repo/theme/shell/m3e-shell/10-a.css")
        self.assertEqual(c["templates"]["gtk4"]["input_path"], "/base/Material-Gnome/gtk-4.0/colors-template.css")

    def test_no_template_kept_is_an_error(self):
        self.config.write_text('[templates.ptyxis]\ninput_path = "a"\noutput_path = "b"\n', encoding="utf-8")
        with self.assertRaises(ValueError):
            self.sandbox()

    def test_quote_in_path_refused(self):
        weird = Path(self.d / 'we"ird')
        weird.mkdir()
        with self.assertRaises(ValueError):
            render_theme.sandbox_config(self.config, weird, Path("/repo/theme"), Path("/base/Material-Gnome"))


class TestCheckSandbox(unittest.TestCase):
    def test_accepts_a_confined_config(self):
        with tempfile.TemporaryDirectory() as d:
            text = f'[config]\nversion_check = false\n[templates.a]\ninput_path = "/x"\noutput_path = "{d}/a.css"\n'
            render_theme.check_sandbox(text, d)

    def test_refuses_output_outside_out(self):
        with tempfile.TemporaryDirectory() as d:
            text = '[templates.a]\ninput_path = "/x"\noutput_path = "/tmp/elsewhere/a.css"\n'
            with self.assertRaises(ValueError):
                render_theme.check_sandbox(text, d)

    def test_refuses_dotdot_escape(self):
        with tempfile.TemporaryDirectory() as d:
            text = f'[templates.a]\ninput_path = "/x"\noutput_path = "{d}/../escape.css"\n'
            with self.assertRaises(ValueError):
                render_theme.check_sandbox(text, d)

    def test_refuses_hooks_and_extra_keys(self):
        with tempfile.TemporaryDirectory() as d:
            text = f'[templates.a]\ninput_path = "/x"\noutput_path = "{d}/a.css"\npost_hook = "rm -rf ~"\n'
            with self.assertRaises(ValueError):
                render_theme.check_sandbox(text, d)

    def test_refuses_unexpected_sections_and_settings(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                render_theme.check_sandbox('[hooks]\nx = 1\n', d)
            with self.assertRaises(ValueError):
                render_theme.check_sandbox('[config]\nreload_apps_list = ["x"]\n', d)


class TestConcatenate(unittest.TestCase):
    def test_parts_in_index_order(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "shell").mkdir()
            cfg = out / "matugen.toml"
            cfg.write_text('[templates.shell-20-b]\nindex = 2\ninput_path = "x"\noutput_path = "y"\n'
                           '[templates.shell-10-a]\nindex = 1\ninput_path = "x"\noutput_path = "y"\n'
                           '[templates.gtk4]\nindex = 0\ninput_path = "x"\noutput_path = "y"\n', encoding="utf-8")
            (out / "shell" / "10-a.css").write_text("A\n", encoding="utf-8")
            (out / "shell" / "20-b.css").write_text("B\n", encoding="utf-8")
            render_theme.concatenate_shell_parts(cfg, out)
            self.assertEqual((out / "gnome-shell.css").read_text(encoding="utf-8"), "A\nB\n")

    def test_missing_rendered_part_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "shell").mkdir()
            cfg = out / "matugen.toml"
            cfg.write_text('[templates.shell-10-a]\nindex = 1\ninput_path = "x"\noutput_path = "y"\n', encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                render_theme.concatenate_shell_parts(cfg, out)


if __name__ == "__main__":
    unittest.main()
