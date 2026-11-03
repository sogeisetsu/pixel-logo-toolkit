"""渲染后端与文字栅格化测试。"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from pixellogo import fonts, text  # noqa: E402
from pixellogo.render import raster, svg  # noqa: E402
from pixellogo.scene import Rect, Scene  # noqa: E402


def demo_scene():
    scene = Scene(width=40, height=20, background="#EEF1F6")
    scene.add(Rect(4, 4, 10, 6, "#02ADFB"))
    return scene


class TestSvg(unittest.TestCase):
    def setUp(self):
        self.svg = svg.to_svg(demo_scene(), scale=2)

    def test_canvas_scaled(self):
        self.assertIn('width="80"', self.svg)
        self.assertIn('height="40"', self.svg)

    def test_crisp_edges_declared(self):
        self.assertIn('shape-rendering="crispEdges"', self.svg)

    def test_no_text_no_gradient(self):
        for forbidden in ("<text", "gradient", "filter", "opacity"):
            self.assertNotIn(forbidden, self.svg)

    def test_every_rect_uses_integer_coordinates(self):
        for element in re.findall(r"<rect [^>]*/>", self.svg):
            for value in re.findall(r'(?:x|y|width|height)="([^"]+)"', element):
                self.assertRegex(value, r"^\d+$")

    def test_rect_count(self):
        self.assertEqual(self.svg.count("<rect"), 2)  # 底色 + 主体


class TestRaster(unittest.TestCase):
    def test_separation_of_colors_is_hard(self):
        image = raster.to_image(demo_scene(), scale=2)
        self.assertEqual(image.size, (80, 40))
        self.assertEqual(image.getpixel((8, 8)), (2, 173, 251))
        self.assertEqual(image.getpixel((9, 9)), (2, 173, 251))
        # 边界外一个像素必须是底色，不能出现过渡色
        self.assertEqual(image.getpixel((7, 8)), (238, 241, 246))
        self.assertEqual(image.getpixel((8, 7)), (238, 241, 246))

    def test_scale_is_integer_multiple(self):
        one = raster.to_image(demo_scene(), scale=1)
        two = raster.to_image(demo_scene(), scale=2)
        self.assertEqual(one.width * 2, two.width)
        self.assertEqual(one.height * 2, two.height)


class TestTextMask(unittest.TestCase):
    chain = None

    @classmethod
    def setUpClass(cls):
        cls.chain = fonts.resolve_chain("press-start-2p")

    def test_latin_line_has_ink(self):
        mask = text.line_mask("REA", 64, self.chain)
        self.assertIsNotNone(mask)
        self.assertGreater(mask.width, 50)
        self.assertGreater(mask.height, 10)

    def test_cjk_line_falls_back(self):
        mask = text.line_mask("逆向工程", 48, self.chain)
        self.assertIsNotNone(mask)
        self.assertGreater(mask.width, 40)

    def test_mixed_line_uses_single_font(self):
        mask = text.line_mask("REA 逆向", 48, self.chain)
        self.assertIsNotNone(mask)

    def test_empty_line(self):
        self.assertIsNone(text.line_mask("", 32, self.chain))

    def test_mask_rects_are_integers_and_merged(self):
        mask = text.line_mask("H", 48, self.chain)
        rects = text.mask_rects(mask.image, 10, 20, "#1F1F1F")
        self.assertTrue(rects)
        for rect in rects:
            for value in (rect.x, rect.y, rect.w, rect.h):
                self.assertIsInstance(value, int)
        # 垂直合并后，矩形数量应远小于掩膜像素行数
        self.assertLess(len(rects), mask.height * 4)

    def test_shadow_shares_geometry(self):
        mask = text.line_mask("A", 32, self.chain)
        rects = text.mask_rects(mask.image, 0, 0, "#000000")
        shadows = text.shadow_rects(rects, 6, 6, "#2B3444")
        self.assertEqual(len(rects), len(shadows))
        self.assertEqual(shadows[0].x - rects[0].x, 6)
        self.assertEqual(shadows[0].y - rects[0].y, 6)


class TestWrap(unittest.TestCase):
    chain = None

    @classmethod
    def setUpClass(cls):
        cls.chain = fonts.resolve_chain("silkscreen")

    def test_measure_matches_mask_within_side_bearing(self):
        for text_value in ("REVERSE ENGINEER", "REA"):
            measured = text.measure_width(text_value, 23, self.chain)
            mask = text.line_mask(text_value, 23, self.chain)
            # 步进宽度不小于墨迹宽度，且不会宽得离谱
            self.assertGreaterEqual(measured, mask.width)
            self.assertLessEqual(measured - mask.width, 23)

    def test_short_line_is_untouched(self):
        self.assertEqual(text.wrap_line("SHORT", 23, self.chain, 400), ["SHORT"])

    def test_latin_breaks_on_spaces(self):
        lines = text.wrap_line("REVERSE ENGINEER", 23, self.chain, 200)
        self.assertEqual(lines, ["REVERSE", "ENGINEER"])
        for line in lines:
            self.assertLessEqual(text.measure_width(line, 23, self.chain), 200)

    def test_cjk_breaks_per_character(self):
        source = "自动折行之后每一行都不会超出文本区域宽度限制"
        lines = text.wrap_line(source, 23, self.chain, 200)
        self.assertGreater(len(lines), 1)
        self.assertEqual("".join(lines), source)
        for line in lines:
            self.assertLessEqual(text.measure_width(line, 23, self.chain), 200)

    def test_long_word_is_hard_split(self):
        source = "https://example.com/a/very/long/path/without/spaces"
        lines = text.wrap_line(source, 18, self.chain, 150)
        self.assertGreater(len(lines), 1)
        self.assertEqual("".join(lines), source)
        for line in lines:
            self.assertLessEqual(text.measure_width(line, 18, self.chain), 150)

    def test_empty_line_stays_empty(self):
        self.assertEqual(text.wrap_line("", 23, self.chain, 200), [""])

    def test_tracking_is_respected(self):
        tight = text.measure_width("REVERSE", 23, self.chain, tracking=0.8)
        normal = text.measure_width("REVERSE", 23, self.chain)
        self.assertLess(tight, normal)


if __name__ == "__main__":
    unittest.main()
