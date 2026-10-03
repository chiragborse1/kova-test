"""The install-E2E tag picker must accept the tags this project actually makes.

``scripts/sandbox/pick-release-tags.sh`` is bash and runs before any Python
environment exists, so it cannot import ``kova_cli.update_channel.STABLE_TAG_RE``
and restates the rule. Its copy had drifted: it required a FOUR-digit major
(``^v[0-9]{4}\\.``, the old CalVer scheme), so after the move to 1.0.0 it matched
no tag this project makes and the "Pick release tags" workflow job failed with
"no release tags found" even though ``v1.0.0`` existed.

These tests pin the shell pattern to the Python authority, so the next version
scheme change cannot silently desynchronise the two.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from kova_cli.update_channel import STABLE_TAG_RE

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "sandbox" / "pick-release-tags.sh"
_PATTERN_LINE = re.compile(r"grep -E '(?P<pattern>\^v[^']*)'")


def _posix(path: Path) -> str:
    """This bash may be WSL, which cannot open a native Windows path; map the drive."""
    text = path.as_posix()
    return f"/mnt/{text[0].lower()}{text[2:]}" if text[1:3] == ":/" else text

def _shell_pattern() -> re.Pattern:
    match = _PATTERN_LINE.search(SCRIPT.read_text(encoding="utf-8-sig"))
    assert match, "the tag filter is no longer a single grep -E line; update this test"
    return re.compile(match.group("pattern"))


@pytest.mark.parametrize("tag", ["v1.0.0", "v1.0.43", "v0.21.5", "v10.20.30", "v0.0.1"])
def test_shell_pattern_accepts_real_release_tags(tag):
    assert _shell_pattern().fullmatch(tag), f"{tag} is a tag this project makes"


@pytest.mark.parametrize(
    "tag", ["v2026.4.8", "v1.0", "v1.0.0-rc1", "backup/x", "rc.11-v0.21.5", "hermes-agent-v1.0.0"],
)
def test_shell_pattern_rejects_non_release_tags(tag):
    assert not _shell_pattern().fullmatch(tag)


@pytest.mark.parametrize(
    "tag", ["v1.0.0", "v1.0.43", "v0.21.5", "v10.20.30", "v0.0.1",
            "v2026.4.8", "v1.0", "v1.0.0-rc1", "backup/x", "rc.11-v0.21.5"],
)
def test_shell_pattern_agrees_with_the_python_authority(tag):
    """The shell copy of the rule must decide exactly what STABLE_TAG_RE decides."""
    assert bool(_shell_pattern().fullmatch(tag)) == bool(STABLE_TAG_RE.match(tag))


@pytest.mark.skipif(not subprocess.run(["bash", "--version"], capture_output=True).returncode == 0,
                    reason="bash unavailable")
def test_picker_reports_a_release_tag_present_in_this_repo(tmp_path):
    """End to end: the repo's own v1.0.0 must survive the picker, not abort it."""
    result = subprocess.run(
        ["bash", _posix(SCRIPT), "--count", "5", "--repo", _posix(REPO_ROOT)],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert "v1.0.0" in result.stdout