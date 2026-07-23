"""Fail the release if the version is not declared consistently.

portcullis states its version in two places -- pyproject.toml and
src/portcullis/__init__.py -- and a release is additionally named by its git
tag. Publishing to PyPI is irreversible: a version number can never be reused,
even after a file is deleted. So this runs before the build, not after, and it
is deliberately strict about all three agreeing.

Run it locally the same way CI does:

    python .github/scripts/check_version.py            # files only
    python .github/scripts/check_version.py v0.1.0     # files + tag
"""

from __future__ import annotations

import pathlib
import re
import sys

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - only on 3.10
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = pathlib.Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
INIT = ROOT / "src" / "portcullis" / "__init__.py"


def pyproject_version() -> str:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return data["project"]["version"]


def dunder_version() -> str:
    match = re.search(
        r'^__version__\s*=\s*["\']([^"\']+)["\']',
        INIT.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if match is None:
        sys.exit(f"error: no __version__ assignment found in {INIT}")
    return match.group(1)


def main() -> None:
    declared = pyproject_version()
    dunder = dunder_version()

    problems: list[str] = []
    if declared != dunder:
        problems.append(
            f"pyproject.toml says {declared!r} but "
            f"src/portcullis/__init__.py says {dunder!r}"
        )

    if len(sys.argv) > 1:
        tag = sys.argv[1]
        tag_version = tag[1:] if tag.startswith("v") else tag
        if tag_version != declared:
            problems.append(
                f"git tag {tag!r} implies version {tag_version!r} "
                f"but pyproject.toml says {declared!r}"
            )

    if problems:
        print("Version declarations disagree:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(
            "\nPyPI never lets a version be reused, so this stops before the "
            "build rather than after the upload.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(f"version OK: {declared}")


if __name__ == "__main__":
    main()
