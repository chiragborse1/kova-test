"""Runtime qualification for SQLite in the published Docker image."""

from __future__ import annotations

import json
import subprocess


_SQLITE_PROBE = r"""
import json
import sqlite3

from kova_cli.sqlite_runtime import is_sqlite_wal_reset_vulnerable

db = sqlite3.connect(":memory:")
try:
    db.execute("CREATE VIRTUAL TABLE docs USING fts5(content, tokenize='trigram')")
    db.execute("INSERT INTO docs VALUES ('kova')")
    # 'ova' IS a trigram of 'kova' and must match; 'erm' is not a substring of
    # it and must not. Asserting a match for 'erm' (the previous version of
    # this probe) could never pass on any host -- the same wrong expectation
    # the Dockerfile's build-time self-test carried.
    substring_hits = db.execute(
        "SELECT count(*) FROM docs WHERE docs MATCH 'ova'"
    ).fetchone()[0]
    non_substring_hits = db.execute(
        "SELECT count(*) FROM docs WHERE docs MATCH 'erm'"
    ).fetchone()[0]
finally:
    db.close()

print(json.dumps({
    "sqlite_version": sqlite3.sqlite_version,
    "wal_reset_vulnerable": is_sqlite_wal_reset_vulnerable(
        sqlite3.sqlite_version_info
    ),
    "trigram_substring_hits": substring_hits,
    "trigram_non_substring_hits": non_substring_hits,
}))
"""


def test_image_links_fixed_sqlite_with_fts5_trigram(built_image: str) -> None:
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--user",
            "kova",
            "--entrypoint",
            "/opt/kova/.venv/bin/python",
            built_image,
            "-c",
            _SQLITE_PROBE,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"SQLite runtime probe failed: stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    payload = json.loads(result.stdout)
    assert payload["wal_reset_vulnerable"] is False, payload
    # Both directions: the tokenizer finds a real trigram, and is not matching
    # everything. One alone would pass a broken build that returns every row.
    assert payload["trigram_substring_hits"] == 1, payload
    assert payload["trigram_non_substring_hits"] == 0, payload
