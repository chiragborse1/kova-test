"""The canonical shell must run tests and propagate a failing test's status."""
from pathlib import Path
import os
import subprocess
import sys

import pytest


@pytest.mark.platforms("posix")
def test_docker_ready_timeout_survives_the_hermetic_env(tmp_path):
    """KOVA_DOCKER_READY_TIMEOUT must reach pytest under `env -i`.

    run_tests.sh forwards a documented allowlist of test knobs into its
    hermetic environment. conftest.py reads KOVA_DOCKER_READY_TIMEOUT at
    import to size the docker cont-init budget, and docker.yml raises it for
    the emulated arm64 row -- but the knob was never on the allowlist, so
    `env -i` silently dropped it and every arm64 container was judged against
    the 30s native default (run 37123258798, 24 timeout failures).

    A missing allowlist entry is invisible: the suite still runs, and the
    only symptom is a timeout that reads like a hang.

    The inner test writes what it saw to a marker file instead of relying on
    the runner's summary wording. run_tests_parallel.py prints "1 tests
    passed" on a passing file (and only truncates it when the path is long),
    so matching that string couples the test to the runner's prose; the
    marker file is the observed fact, independent of how it is reported.
    """
    marker = tmp_path / "observed.txt"
    case = tmp_path / "test_docker_timeout_env.py"
    case.write_text(
        "import os\n"
        "from pathlib import Path\n"
        f"def test_env_survived():\n"
        f"    Path({str(marker)!r}).write_text("
        "os.environ.get('KOVA_DOCKER_READY_TIMEOUT', '<MISSING>'))\n",
        encoding="utf-8",
    )
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["bash", str(root / "scripts/run_tests.sh"), "-j", "1", str(case)],
        cwd=tmp_path, capture_output=True, text=True, timeout=180,
        env={**os.environ, "KOVA_PYTHON": sys.executable, "KOVA_TEST_FILE_RETRIES": "0",
             "KOVA_DOCKER_READY_TIMEOUT": "300"},
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert marker.exists(), f"inner test never ran; output was:\n{output}"
    assert marker.read_text(encoding="utf-8") == "300", (
        "pytest did not observe KOVA_DOCKER_READY_TIMEOUT=300; run_tests.sh's "
        f"TEST_ENV allowlist dropped it. Observed: "
        f"{marker.read_text(encoding='utf-8')!r}"
    )


def test_docker_ready_timeout_is_on_the_allowlist():
    """Guard the allowlist directly so the env test above cannot be the only guard.

    Cheap and text-only: if someone removes the entry without noticing the
    failure, this names the exact file and line to restore.
    """
    root = Path(__file__).resolve().parents[2]
    shell = (root / "scripts/run_tests.sh").read_text(encoding="utf-8")
    block = shell.split("TEST_ENV=()", 1)[1].split("; do", 1)[0]
    assert "KOVA_DOCKER_READY_TIMEOUT" in block, (
        "KOVA_DOCKER_READY_TIMEOUT is missing from run_tests.sh's TEST_ENV "
        "allowlist; tests/docker/conftest.py would silently fall back to 30s"
    )


@pytest.mark.platforms("posix")
def test_shell_runner_executes_tests_and_propagates_failure(tmp_path):
    case = tmp_path / "test_runner_canary.py"
    marker = tmp_path / "executed"
    case.write_text(
        "from pathlib import Path\nimport os\n"
        "def test_canary():\n"
        f"    Path({str(marker)!r}).write_text('executed')\n"
        "    assert os.environ['PATHEXT'] == '.COM;.EXE;.BAT;.CMD'\n"
        "    assert False, 'runner failure propagation canary'\n",
        encoding="utf-8",
    )
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["bash", str(root / "scripts/run_tests.sh"), "-j", "1", str(case)],
        cwd=tmp_path, capture_output=True, text=True, timeout=180,
        env={**os.environ, "KOVA_PYTHON": sys.executable, "KOVA_TEST_FILE_RETRIES": "0",
             "PATHEXT": ".COM;.EXE;.BAT;.CMD"},
    )
    assert marker.read_text(encoding="utf-8") == "executed", result.stdout + result.stderr
    assert result.returncode != 0, result.stdout + result.stderr
    assert "runner failure propagation canary" in result.stdout + result.stderr
