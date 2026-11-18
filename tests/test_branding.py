"""Cross-file Plasma theme and color contrast regressions, runnable off Linux."""
from configparser import ConfigParser
import json
from pathlib import Path
import unittest
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
BRANDING = ROOT / "branding"


def relative_luminance(value):
    channels = [int(n) / 255 for n in value.split(",")]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
    return sum(weight * component for weight, component in zip((0.2126, 0.7152, 0.0722), linear))


class BrandingTests(unittest.TestCase):
    def test_new_account_theme_resolves_to_palette_and_wallpaper(self):
        skel = ConfigParser()
        skel.read(ROOT / "packages/defaults/kdeglobals")
        theme = BRANDING / skel["KDE"]["LookAndFeelPackage"]
        metadata = json.loads((theme / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["KPackageStructure"], "Plasma/LookAndFeel")
        self.assertEqual(metadata["KPlugin"]["Id"], theme.name)
        settings = ConfigParser()
        settings.read(theme / "contents/defaults")
        colors = settings["kdeglobals][General"]["ColorScheme"]
        self.assertTrue((BRANDING / f"{colors}.colors").is_file())
        wall = BRANDING / settings["Wallpaper"]["Image"]
        wall_info = json.loads((wall / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(wall_info["KPlugin"]["Id"], wall.name)
        self.assertEqual(wall_info["KPackageStructure"], "Wallpaper/Images")
        art = ElementTree.parse(wall / "parallax.svg").getroot()
        self.assertEqual((art.attrib["width"], art.attrib["height"]), ("3840", "2160"))

    def test_text_and_focus_contrast_on_each_normal_and_alternate_surface(self):
        scheme = ConfigParser()
        scheme.read(BRANDING / "KernovaNight.colors", encoding="utf-8")
        backgrounds = ("BackgroundNormal", "BackgroundAlternate")
        for group in (name for name in scheme if name.startswith("Colors:")):
            for foreground, minimum in (("ForegroundNormal", 4.5), ("ForegroundInactive", 4.5),
                                        ("ForegroundLink", 4.5), ("DecorationFocus", 3.0)):
                for background in backgrounds:
                    with self.subTest(group=group, foreground=foreground, background=background):
                        pair = (scheme[group][foreground], scheme[group][background])
                        dark, bright = sorted(map(relative_luminance, pair))
                        self.assertGreaterEqual((bright + 0.05) / (dark + 0.05), minimum)

    def test_launcher_icon_exists_and_is_scalable(self):
        launcher = ConfigParser(interpolation=None)
        launcher.read(ROOT / "apps/integration/kernova-welcome.desktop", encoding="utf-8")
        icon = ElementTree.parse(BRANDING / (launcher["Desktop Entry"]["Icon"] + ".svg")).getroot()
        self.assertEqual(icon.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertTrue(icon.attrib.get("viewBox"))


if __name__ == "__main__":
    unittest.main()
