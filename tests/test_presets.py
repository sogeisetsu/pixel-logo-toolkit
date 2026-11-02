"""风格预设测试：数量、命名与可读性。"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from pixellogo import presets  # noqa: E402

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class TestPresetSet(unittest.TestCase):
    def test_has_ten_presets(self):
        self.assertEqual(len(presets.PRESETS), 10)

    def test_keys_are_lowercase_words(self):
        for key in presets.PRESETS:
            self.assertRegex(key, r"^[a-z]+$")

    def test_labels_are_unique(self):
        labels = [preset.label for preset in presets.list_presets()]
        self.assertEqual(len(labels), len(set(labels)))

    def test_all_colors_are_hex(self):
        for preset in presets.list_presets():
            for field in ("bg", "fg", "primary", "accent", "shadow"):
                self.assertRegex(getattr(preset, field), HEX, f"{preset.key}.{field}")


class TestReadability(unittest.TestCase):
    def test_foreground_contrast(self):
        for preset in presets.list_presets():
            ratio = presets.contrast_ratio(preset.fg, preset.bg)
            self.assertGreaterEqual(ratio, 4.5, f"{preset.key} 字色对比度不足：{ratio:.2f}")

    def test_primary_contrast(self):
        # 主色只用于超大号标题，按 WCAG"大字号"标准放宽到 2:1
        for preset in presets.list_presets():
            ratio = presets.contrast_ratio(preset.primary, preset.bg)
            self.assertGreaterEqual(ratio, 2.0, f"{preset.key} 主色对比度不足：{ratio:.2f}")

    def test_shadow_is_distinguishable_from_background(self):
        # 浅色底上投影必须明显压深；深色底的投影本就接近纯黑，只要求不是同一个色
        for preset in presets.list_presets():
            self.assertNotEqual(preset.shadow.lower(), preset.bg.lower(), preset.key)
            if presets._luminance(preset.bg) > 0.5:
                ratio = presets.contrast_ratio(preset.shadow, preset.bg)
                self.assertGreaterEqual(ratio, 1.5, f"{preset.key} 投影与底色太接近：{ratio:.2f}")

    def test_contrast_ratio_symmetry(self):
        self.assertAlmostEqual(
            presets.contrast_ratio("#000000", "#FFFFFF"),
            presets.contrast_ratio("#FFFFFF", "#000000"),
        )


if __name__ == "__main__":
    unittest.main()
