"""字体注册与字形覆盖测试。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from pixellogo import fonts  # noqa: E402


class TestRegistry(unittest.TestCase):
    def test_all_builtin_fonts_exist(self):
        for spec in fonts.list_fonts():
            self.assertTrue(spec.path.is_file(), f"缺失字体文件：{spec.path}")
            self.assertGreater(spec.path.stat().st_size, 10_000)

    def test_every_font_has_license(self):
        for spec in fonts.list_fonts():
            license_path = fonts.LICENSE_DIR / spec.license_file
            self.assertTrue(license_path.is_file(), f"缺失许可证：{license_path}")
            self.assertIn("SIL OPEN FONT LICENSE", license_path.read_text(encoding="utf-8").upper())

    def test_font_path_by_key_and_by_path(self):
        path = fonts.font_path("press-start-2p")
        self.assertTrue(path.endswith("PressStart2P.ttf"))
        self.assertEqual(fonts.font_path(path), path)

    def test_unknown_font_raises(self):
        with self.assertRaises(fonts.FontError):
            fonts.font_path("no-such-font")


class TestCoverage(unittest.TestCase):
    def test_latin_fonts_lack_cjk(self):
        for key in ("press-start-2p", "silkscreen", "pixelify"):
            path = fonts.font_path(key)
            self.assertTrue(fonts.covers(path, "A"), key)
            self.assertFalse(fonts.covers(path, "中"), key)

    def test_cjk_font_covers_both(self):
        path = fonts.font_path("ark-pixel")
        for char in ("A", "中", "文", "，", "！"):
            self.assertTrue(fonts.covers(path, char), char)

    def test_missing_chars_is_deduplicated(self):
        path = fonts.font_path("press-start-2p")
        self.assertEqual(fonts.missing_chars(path, "中文中文"), ["中", "文"])


class TestSelection(unittest.TestCase):
    def test_unified_keeps_primary_for_pure_latin(self):
        chain = fonts.resolve_chain("press-start-2p")
        self.assertEqual(fonts.pick_unified("REA", chain), fonts.font_path("press-start-2p"))

    def test_unified_switches_to_cjk_for_mixed_text(self):
        chain = fonts.resolve_chain("press-start-2p")
        self.assertEqual(fonts.pick_unified("REA 逆向", chain), fonts.font_path("ark-pixel"))

    def test_chain_deduplicates(self):
        chain = fonts.resolve_chain("ark-pixel", ["ark-pixel"])
        self.assertEqual(len(chain), 1)


if __name__ == "__main__":
    unittest.main()
