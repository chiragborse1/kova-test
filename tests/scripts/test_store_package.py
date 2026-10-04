"""The Store package is bound to the claim before Partner Center ever sees it."""
import json
import zipfile
from pathlib import Path

import pytest

from scripts.bundles.release_artifacts import (
    record_store,
    validate_store_bundle,
)

TAG = "v1.2.3"
COMMIT = "a" * 40
PUBLISHER = "CN=2F021361-3B6D-4856-9252-B417E78D18A"
IDENTITY = "5402NeuralStudio.KovaAgent"


def _manifest(arch, *, publisher=PUBLISHER, identity=IDENTITY, version="1.2.3.0"):
    return f"""<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10">
  <Identity Name="{identity}" ProcessorArchitecture="{arch}" Publisher="{publisher}" Version="{version}" />
  <Applications>
    <Application Id="KovaBundled" Executable="Kova.exe" EntryPoint="Windows.FullTrustApplication" />
  </Applications>
</Package>"""


def _stamp(commit=COMMIT, tag=TAG):
    return json.dumps({"schemaVersion": 1, "commit": commit, "tag": tag,
                       "baseVersion": tag.removeprefix("v"), "source": "ci"})


def _package(root, arch, *, filename=None, publisher=PUBLISHER, commit=COMMIT, tag=TAG):
    name = filename or f"Store-KovaBundled-{TAG[1:]}-win-{arch}.msix"
    path = Path(root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("AppxManifest.xml", _manifest(arch, publisher=publisher))
        archive.writestr("app/resources/install-stamp.json", _stamp(commit=commit, tag=tag))
    return path


def _bundle(root, arches=("x64", "arm64"), *, publisher=PUBLISHER, version="1.2.3.0"):
    packages = "".join(
        f'<Package Type="application" Architecture="{a}" />' for a in arches)
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<Bundle xmlns="http://schemas.microsoft.com/appx/2013/bundle">'
        f'<Identity Name="{IDENTITY}" Publisher="{publisher}" Version="{version}" />'
        f"<Packages>{packages}</Packages></Bundle>")
    path = Path(root) / f"Store-KovaBundled-{version}-win.msixbundle"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("AppxMetadata/AppxBundleManifest.xml", xml)
    return path


def _rows(root):
    out = []
    for arch in ("x64", "arm64"):
        target = Path(root) / f"store-metadata-{arch}.json"
        record_store(arch, Path(root), TAG, COMMIT, target)
        out.append(json.loads(target.read_text(encoding="utf-8")))
    return out


def test_record_store_reads_identity_and_provenance(tmp_path):
    _package(tmp_path, "x64")
    _package(tmp_path, "arm64")
    rows = _rows(tmp_path)
    assert [r["arch"] for r in rows] == ["x64", "arm64"]
    for row in rows:
        assert row["identity"] == IDENTITY
        assert row["publisher"] == PUBLISHER
        assert row["applicationId"] == "KovaBundled"
        assert row["tag"] == TAG and row["commit"] == COMMIT


def test_record_store_rejects_a_foreign_commit(tmp_path):
    _package(tmp_path, "x64")
    _package(tmp_path, "arm64", commit="b" * 40)
    with pytest.raises(ValueError, match="provenance"):
        record_store("arm64", tmp_path, TAG, COMMIT, tmp_path / "out.json")


def test_record_store_rejects_the_out_of_store_filename(tmp_path):
    _package(tmp_path, "x64")
    _package(tmp_path, "arm64", filename="KovaBundled-1.2.3-win-arm64.msix")
    with pytest.raises(ValueError, match="Expected exactly one artifact"):
        record_store("arm64", tmp_path, TAG, COMMIT, tmp_path / "out.json")


def test_validate_store_bundle_binds_both_architectures(tmp_path):
    _package(tmp_path, "x64")
    _package(tmp_path, "arm64")
    rows = _rows(tmp_path)
    bundle = _bundle(tmp_path)
    result = validate_store_bundle(bundle, rows, tag=TAG, commit=COMMIT, publisher=PUBLISHER)
    assert result["sha256"] and result["size"] > 0


def test_validate_store_bundle_rejects_a_single_architecture(tmp_path):
    _package(tmp_path, "x64")
    _package(tmp_path, "arm64")
    rows = _rows(tmp_path)
    bundle = _bundle(tmp_path, arches=("x64",))
    with pytest.raises(ValueError, match="both architectures|bundle must cover"):
        validate_store_bundle(bundle, rows, tag=TAG, commit=COMMIT)


def test_validate_store_bundle_rejects_a_foreign_publisher(tmp_path):
    _package(tmp_path, "x64")
    _package(tmp_path, "arm64")
    rows = _rows(tmp_path)
    bundle = _bundle(tmp_path)
    with pytest.raises(ValueError, match="Partner Center identity"):
        validate_store_bundle(bundle, rows, tag=TAG, commit=COMMIT,
                              publisher="CN=EE6D86E4-606F-4E38-B940-AD7248C9D519")


def test_validate_store_bundle_rejects_packages_that_disagree(tmp_path):
    _package(tmp_path, "x64")
    _package(tmp_path, "arm64")
    rows = _rows(tmp_path)
    rows[1]["version"] = "9.9.9.9"
    with pytest.raises(ValueError, match="disagree on version"):
        validate_store_bundle(_bundle(tmp_path), rows, tag=TAG, commit=COMMIT)


def _workflow(name):
    import yaml
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / ".github" / "workflows" / name
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def test_store_jobs_are_opt_in():
    """No Store build, verification or Partner Center contact without the flag.

    The Store jobs are the only path to Partner Center, so the opt-in has to
    gate the build itself -- not just the submission step -- or a default
    release would still build and verify a package it never sends.
    """
    desktop = _workflow("desktop-bundled-release.yml")
    on = desktop[True]
    assert on["workflow_call"]["inputs"]["submit-store"]["default"] is False
    assert "inputs.submit-store" in desktop["jobs"]["build-store-package"]["if"]
    assert "inputs.submit-store" in desktop["jobs"]["stable-store"]["if"]


def test_stable_release_threads_the_opt_in_to_both_store_calls():
    stable = _workflow("stable-release.yml")
    assert stable[True]["workflow_dispatch"]["inputs"]["submit-store"]["default"] is False
    for job in ("candidates-store", "publish-store"):
        entry = stable["jobs"][job]
        assert "inputs.submit-store" in entry["with"]["submit-store"]
        assert entry["with"]["jobs"] == "store"
    # publish-store only runs once candidates-store succeeded, and a skipped
    # candidate job never reports success -- so the default path submits nothing.
    assert "needs.candidates-store.result == 'success'" in stable["jobs"]["publish-store"]["if"]
