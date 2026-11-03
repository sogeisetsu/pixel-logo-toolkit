"""画布模式与排版测试。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from pixellogo import modes, presets  # noqa: E402
from pixellogo.layout import Design, build_scene, missing_glyph_warnings  # noqa: E402


def make(mode_key="poster", **kwargs):
    mode = modes.get_mode(mode_key)
    preset = presets.get_preset(kwargs.pop("preset_key", "terminal"))
    return build_scene(Design(title=kwargs.pop("title", "REA"), preset=preset,
                              mode=mode, **kwargs))


class TestModes(unittest.TestCase):
    def test_output_sizes(self):
        self.assertEqual(modes.get_mode("poster").output_size, (1080, 1440))
        self.assertEqual(modes.get_mode("card").output_size, (1440, 1080))
        self.assertEqual(modes.get_mode("banner").output_size, (1280, 640))
        self.assertEqual(modes.get_mode("slide").output_size, (1920, 1080))
        self.assertEqual(modes.get_mode("square").output_size, (1080, 1080))

    def test_mode_names_are_semantic_words(self):
        for mode in modes.list_modes():
            self.assertRegex(mode.key, r"^[a-z]+$")
            self.assertNotIn(":", mode.key)

    def test_ratio_display(self):
        self.assertEqual(modes.get_mode("slide").ratio, "16:9")
        self.assertEqual(modes.get_mode("square").ratio, "1:1")

    def test_legacy_aliases_still_work(self):
        self.assertEqual(modes.get_mode("xhs").key, "poster")
        self.assertEqual(modes.get_mode("og").key, "banner")
        self.assertEqual(modes.get_mode("4:3").key, "card")
        self.assertEqual(modes.get_mode("16:9").key, "slide")
        self.assertEqual(modes.get_mode("1:1").key, "square")
        self.assertEqual(modes.get_mode("github").key, "banner")

    def test_unknown_mode(self):
        with self.assertRaises(ValueError):
            modes.get_mode("hexagon")

    def test_custom_mode(self):
        mode = modes.custom_mode(1200, 900)
        self.assertEqual(mode.output_size, (2400, 1800))


class TestLayout(unittest.TestCase):
    def test_every_mode_fills_canvas_with_background(self):
        for key in ("poster", "card", "banner", "slide", "square"):
            scene = make(key, subtitle=["LINE ONE"], desc=["footnote"])
            self.assertEqual((scene.width, scene.height),
                             (modes.get_mode(key).width, modes.get_mode(key).height))
            self.assertTrue(scene.rects)

    def test_rects_stay_inside_canvas(self):
        for key in ("poster", "card", "banner", "slide", "square"):
            scene = make(key, subtitle=["SUB"], desc=["DESC"])
            for rect in scene.rects:
                self.assertGreaterEqual(rect.x, 0, key)
                self.assertGreaterEqual(rect.y, 0, key)
                self.assertLessEqual(rect.x + rect.w, scene.width, f"{key} 右溢出")
                self.assertLessEqual(rect.y + rect.h, scene.height, f"{key} 下溢出")

    def test_palette_is_small(self):
        scene = make(subtitle=["SUB"], desc=["DESC"])
        self.assertLessEqual(len(scene.colors), 5)

    def test_long_title_shrinks_within_content_width(self):
        tight = make("banner", title="A VERY LONG TITLE THAT MUST SHRINK")
        short = make("banner", title="AB")
        self.assertGreater(len(tight.rects), 0)
        self.assertGreater(len(short.rects), 0)

    def test_cjk_title_renders(self):
        scene = make("poster", title="像素工具包", subtitle=["中文副标题"])
        self.assertGreater(len(scene.rects), 100)

    def test_shadow_can_be_disabled(self):
        with_shadow = make(shadow_offset=1, subtitle=["S"])
        without = make(shadow_offset=0, subtitle=["S"])
        self.assertGreater(len(with_shadow.rects), len(without.rects))

    def test_badge_and_eyebrow(self):
        plain = make(subtitle=["S"])
        decorated = make(subtitle=["S"], badge="NEW", eyebrow="TOOLKIT")
        self.assertGreater(len(decorated.rects), len(plain.rects))

    def test_divider_none_removes_accent(self):
        scene = make(divider="none", subtitle=["S"], desc=["D"])
        self.assertNotIn("#FF6104", scene.colors)

    def test_center_alignment(self):
        left = make(align="left", subtitle=["SHORT"])
        center = make(align="center", subtitle=["SHORT"])
        self.assertNotEqual(sorted((r.x for r in left.rects))[:5],
                            sorted((r.x for r in center.rects))[:5])

    def test_uppercase_changes_glyphs(self):
        plain = make(title="abc", subtitle=["sub"])
        upper = make(title="abc", subtitle=["sub"], uppercase=True)
        self.assertNotEqual(
            [(r.x, r.y, r.w, r.h) for r in plain.rects],
            [(r.x, r.y, r.w, r.h) for r in upper.rects],
        )

    def test_tracking_tightens_ink_width(self):
        def ink_width(scene):
            return max(r.x + r.w for r in scene.rects) - min(r.x for r in scene.rects)

        # 固定字号，避免"标题自动铺满"把字距差异吃掉
        loose = make(title="PIXEL", title_size=48, tracking=1.0)
        tight = make(title="PIXEL", title_size=48, tracking=0.8)
        self.assertLess(ink_width(tight), ink_width(loose))

    def test_leading_increases_block_height(self):
        def ink_height(scene):
            return max(r.y + r.h for r in scene.rects) - min(r.y for r in scene.rects)

        normal = make(subtitle=["ONE", "TWO", "THREE"], desc=["D"])
        loose = make(subtitle=["ONE", "TWO", "THREE"], desc=["D"], leading=1.5)
        self.assertGreater(ink_height(loose), ink_height(normal))

    def test_motif_fits_in_narrow_modes(self):
        # card 的文本区原本占 94%，显式要求装饰时必须让出位置而不是静默忽略
        scene = make("card", subtitle=["S"], motif="blocks")
        squares = [r for r in scene.rects
                   if r.w == r.h and r.w > 20 and r.x > scene.width * 0.6]
        self.assertGreaterEqual(len(squares), 3)

    def test_motif_off_in_banner_by_default(self):
        with_motif = make("banner", subtitle=["S"])
        without = make("banner", subtitle=["S"], motif="none")
        self.assertGreater(len(with_motif.rects), len(without.rects))

    def test_bg_pattern_adds_texture(self):
        plain = make(subtitle=["S"])
        gridded = make(subtitle=["S"], pattern="grid")
        self.assertGreater(len(gridded.rects), len(plain.rects))
        self.assertEqual(len(gridded.colors), len(plain.colors) + 1)

    def test_bg_pattern_stays_inside_canvas(self):
        for pattern in ("grid", "dots", "scanlines"):
            scene = make(subtitle=["S"], pattern=pattern)
            for rect in scene.rects:
                self.assertGreaterEqual(rect.x, 0, pattern)
                self.assertGreaterEqual(rect.y, 0, pattern)
                self.assertLessEqual(rect.x + rect.w, scene.width, pattern)
                self.assertLessEqual(rect.y + rect.h, scene.height, pattern)

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            make(title="  ")

    def test_missing_glyph_warning_names_only_the_missing_chars(self):
        design = Design(title="ZIG", preset=presets.get_preset("terminal"),
                        mode=modes.get_mode("card"), desc=["compile time 即运行时"])
        warnings = missing_glyph_warnings(design)
        self.assertTrue(warnings)
        self.assertTrue(any("即" in line for line in warnings), warnings)
        # 同行里能正常渲染的字不应被牵连进告警
        for char in "运行时":
            self.assertFalse(any(char in line for line in warnings), char)

    def test_no_glyph_warning_for_covered_text(self):
        design = Design(title="ZIG", preset=presets.get_preset("terminal"),
                        mode=modes.get_mode("card"), desc=["compile time 运行时"])
        self.assertEqual(missing_glyph_warnings(design), [])


LONG_CJK = "自动折行之后每一行都不会超出文本区域宽度限制这是用来验证折行是否生效的一整段中文副标题"


class TestWrapping(unittest.TestCase):
    def test_long_subtitle_stays_inside_canvas(self):
        scene = make("card", subtitle=[LONG_CJK])
        for rect in scene.rects:
            self.assertLessEqual(rect.x + rect.w, scene.width)
            self.assertLessEqual(rect.y + rect.h, scene.height)

    def test_wrap_can_be_disabled(self):
        # 关闭折行后回到旧行为：单行硬挤，越出画布右侧
        wrapped = make("card", subtitle=[LONG_CJK])
        raw = make("card", subtitle=[LONG_CJK], wrap=False)
        self.assertGreater(max(r.x + r.w for r in raw.rects),
                           max(r.x + r.w for r in wrapped.rects))
        self.assertGreater(max(r.x + r.w for r in raw.rects), raw.width)

    def test_many_lines_shrink_to_fit(self):
        scene = make("poster", subtitle=[f"LINE {index}" for index in range(14)])
        for rect in scene.rects:
            self.assertLessEqual(rect.y + rect.h, scene.height)

    def test_overflow_is_reported_when_even_minimum_font_fails(self):
        design = Design(title="TEST", preset=presets.get_preset("terminal"),
                        mode=modes.get_mode("poster"),
                        subtitle=[f"LINE {index}" for index in range(60)])
        diagnostics: list[str] = []
        build_scene(design, diagnostics)
        self.assertTrue(diagnostics)
        self.assertIn("px", diagnostics[0])

    def test_normal_content_has_no_diagnostics(self):
        design = Design(title="REA", preset=presets.get_preset("terminal"),
                        mode=modes.get_mode("poster"),
                        subtitle=["REVERSE ENGINEER"], desc=["One CLI for agents"])
        diagnostics: list[str] = []
        build_scene(design, diagnostics)
        self.assertEqual(diagnostics, [])


if __name__ == "__main__":
    unittest.main()
