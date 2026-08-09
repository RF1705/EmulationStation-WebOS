#!/usr/bin/env python3
"""Inject repository theme overlays into a packaged Simple Dark ZIP."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


OPENTTD_WEBSITE_REVISION = "7a4d71998fa265c08221ef24019c5da00bddfc39"
OPENTTD_WEBSITE_RAW = (
    "https://raw.githubusercontent.com/OpenTTD/website/"
    f"{OPENTTD_WEBSITE_REVISION}"
)
OPENTTD_ASSETS = {
    "openttd-64.gif": f"{OPENTTD_WEBSITE_RAW}/static/img/layout/openttd-64.gif",
    "openttd-logo.png": f"{OPENTTD_WEBSITE_RAW}/static/img/layout/openttd-logo.png",
    "openttd-screenshot.png": (
        f"{OPENTTD_WEBSITE_RAW}/_screenshots/1.0-20081018_tom_storey.png"
    ),
}


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "EmulationStation-WebOS"})
    with urllib.request.urlopen(request, timeout=60) as response:
        destination.write_bytes(response.read())


def build_openttd_assets() -> dict[str, bytes]:
    """Build TV-sized theme artwork from assets used by the official OpenTTD site."""
    with tempfile.TemporaryDirectory(prefix="openttd-theme-") as temporary_name:
        temporary_path = Path(temporary_name)
        for filename, url in OPENTTD_ASSETS.items():
            download(url, temporary_path / filename)

        # Recreate the official website's #openttd-logo composition exactly:
        # 64 px logo mark at the left, 151x29 wordmark starting at x=78 and
        # four pixels above the bottom edge of the 250x68 logo area.
        logo_svg = temporary_path / "openttd-composite.svg"
        logo_png = temporary_path / "openttd.png"
        logo_svg.write_text(
            """<svg xmlns="http://www.w3.org/2000/svg" width="250" height="68" viewBox="0 0 250 68">
  <image href="openttd-64.gif" x="0" y="2" width="64" height="64"/>
  <image href="openttd-logo.png" x="78" y="35" width="151" height="29"/>
</svg>
""",
            encoding="utf-8",
        )
        subprocess.run(
            ["rsvg-convert", "-w", "500", "-h", "136", str(logo_svg), "-o", str(logo_png)],
            cwd=temporary_path,
            check=True,
        )

        # The official showcase screenshot is 1920x1200. Crop it to 16:9 for
        # televisions and add only a light darkening veil so the artwork stays
        # recognisable while carousel/help text remains readable.
        background_svg = temporary_path / "openttd-background.svg"
        background_png = temporary_path / "openttd_background.png"
        background_svg.write_text(
            """<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <image href="openttd-screenshot.png" x="0" y="0" width="1920" height="1080" preserveAspectRatio="xMidYMid slice"/>
  <rect x="0" y="0" width="1920" height="1080" fill="#000000" fill-opacity="0.18"/>
</svg>
""",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "rsvg-convert",
                "-w",
                "1920",
                "-h",
                "1080",
                str(background_svg),
                "-o",
                str(background_png),
            ],
            cwd=temporary_path,
            check=True,
        )

        return {
            "openttd/art/openttd.png": logo_png.read_bytes(),
            "openttd/art/openttd_background.png": background_png.read_bytes(),
        }


def add_overlay(archive_path: Path, overlay_path: Path) -> None:
    if not archive_path.is_file():
        raise SystemExit(f"Simple Dark archive not found: {archive_path}")
    if not overlay_path.is_dir():
        raise SystemExit(f"Simple Dark overlay not found: {overlay_path}")

    overlay_files = {
        path.relative_to(overlay_path).as_posix(): path.read_bytes()
        for path in overlay_path.rglob("*")
        if path.is_file()
    }
    if not overlay_files:
        raise SystemExit(f"Simple Dark overlay is empty: {overlay_path}")

    if "openttd/theme.xml" in overlay_files:
        # These were the temporary hand-made placeholders. Keep them out of the
        # package and generate the real artwork from official OpenTTD assets.
        overlay_files.pop("openttd/art/openttd.svg", None)
        overlay_files.pop("openttd/art/openttd_art_blur.svg", None)
        overlay_files.update(build_openttd_assets())

    fd, temporary_name = tempfile.mkstemp(
        prefix="simple-dark-overlay-", suffix=".zip", dir=archive_path.parent
    )
    os.close(fd)
    temporary_path = Path(temporary_name)

    try:
        with zipfile.ZipFile(archive_path, "r") as source:
            members = source.infolist()
            roots = [member.filename.split("/", 1)[0] for member in members if "/" in member.filename]
            if not roots:
                raise SystemExit("Simple Dark archive has no codeload root directory")
            prefix = roots[0] + "/"
            replaced = {prefix + relative for relative in overlay_files}

            with zipfile.ZipFile(
                temporary_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
            ) as destination:
                for member in members:
                    if member.filename in replaced:
                        continue
                    destination.writestr(member, b"" if member.is_dir() else source.read(member.filename))

                for relative, content in sorted(overlay_files.items()):
                    destination.writestr(prefix + relative, content)

        with zipfile.ZipFile(temporary_path, "r") as result:
            missing = sorted(replaced - set(result.namelist()))
            if missing:
                raise SystemExit("Simple Dark overlay is incomplete: " + ", ".join(missing))

        os.replace(temporary_path, archive_path)

        # resources/ is copied wholesale into the package before this runs.
        # Remove that build-only copy after its contents have been embedded in
        # simple-dark.zip, but never delete the repository's source overlay.
        packaged_overlay_root = archive_path.parents[1] / "theme-overlays"
        source_overlay_root = overlay_path.parent
        if (
            packaged_overlay_root.is_dir()
            and packaged_overlay_root.resolve() != source_overlay_root.resolve()
        ):
            shutil.rmtree(packaged_overlay_root)

        print(f"Added {len(overlay_files)} Simple Dark overlay files from {overlay_path}")
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} SIMPLE_DARK_ZIP OVERLAY_DIR", file=sys.stderr)
        return 2
    add_overlay(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
