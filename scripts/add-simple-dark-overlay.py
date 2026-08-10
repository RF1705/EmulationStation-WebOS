#!/usr/bin/env python3
"""Inject repository theme overlays into a packaged Simple Dark ZIP."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


def add_overlay(archive_path: Path, overlay_path: Path) -> None:
    if not archive_path.is_file():
        raise SystemExit(f"Simple Dark archive not found: {archive_path}")
    if not overlay_path.is_dir():
        raise SystemExit(f"Simple Dark overlay not found: {overlay_path}")

    overlay_files = {
        path.relative_to(overlay_path).as_posix(): path
        for path in overlay_path.rglob("*")
        if path.is_file()
    }
    if not overlay_files:
        raise SystemExit(f"Simple Dark overlay is empty: {overlay_path}")

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

                for relative, source_file in sorted(overlay_files.items()):
                    destination.writestr(prefix + relative, source_file.read_bytes())

        with zipfile.ZipFile(temporary_path, "r") as result:
            missing = sorted(replaced - set(result.namelist()))
            if missing:
                raise SystemExit("Simple Dark overlay is incomplete: " + ", ".join(missing))

        os.replace(temporary_path, archive_path)

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
