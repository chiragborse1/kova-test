"""uv.lock must record the project's own version, exactly as pyproject states it.

`uv sync --locked` refuses a lock that disagrees with the manifest, and the
error it emits names a transitive dependency rather than the real cause. The
`v1.0.0` tag shipped `uv.lock` recording `kova-agent 0.0.0` while its
`pyproject.toml` said `1.0.0`, so every upgrade-E2E leg that installs from that
release failed with:

    error: Since the package `kittentts==0.8.1 @ direct+https://...` comes from
    a direct dependency, a hash was expected but one was not found for wheel

No CI job ran `uv lock --check`, so the inconsistency shipped silently and was
only found by dispatching a release workflow.

Verified directly: on `v1.0.0`, `uv lock --check` exits 2; changing that single
`version = "0.0.0"` line to `"1.0.0"` makes it exit 0, and a full
`uv sync --locked --extra all` then succeeds.

The project name/version is plain data in both files, so this compares them
directly rather than shelling out to uv -- the check is exact, needs no
network, and cannot itself be skipped by a resolver quirk.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
UV_LOCK = ROOT / "uv.lock"

# [[package]] blocks that describe the project itself are `source = { editable }`.
_PROJECT_BLOCK = re.compile(
    r'\[\[package\]\]\nname = "(?P<name>[^"]+)"\nversion = "(?P<version>[^"]+)"\n'
    r'source = \{ editable = "\." \}',
)


def _project() -> dict[str, str]:
    with PYPROJECT.open("rb") as handle:
        project = tomllib.load(handle)["project"]
    return {"name": project["name"], "version": project["version"]}


def _locked() -> dict[str, str]:
    text = UV_LOCK.read_text(encoding="utf-8-sig")
    blocks = list(_PROJECT_BLOCK.finditer(text))
    assert len(blocks) == 1, (
        f"expected exactly one editable self-package in uv.lock, found {len(blocks)}"
    )
    return {"name": blocks[0].group("name"), "version": blocks[0].group("version")}


def test_lock_records_the_project_name():
    assert _locked()["name"] == _project()["name"]


def test_lock_records_the_project_version():
    """The defect this exists for: the lock drifted to 0.0.0 and nothing caught it."""
    locked, declared = _locked()["version"], _project()["version"]
    assert locked == declared, (
        f"uv.lock records {locked!r} but pyproject.toml declares {declared!r}. "
        "`uv sync --locked` will fail, and it blames a transitive dependency "
        "rather than this mismatch. Refresh the lock: uv lock"
    )


@pytest.mark.parametrize("field", ["name", "version"])
def test_lock_and_manifest_agree(field):
    assert _locked()[field] == _project()[field]