#!/usr/bin/env python3
"""Bump the shared project version across VERSION, pyproject.toml and package.json.

Usage: scripts/bump_version.py {major|minor|patch|<explicit version>}
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
PYPROJECT_FILE = ROOT / "backend" / "pyproject.toml"
PACKAGE_JSON_FILE = ROOT / "frontend" / "package.json"

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def bump(current: str, part: str) -> str:
    match = SEMVER_RE.match(current)
    if not match:
        raise SystemExit(f"VERSION file does not contain a valid semver: {current!r}")
    major, minor, patch = (int(x) for x in match.groups())
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise SystemExit(f"Unknown bump part: {part!r}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    arg = sys.argv[1]

    current = VERSION_FILE.read_text().strip()
    new_version = bump(current, arg) if arg in {"major", "minor", "patch"} else arg
    if not SEMVER_RE.match(new_version):
        raise SystemExit(f"Not a valid semver: {new_version!r}")

    VERSION_FILE.write_text(f"{new_version}\n")

    pyproject = PYPROJECT_FILE.read_text()
    updated_pyproject, count = re.subn(
        r'^version = "[^"]+"$', f'version = "{new_version}"', pyproject, count=1, flags=re.MULTILINE,
    )
    if count != 1:
        raise SystemExit(f"Could not find a version field to update in {PYPROJECT_FILE}")
    PYPROJECT_FILE.write_text(updated_pyproject)

    package_json = PACKAGE_JSON_FILE.read_text()
    updated_package_json, count = re.subn(
        r'^(\s*)"version": "[^"]+",$', rf'\1"version": "{new_version}",', package_json, count=1, flags=re.MULTILINE,
    )
    if count != 1:
        raise SystemExit(f"Could not find a version field to update in {PACKAGE_JSON_FILE}")
    PACKAGE_JSON_FILE.write_text(updated_package_json)

    print(f"{current} -> {new_version}")


if __name__ == "__main__":
    main()
