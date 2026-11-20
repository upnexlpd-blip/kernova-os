"""Check that the built Debian packages contain the intended, decodable artwork."""
import json
from pathlib import Path
import sys

from PySide6.QtGui import QImageReader


def main(root):
    source = Path(__file__).resolve().parents[1]
    share = root / "usr/share"
    images = sorted((share / "wallpapers").glob("Kernova*/contents/images/3840x2160.jpg"))
    assert len(images) == 10, f"Expected ten KERNOVA photographs, found {len(images)}"
    for image in images:
        directory = image.parents[2]
        plugin = json.loads((directory / "metadata.json").read_bytes())["KPlugin"]
        assert plugin["Id"] == directory.name and plugin["Authors"] and plugin["Name[mk]"]
        assert image.read_bytes() == (source / "branding" / directory.name / "contents/images" / image.name).read_bytes()
        decoded = QImageReader(str(image)).read()
        assert (decoded.width(), decoded.height()) == (3840, 2160), image
    for name in ("chrome", "viber", "telegram", "whatsapp", "browser", "files", "editor", "terminal",
                 "codex", "claude", "cursor", "alpaca"):
        icon = share / "kernova/welcome/icons" / f"{name}.svg"
        assert icon.read_bytes() == (source / "apps/welcome/icons" / icon.name).read_bytes()
        assert not QImageReader(str(icon)).read().isNull(), icon
    ribbon = share / "kernova/welcome/icons/pro-ribbon.jpg"
    assert not QImageReader(str(ribbon)).read().isNull(), ribbon
    assert (share / "kernova/welcome/pro_comparison.py").is_file()
    print("Verified ten packaged 4K photographs, twelve application icons and the Pro comparison artwork.")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
