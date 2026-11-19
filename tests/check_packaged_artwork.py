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
    for name in ("chrome", "viber", "telegram", "whatsapp", "browser", "files", "editor", "terminal"):
        icon = share / "kernova/welcome/icons" / f"{name}.svg"
        assert icon.read_bytes() == (source / "apps/welcome/icons" / icon.name).read_bytes()
        assert not QImageReader(str(icon)).read().isNull(), icon
    print("Verified ten packaged 4K photographs and eight application icons.")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
