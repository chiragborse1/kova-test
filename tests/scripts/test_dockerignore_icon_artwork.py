"""Every artwork file the icon generator reads must survive ``.dockerignore``.

The Docker ``icons`` stage builds with a context filtered by ``.dockerignore``,
which excludes ``assets/*`` and re-includes only the files the web icon prebuild
needs. Two of the four marks ``scripts/generate_icons.py`` composes from were not
re-included, so the stage built against an empty SVG:

    ValueError: `svg_string` is empty or `svg_path` contains empty invalid svg

This test reads the generator to find the paths it loads and asserts each one is
present in the build context. It derives the list instead of restating it, so
adding a mark variant cannot silently re-break the image build.
"""
from __future__ import annotations

import fnmatch
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCKERIGNORE = ROOT / ".dockerignore"
GENERATOR = ROOT / "scripts" / "generate_icons.py"


def _patterns() -> list[str]:
    return [
        line.strip()
        for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _excluded(relative: str, patterns: list[str]) -> bool:
    """Docker's rule: the last matching pattern wins, and ``!`` re-includes."""
    verdict = False
    for pattern in patterns:
        negated = pattern.startswith("!")
        cleaned = (pattern[1:] if negated else pattern).rstrip("/")
        if (
            fnmatch.fnmatch(relative, cleaned)
            or fnmatch.fnmatch(relative, cleaned + "/*")
            or relative.startswith(cleaned + "/")
        ):
            verdict = not negated
    return verdict


def _artwork_the_generator_reads() -> list[str]:
    """Paths under assets/ that generate_icons.py loads or names literally."""
    import re

    source = GENERATOR.read_text(encoding="utf-8")
    found: set[str] = set()

    # assets/icon-master*.svg are named in TARGETS and in the module docstring as
    # things the generator WRITES. They are not inputs, so they must not be
    # demanded from the build context. Match both spellings.
    outputs = set(re.findall(r'\("?assets/[\w./-]+\.[a-z]+"?', source))
    outputs |= {n for n in re.findall(r'assets/[\w./-]+\.svg', source)
                if n.startswith("assets/icon-master")}

    # Literal asset filenames in the source (backgrounds, squircle shapes).
    for name in re.findall(r'[\w./-]+\.svg', source):
        candidate = f"assets/{name}" if not name.startswith("assets/") else name
        if candidate in outputs:
            continue
        if (ROOT / candidate).is_file():
            found.add(candidate)

    # assets / "kova" / f"kova-mark-{color}.svg" -- the four mark variants.
    if 'assets / "kova"' in source or '"kova"' in source:
        for svg in sorted((ROOT / "assets" / "kova").glob("kova-mark-*.svg")):
            found.add(f"assets/kova/{svg.name}")

    return sorted(found)


def test_generator_artwork_exists_in_the_repository():
    artwork = _artwork_the_generator_reads()
    assert artwork, "no artwork discovered; the extraction is stale, not the tree"
    for relative in artwork:
        assert (ROOT / relative).is_file(), f"{relative} is referenced but missing"


@pytest.mark.parametrize("relative", _artwork_the_generator_reads())
def test_generator_artwork_survives_dockerignore(relative):
    patterns = _patterns()
    assert not _excluded(relative, patterns), (
        f"{relative} is excluded by .dockerignore but scripts/generate_icons.py "
        "reads it, so the Docker icons stage builds against an empty SVG"
    )