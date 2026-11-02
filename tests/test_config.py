"""JSONC 解析与配置合并测试。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from pixellogo import config as configlib  # noqa: E402
from pixellogo import i18n  # noqa: E402
from pixellogo import jsonc  # noqa: E402


def setUpModule():
    # 错误文案随语言变化，这里固定中文，保证断言与宿主语言无关
    i18n.set_language("zh")


def tearDownModule():
    i18n.reset()


class TestJsonc(unittest.TestCase):
    def test_line_comments(self):
        data = jsonc.loads('{\n  // 主标题\n  "title": "REA" // 行尾\n}')
        self.assertEqual(data["title"], "REA")

    def test_block_comments(self):
        data = jsonc.loads('{ /* 块注释 */ "title": "A" }')
        self.assertEqual(data["title"], "A")

    def test_trailing_commas(self):
        data = jsonc.loads('{"title": "A", "subtitle": ["x", "y",],}')
        self.assertEqual(data["subtitle"], ["x", "y"])

    def test_slashes_inside_strings_are_preserved(self):
        data = jsonc.loads('{"desc": ["a // b", "http://x/*y*/"]}')
        self.assertEqual(data["desc"], ["a // b", "http://x/*y*/"])

    def test_comma_inside_string_is_preserved(self):
        data = jsonc.loads('{"title": "a,}", "sub": "[1,]"}')
        self.assertEqual(data["title"], "a,}")

    def test_broken_json_reports_line(self):
        with self.assertRaises(jsonc.JsoncError) as ctx:
            jsonc.loads('{\n  "title": "A",\n  "x": }\n')
        self.assertIn("第 3 行", str(ctx.exception))

    def test_unclosed_block_comment(self):
        with self.assertRaises(jsonc.JsoncError):
            jsonc.loads('{"a": 1} /* 没闭合')


class TestMerge(unittest.TestCase):
    def test_deep_merge_keeps_nested_keys(self):
        base = {"colors": {"bg": "#000000", "fg": "#FFFFFF"}, "preset": "cyber"}
        override = {"colors": {"fg": "#111111"}}
        merged = configlib.deep_merge(base, override)
        self.assertEqual(merged["colors"], {"bg": "#000000", "fg": "#111111"})
        self.assertEqual(merged["preset"], "cyber")

    def test_lists_are_replaced_not_concatenated(self):
        merged = configlib.deep_merge({"subtitle": ["A", "B"]}, {"subtitle": ["C"]})
        self.assertEqual(merged["subtitle"], ["C"])

    def test_set_path_creates_nested(self):
        data = {}
        configlib.set_path(data, "colors.primary", "#FF3D81")
        self.assertEqual(data["colors"]["primary"], "#FF3D81")

    def test_coerce_types(self):
        self.assertEqual(configlib.coerce("3"), 3)
        self.assertEqual(configlib.coerce("0.5"), 0.5)
        self.assertEqual(configlib.coerce("true"), True)
        self.assertEqual(configlib.coerce("#02ADFB"), "#02ADFB")


class TestResolve(unittest.TestCase):
    def test_defaults(self):
        settings = configlib.resolve({"title": "REA"}, {})
        self.assertEqual(settings.mode_key, "poster")
        self.assertEqual(settings.scale, 2)
        self.assertEqual(settings.out, "out")
        self.assertEqual(settings.design.preset.key, "terminal")

    def test_cli_overrides_file(self):
        settings = configlib.resolve(
            {"title": "REA", "preset": "cyber", "mode": "banner"},
            {"preset": "terminal"},
        )
        self.assertEqual(settings.design.preset.key, "terminal")
        self.assertEqual(settings.mode_key, "banner")

    def test_file_title_used_when_cli_has_none(self):
        settings = configlib.resolve({"title": "来自配置"}, {})
        self.assertEqual(settings.design.title, "来自配置")

    def test_missing_title(self):
        with self.assertRaises(configlib.ConfigError):
            configlib.resolve({"preset": "cyber"}, {})

    def test_invalid_color(self):
        with self.assertRaises(configlib.ConfigError) as ctx:
            configlib.resolve({"title": "A", "colors": {"primary": "blue"}}, {})
        self.assertIn("十六进制", str(ctx.exception))

    def test_unknown_key_warns(self):
        settings = configlib.resolve({"title": "A", "nope": 1}, {})
        self.assertTrue(any("nope" in warning for warning in settings.warnings))

    def test_subtitle_accepts_string_and_list(self):
        one = configlib.resolve({"title": "A", "subtitle": "ONE LINE"}, {})
        two = configlib.resolve({"title": "A", "subtitle": ["A", "B"]}, {})
        self.assertEqual(one.design.subtitle, ["ONE LINE"])
        self.assertEqual(two.design.subtitle, ["A", "B"])

    def test_custom_size(self):
        settings = configlib.resolve({"title": "A", "size": "1200x900"}, {})
        self.assertEqual((settings.design.mode.width, settings.design.mode.height), (1200, 900))
        self.assertEqual(settings.design.mode.key, "custom")

    def test_bad_size(self):
        with self.assertRaises(configlib.ConfigError):
            configlib.resolve({"title": "A", "size": "wide"}, {})

    def test_describe_snapshot(self):
        snapshot = configlib.resolve({"title": "REA", "mode": "banner"}, {}).describe()
        self.assertEqual(snapshot["canvas"]["output"], [1280, 640])
        self.assertEqual(snapshot["content"]["title"], "REA")

    def test_example_configs_are_valid(self):
        for name in ("rea.jsonc", "og.jsonc"):
            path = os.path.join(ROOT, "examples", name)
            settings = configlib.resolve(jsonc.load(path), {})
            self.assertTrue(settings.design.title)


if __name__ == "__main__":
    unittest.main()
