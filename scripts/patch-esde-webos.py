#!/usr/bin/env python3
"""Apply small, idempotent webOS build adjustments to an ES-DE checkout."""
from __future__ import annotations
import argparse
from pathlib import Path

def replace_once(path: Path, old: str, new: str, marker: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    if old not in text:
        raise RuntimeError(f"Expected text not found in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    cmake = source / "CMakeLists.txt"
    if not cmake.is_file():
        raise SystemExit(f"ES-DE CMakeLists.txt not found below {source}")

    option_anchor = 'option(DEINIT_ON_LAUNCH "Set to ON to deinitialize on game launch" OFF)'
    replace_once(
        cmake,
        option_anchor,
        option_anchor + '\noption(WEBOS "Set to ON when targeting LG webOS" OFF) # webOS port',
        'option(WEBOS "Set to ON when targeting LG webOS" OFF)',
    )

    project_anchor = "project(es-de)"
    replace_once(
        cmake,
        project_anchor,
        project_anchor + "\n\nif(WEBOS)\n    add_compile_definitions(WEBOS)\n    message(STATUS \"-- Building for LG webOS\")\nendif() # webOS port",
        "-- Building for LG webOS",
    )
    print(f"Applied webOS build adjustments to {source}")

if __name__ == "__main__":
    main()
