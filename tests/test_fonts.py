"""字体注册与字形覆盖测试。"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

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


class TestLanguageVariants(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.env = patch.dict(os.environ, {"PIXELLOGO_FONT_DIR": self.tmp})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_bundled_variant_resolves(self):
        path = fonts.cjk_font_path("zh-hans")
        self.assertTrue(path.endswith("ArkPixel-zh-hans.ttf"))
        self.assertTrue(os.path.isfile(path))

    def test_aliases_normalize(self):
        self.assertEqual(fonts.normalize_lang("zh_CN"), "zh-hans")
        self.assertEqual(fonts.normalize_lang("zh-TW"), "zh-hant")
        self.assertEqual(fonts.normalize_lang("JP"), "ja")

    def test_unknown_language(self):
        with self.assertRaises(fonts.FontError):
            fonts.normalize_lang("fr")

    def test_missing_variant_gives_install_hint(self):
        with self.assertRaises(fonts.FontError) as ctx:
            fonts.cjk_font_path("ja")
        self.assertIn("fonts install ja", str(ctx.exception))

    def test_cached_variant_is_picked_up(self):
        target = os.path.join(self.tmp, "ArkPixel-ja.ttf")
        with open(target, "wb") as handle:
            handle.write(b"\x00" * 2048)
        self.assertEqual(fonts.cjk_font_path("ja"), target)

    def test_variant_status_lists_all(self):
        status = {key: state for key, state, _label in fonts.variant_status()}
        self.assertEqual(status["zh-hans"], "bundled")
        self.assertIn("ja", status)
        self.assertIn("ko", status)

    def test_korean_variant_uses_hangul_font(self):
        # Ark Pixel 的 ko 版没有谚文，韩语必须走 Galmuri
        self.assertEqual(fonts.CJK_VARIANTS["ko"].filename, "Galmuri11.ttf")
        license_path = fonts.LICENSE_DIR / "OFL-Galmuri.txt"
        self.assertTrue(license_path.is_file())
        self.assertIn("SIL OPEN FONT LICENSE", license_path.read_text(encoding="utf-8").upper())


if __name__ == "__main__":
    unittest.main()
