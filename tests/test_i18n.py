"""输出语言（i18n）测试：解析顺序、文案完整性、argparse 报错本地化。"""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from pixellogo import i18n  # noqa: E402

LOCALE_VARS = ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE")


class LanguageEnvMixin(unittest.TestCase):
    """隔离语言相关的环境变量与缓存。"""

    def setUp(self):
        self._saved = {name: os.environ.get(name) for name in LOCALE_VARS + (i18n.ENV_VAR,)}
        for name in LOCALE_VARS + (i18n.ENV_VAR,):
            os.environ.pop(name, None)
        i18n.reset()

    def tearDown(self):
        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        i18n.reset()


class TestNormalize(unittest.TestCase):
    def test_accepts_common_spellings(self):
        for value in ("en", "EN", "en-US", "en_us", "english"):
            self.assertEqual(i18n.normalize(value), "en", value)
        for value in ("zh", "zh-CN", "zh_cn", "zh-Hans", "zh-TW", "chinese", "cn"):
            self.assertEqual(i18n.normalize(value), "zh", value)

    def test_unknown_returns_none(self):
        for value in ("fr", "de-DE", "", None):
            self.assertIsNone(i18n.normalize(value), value)


class TestDetect(LanguageEnvMixin):
    def test_defaults_to_english_without_any_hint(self):
        if os.name == "nt":  # Windows 会读系统界面语言，这里不强行断言
            self.assertIn(i18n.detect(), i18n.SUPPORTED)
        else:
            self.assertEqual(i18n.detect(), "en")

    def test_locale_variables(self):
        os.environ["LANG"] = "zh_CN.UTF-8"
        self.assertEqual(i18n.detect(), "zh")
        os.environ["LANG"] = "en_US.UTF-8"
        self.assertEqual(i18n.detect(), "en")

    def test_lc_all_wins_over_lang(self):
        os.environ["LANG"] = "zh_CN.UTF-8"
        os.environ["LC_ALL"] = "en_US.UTF-8"
        self.assertEqual(i18n.detect(), "en")

    def test_posix_locale_means_english(self):
        for value in ("C", "POSIX", "C.UTF-8", "POSIX.UTF-8"):
            os.environ["LANG"] = value
            self.assertEqual(i18n.detect(), "en", value)

    def test_c_locale_beats_chinese_lang(self):
        os.environ["LC_ALL"] = "C.UTF-8"
        os.environ["LANG"] = "zh_CN.UTF-8"
        self.assertEqual(i18n.detect(), "en")

    def test_env_var_beats_locale(self):
        os.environ["LANG"] = "en_US.UTF-8"
        os.environ[i18n.ENV_VAR] = "zh"
        self.assertEqual(i18n.detect(), "zh")

    def test_env_var_auto_falls_back_to_locale(self):
        os.environ["LANG"] = "zh_CN.UTF-8"
        os.environ[i18n.ENV_VAR] = "auto"
        self.assertEqual(i18n.detect(), "zh")

    def test_language_list_format(self):
        os.environ["LANGUAGE"] = "zh_CN:en_US"
        self.assertEqual(i18n.detect(), "zh")


class TestSetLanguage(LanguageEnvMixin):
    def test_explicit_and_auto(self):
        self.assertEqual(i18n.set_language("en"), "en")
        self.assertEqual(i18n.get_language(), "en")
        os.environ["LANG"] = "zh_CN.UTF-8"
        self.assertEqual(i18n.set_language("auto"), "zh")
        self.assertEqual(i18n.get_language(), "zh")

    def test_invalid_value_raises(self):
        with self.assertRaises(ValueError):
            i18n.set_language("fr")

    def test_reset_redetects(self):
        i18n.set_language("zh")
        os.environ["LANG"] = "en_US.UTF-8"
        i18n.reset()
        self.assertEqual(i18n.get_language(), "en")


