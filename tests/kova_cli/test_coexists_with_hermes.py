"""Kova and an upstream Hermes install must be able to share one machine.

A rebrand that only changes what a product is CALLED leaves every name it
CLAIMS untouched, and those names are what collide: two installers writing one
config directory, two CLIs fighting over one command name, two scheduled
tasks, two app bundles with the same id. This pins the claimed identities so a
future rename cannot quietly reintroduce a collision - and so nobody has to
rediscover it by installing both.

What is asserted here is the identity Kova claims, not the identity upstream
happens to use: the point is that none of Kova's names are the ones a Hermes
install owns, and that they are internally consistent across every file that
has to agree.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tauri_conf() -> dict:
    # utf-8-sig: an editor on Windows can leave a BOM here, and a BOM is not a
    # product defect - it must not read as a broken identity.
    return json.loads(
        (ROOT / "apps" / "bootstrap-installer" / "src-tauri" / "tauri.conf.json")
        .read_text(encoding="utf-8-sig")
    )


def test_console_scripts_are_kova_scoped(pyproject):
    """`hermes` on PATH belongs to the other product. Kova claims only its own."""
    scripts = pyproject["project"]["scripts"]
    assert set(scripts) == {"kova", "kova-agent", "kova-acp"}
    for name, target in scripts.items():
        assert name.startswith("kova"), f"{name} does not name Kova"
        # The entry module must be Kova's too, or `kova` would run Hermes' code.
        assert target.split(".")[0] in {"kova_cli", "agent", "acp_adapter"}, target


def test_distribution_name_is_kova_scoped(pyproject):
    name = pyproject["project"]["name"]
    assert name == "kova-agent"
    assert "hermes" not in name.lower()
    assert "nous" not in name.lower()


def test_config_home_is_not_the_hermes_home():
    """The one thing that genuinely destroys data when two installs share it."""
    from kova_constants import get_kova_home

    home = Path(get_kova_home())
    assert home.name.lower() not in {"hermes", "hermesagent"}
    assert ".hermes" not in str(home).replace("\\", "/")


def test_hermes_home_env_var_is_not_read():
    """Kova must not adopt Hermes' override, or KOVA_HOME would be ignored."""
    from kova_constants import get_kova_home

    import os

    previous = os.environ.get("HERMES_HOME")
    os.environ["HERMES_HOME"] = str(ROOT / "_should_never_be_used")
    try:
        home = Path(get_kova_home())
        assert "should_never_be_used" not in str(home)
    finally:
        if previous is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = previous


def test_installer_bundle_id_is_kova_scoped(tauri_conf):
    identifier = tauri_conf["identifier"]
    assert identifier == "com.openkova.kova.setup"
    for other in ("nousresearch", "hermes"):
        assert other not in identifier.lower()


def test_installer_publisher_is_kova_scoped(tauri_conf):
    """Apps & Features and the signing identity both key off publisher."""
    assert tauri_conf["bundle"]["publisher"] == "Neural Studios"
    assert "Nous" not in tauri_conf["bundle"]["copyright"]


def test_cargo_authors_are_kova_scoped():
    cargo = (ROOT / "apps" / "bootstrap-installer" / "src-tauri" / "Cargo.toml").read_text(
        encoding="utf-8"
    )
    authors = re.search(r"^authors\s*=\s*(.+)$", cargo, re.M)
    assert authors, "Cargo.toml has no authors"
    assert "Nous" not in authors.group(1)


def test_no_product_code_claims_a_hermes_path():
    """No shipped module may reference Hermes' on-disk names.

    Prose, docs links and test fixtures are excluded deliberately: a comment
    naming the upstream project is attribution, a path would be a collision.
    """
    offenders: list[str] = []
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT)
        if rel.parts[0] in {"tests", "evals", "node_modules", ".venv", "_regression", "_salvage"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("*"):
                continue
            if re.search(r"HermesAgent|HERMES_HOME|\\.hermes\b", line):
                offenders.append(f"{rel}:{lineno}")
    assert not offenders, "product code still claims a Hermes path: " + ", ".join(offenders)
