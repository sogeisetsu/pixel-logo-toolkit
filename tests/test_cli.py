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
        for key in ("xhs", "4:3", "og"):
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

        expected = {"xhs": (1080, 1440), "4:3": (1440, 1080), "og": (1280, 640)}
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
            result = run_cli("-t", "My Title", "-m", "og", "-o", tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            files = os.listdir(tmp)
            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].startswith("My-Title"))

    def test_missing_title_is_an_error(self):
        result = run_cli("-m", "og")
        self.assertNotEqual(result.returncode, 0)

    def test_unknown_preset_is_an_error(self):
        result = run_cli("-t", "X", "-p", "nope")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("未知风格预设", result.stderr)


if __name__ == "__main__":
    unittest.main()