class TestCatalog(LanguageEnvMixin):
    def test_both_languages_cover_the_same_keys(self):
        self.assertEqual(set(i18n.MESSAGES["en"]), set(i18n.MESSAGES["zh"]))

    def test_supported_languages_are_present(self):
        self.assertEqual(set(i18n.SUPPORTED), set(i18n.MESSAGES))

    def test_translation_switches_with_language(self):
        i18n.set_language("en")
        self.assertEqual(i18n.t("mode.poster"), "Portrait poster (Xiaohongshu cover)")
        i18n.set_language("zh")
        self.assertEqual(i18n.t("mode.poster"), "竖版海报（小红书封面）")

    def test_placeholders_are_filled(self):
        i18n.set_language("en")
        text = i18n.t("config.range", name="scale", low=1, high=8)
        self.assertIn("scale", text)
        self.assertIn("1", text)
        self.assertIn("8", text)

    def test_unknown_key_falls_back_to_the_key(self):
        i18n.set_language("en")
        self.assertEqual(i18n.t("no.such.key"), "no.such.key")

    def test_missing_translation_falls_back_to_english(self):
        i18n.set_language("zh")
        original = i18n.MESSAGES["zh"].pop("mode.square")
        try:
            self.assertEqual(i18n.t("mode.square"), "Square image (social avatar / grid)")
        finally:
            i18n.MESSAGES["zh"]["mode.square"] = original

    def test_join_uses_language_separator(self):
        i18n.set_language("zh")
        self.assertEqual(i18n.join(["a", "b"]), "a、b")
        i18n.set_language("en")
        self.assertEqual(i18n.join(["a", "b"]), "a, b")

    def test_display_width_and_padding(self):
        self.assertEqual(i18n.display_width("海报"), 4)
        self.assertEqual(i18n.display_width("ab"), 2)
        self.assertEqual(i18n.pad("海报", 6), "海报  ")


class TestArgparseTranslation(LanguageEnvMixin):
    def test_english_is_untouched(self):
        i18n.set_language("en")
        raw = "unrecognized arguments: foo"
        self.assertEqual(i18n.translate_argparse_error(raw), raw)

    def test_common_messages_are_localized(self):
        i18n.set_language("zh")
        cases = [
            "unrecognized arguments: foo",
            "the following arguments are required: -t/--title",
            "argument -f/--format: expected one argument",
            "argument --ui-lang: invalid choice: 'fr' (choose from 'auto', 'en', 'zh')",
        ]
        for raw in cases:
            translated = i18n.translate_argparse_error(raw)
            self.assertNotEqual(translated, raw, raw)
            self.assertTrue(any("\u4e00" <= char <= "\u9fff" for char in translated), raw)

    def test_unknown_message_keeps_original_text(self):
        i18n.set_language("zh")
        raw = "something argparse invented later"
        self.assertEqual(i18n.translate_argparse_error(raw), raw)


def run_cli(*args, env_extra=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC + os.pathsep + env.get("PYTHONPATH", "")
    for name in LOCALE_VARS + (i18n.ENV_VAR,):
        env.pop(name, None)
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, "-m", "pixellogo", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=180,
    )


class TestCliLanguageSwitch(unittest.TestCase):
    """端到端：命令行参数与环境变量如何影响实际输出。"""

    def test_auto_follows_chinese_locale(self):
        result = run_cli("--list", "modes", env_extra={"LANG": "zh_CN.UTF-8"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("竖版海报", result.stdout)

    def test_auto_follows_english_locale(self):
        result = run_cli("--list", "modes", env_extra={"LANG": "en_US.UTF-8"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Portrait poster", result.stdout)
        self.assertNotIn("竖版海报", result.stdout)

    def test_env_var_switches_language(self):
        result = run_cli("--list", "presets", env_extra={"PIXELLOGO_UI_LANG": "en"})
        self.assertIn("Neon cyber", result.stdout)

    def test_flag_beats_env_and_locale(self):
        result = run_cli("--ui-lang", "en", "--list", "modes",
                         env_extra={"PIXELLOGO_UI_LANG": "zh", "LANG": "zh_CN.UTF-8"})
        self.assertIn("Portrait poster", result.stdout)

    def test_help_page_follows_language(self):
        english = run_cli("--ui-lang", "en", "--help", env_extra={"LANG": "zh_CN.UTF-8"})
        self.assertIn("Common examples", english.stdout)
        self.assertIn("show this help and exit", english.stdout)
        chinese = run_cli("--ui-lang", "zh", "--help")
        self.assertIn("常用示例", chinese.stdout)
        self.assertIn("显示本帮助并退出", chinese.stdout)

    def test_fonts_subcommand_is_localized(self):
        english = run_cli("--ui-lang", "en", "fonts")
        self.assertIn("Font directory", english.stdout)
        chinese = run_cli("--ui-lang", "zh", "fonts")
        self.assertIn("字体目录", chinese.stdout)

    def test_error_messages_are_localized(self):
        english = run_cli("--ui-lang", "en", "-t", "X", "-p", "nope")
        self.assertEqual(english.returncode, 2)
        self.assertIn("unknown style preset", english.stderr)
        chinese = run_cli("--ui-lang", "zh", "-t", "X", "-p", "nope")
        self.assertEqual(chinese.returncode, 2)
        self.assertIn("未知风格预设", chinese.stderr)

    def test_invalid_ui_lang_is_rejected(self):
        result = run_cli("--ui-lang", "fr")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--ui-lang", result.stderr)

    def test_ui_lang_before_subcommand(self):
        result = run_cli("--ui-lang", "en", "help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Common examples", result.stdout)


if __name__ == "__main__":
    unittest.main()
