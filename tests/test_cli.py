"""CLI 集成测试。"""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")


def run_cli(*args):
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "pixellogo", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=180,
    )


class TestVersion(unittest.TestCase):
    def test_version_flag(self):
        result = run_cli("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pixellogo 0.1.0", result.stdout)

    def test_help_lists_entrypoint(self):
        result = run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pixellogo", result.stdout)


class TestList(unittest.TestCase):
    def test_list_modes(self):
        result = run_cli("--list", "modes")
        self.assertEqual(result.returncode, 0, result.stderr)
        for key in ("poster", "card", "banner", "slide", "square"):
            self.assertIn(key, result.stdout)
        self.assertIn("1080×1440", result.stdout)

    def test_list_presets(self):
        result = run_cli("--list", "presets")
        self.assertIn("terminal", result.stdout)
        self.assertIn("cyber", result.stdout)

    def test_list_fonts(self):
        result = run_cli("--list", "fonts")
        self.assertIn("ark-pixel", result.stdout)


class TestRender(unittest.TestCase):
    def test_three_modes(self):
        from PIL import Image

        expected = {
            "poster": (1080, 1440),
            "card": (1440, 1080),
            "banner": (1280, 640),
            "slide": (1920, 1080),
            "square": (1080, 1080),
        }
        with tempfile.TemporaryDirectory() as tmp:
            for mode, size in expected.items():
                target = os.path.join(tmp, f"{mode.replace(':', 'x')}.png")
                result = run_cli("-t", "REA", "-s", "REVERSE ENGINEER", "-d", "foot note",
                                 "-m", mode, "-o", target)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(os.path.isfile(target))
                with Image.open(target) as image:
                    self.assertEqual(image.size, size)

    def test_directory_output_uses_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli("-t", "My Title", "-m", "banner", "-o", tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            files = sorted(os.listdir(tmp))
            self.assertEqual(len(files), 2)  # 默认同时产出 png 与 svg
            self.assertTrue(all(name.startswith("My-Title") for name in files))
            self.assertEqual({os.path.splitext(n)[1] for n in files}, {".png", ".svg"})

    def test_format_png_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli("-t", "A", "-m", "banner", "-f", "png", "-o", tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([n[-4:] for n in os.listdir(tmp)], [".png"])

    def test_format_svg_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli("-t", "A", "-m", "banner", "-f", "svg", "-o", tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            files = os.listdir(tmp)
            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].endswith(".svg"))
            with open(os.path.join(tmp, files[0]), encoding="utf-8") as handle:
                content = handle.read()
            self.assertTrue(content.startswith("<svg"))
            self.assertIn('shape-rendering="crispEdges"', content)

    def test_explicit_file_path_overrides_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "cover.svg")
            result = run_cli("-t", "A", "-m", "banner", "-f", "both", "-o", target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(sorted(os.listdir(tmp)), ["cover.png", "cover.svg"])

    def test_batch_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli("-c", os.path.join(ROOT, "examples", "batch.jsonc"),
                             "-f", "png", "-o", tmp, "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = __import__("json").loads(result.stdout)
            self.assertEqual(len(payload), 3)
            self.assertEqual(len(os.listdir(tmp)), 3)

    def test_json_flag_reports_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli("-t", "A", "-m", "banner", "-f", "png", "-o", tmp, "--json")
            payload = __import__("json").loads(result.stdout)
            self.assertEqual(payload[0]["width"], 1280)
            self.assertEqual(payload[0]["height"], 640)

    def test_missing_title_is_an_error(self):
        result = run_cli("-m", "banner")
        self.assertNotEqual(result.returncode, 0)

    def test_unknown_preset_is_an_error(self):
        result = run_cli("-t", "X", "-p", "nope")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("未知风格预设", result.stderr)


if __name__ == "__main__":
    unittest.main()
