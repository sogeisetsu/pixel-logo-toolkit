"""画廊数据流水线测试：Markdown 改动必须能落到页面数据上。"""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

SPEC = importlib.util.spec_from_file_location(
    "gallery_site", os.path.join(ROOT, "tools", "gallery_site.py"))
gallery_site = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gallery_site)


def load():
    with open(gallery_site.DOC, encoding="utf-8") as handle:
        return gallery_site.parse_markdown(handle.read())


class TestGalleryData(unittest.TestCase):
    def setUp(self):
        self.data = load()
        self.items = [item for sec in self.data["sections"] for item in sec["items"]]

    def test_every_image_is_catalogued(self):
        on_disk = sorted(name for name in os.listdir(os.path.join(ROOT, "docs", "images", "gallery"))
                         if name.endswith(".png"))
        listed = sorted(os.path.basename(item["image"]) for item in self.items)
        self.assertEqual(on_disk, listed)

    def test_images_and_commands_are_consistent(self):
        self.assertEqual(gallery_site.validate(self.data), [])

    def test_sections_are_translated(self):
        for sec in self.data["sections"]:
            self.assertTrue(sec["zh"], sec)
            self.assertTrue(sec["en"], sec)
            self.assertNotEqual(sec["zh"], sec["en"])

    def test_items_have_english_notes(self):
        missing = [item["title"] for item in self.items if not item["noteEn"]]
        self.assertEqual(missing, [])

    def test_command_metadata_matches_image_name(self):
        for item in self.items:
            self.assertEqual(os.path.basename(item["out"].replace("\\", "/")),
                             os.path.basename(item["image"]), item["image"])
            self.assertIn(item["canvas"], ("poster", "card", "banner", "slide", "square", "custom"))

    def test_timeline_is_newest_first(self):
        dates = [entry["date"] for entry in self.data["timeline"]]
        self.assertEqual(dates, sorted(dates, reverse=True))
        for entry in self.data["timeline"]:
            self.assertTrue(entry["zh"])
            self.assertTrue(entry["en"])

    def test_bundle_serialises(self):
        source = gallery_site.build_js(self.data)
        self.assertIn("window.GALLERY_DATA", source)
        self.assertIn("\"sections\"", source)


if __name__ == "__main__":
    unittest.main()
