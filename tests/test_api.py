"""Python API 测试。"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import pixellogo  # noqa: E402
from pixellogo import config as configlib  # noqa: E402


class TestSceneApi(unittest.TestCase):
    def test_make_scene_returns_geometry(self):
        scene = pixellogo.make_scene(title="REA", mode="square")
        self.assertEqual((scene.width, scene.height), (540, 540))
        self.assertTrue(scene.rects)

    def test_make_image_is_scaled_bitmap(self):
        image = pixellogo.make_image(title="REA", mode="banner", scale=1)
        self.assertEqual(image.size, (640, 320))
        image2 = pixellogo.make_image(title="REA", mode="banner")
        self.assertEqual(image2.size, (1280, 640))

    def test_to_svg_text(self):
        content = pixellogo.to_svg_text(title="REA", mode="banner")
        self.assertTrue(content.startswith("<svg"))
        self.assertIn('shape-rendering="crispEdges"', content)

    def test_options_mirror_config_schema(self):
        scene = pixellogo.make_scene(
            title="REA",
            mode="poster",
            preset="cyber",
            subtitle=["LINE"],
            colors={"primary": "#FF3D81"},
            layout={"align": "left", "divider": "dash"},
        )
        self.assertIn("#FF3D81", scene.colors)
        self.assertIn("#0D1117", scene.colors)


class TestRenderApi(unittest.TestCase):
    def test_render_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = pixellogo.render(title="REA", mode="banner", format="png", out=tmp)
            self.assertEqual(len(paths), 1)
            self.assertTrue(paths[0].is_file())
            self.assertEqual(paths[0].suffix, ".png")

    def test_render_both_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = pixellogo.render(title="REA", mode="banner", format="both", out=tmp)
            self.assertEqual({p.suffix for p in paths}, {".png", ".svg"})

    def test_render_to_explicit_path(self):
        # 显式路径决定文件主干，format 决定扩展名
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "cover.png")
            paths = pixellogo.render(title="REA", mode="banner", format="both", out=target)
            self.assertEqual(sorted(p.name for p in paths), ["cover.png", "cover.svg"])

            only_svg = pixellogo.render(title="REA", mode="banner", format="svg", out=target)
            self.assertEqual([p.name for p in only_svg], ["cover.svg"])

    def test_render_many(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = pixellogo.render_many(
                [
                    {"title": "A", "mode": "banner"},
                    {"title": "B", "mode": "square"},
                ],
                out=tmp,
                format="png",
            )
            self.assertEqual(len(results), 2)
            self.assertEqual(len(os.listdir(tmp)), 2)

    def test_missing_title_raises(self):
        with self.assertRaises(configlib.ConfigError):
            pixellogo.make_scene(mode="banner")


if __name__ == "__main__":
    unittest.main()
