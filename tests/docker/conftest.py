"""Shared fixtures for docker-image integration tests.

Tests in this directory build the image with the current ``Dockerfile``
and exercise it via ``docker run``. They skip when Docker is unavailable
(e.g. on developer laptops without a daemon).

Override the image with ``KOVA_TEST_IMAGE`` env var to point at a pre-built
image (faster local iteration); otherwise the ``built_image`` fixture builds
the repo's Dockerfile once per session.

"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections.abc import Iterator

import pytest

IMAGE_TAG = os.environ.get("KOVA_TEST_IMAGE", "kova-agent-harness:latest")

# Readiness deadlines. A container's cont-init chain (UID remap, chown, config
# seeding, skills sync, browser discovery, config migration) is a fixed amount
# of work, but a fixed amount of work is measured in instructions -- and an
# arm64 image on an amd64 host runs every one of them through qemu at roughly
# 8x the cost. Measured on run 37027608034: the arm64 build took 40.4 min against
# amd64's 4.9. So 30s fits a native runner and cannot fit an emulated one; the
# first qemu run failed every readiness check with
#   TimeoutError: container ... did not finish cont-init within 30.0s
# and said nothing at all about the image. Overridable so the docker workflow
# can raise it for the emulated row only; amd64 keeps the tight default.
CONTAINER_READY_TIMEOUT_S = float(os.environ.get("KOVA_DOCKER_READY_TIMEOUT", "30"))

# Command deadlines scale with the same knob. Raising the readiness budget
# alone is not enough: the failures on the emulated row are not the
# `wait_for_container_ready` poll (which reads this constant) but the
# `subprocess.run(..., timeout=N)` deadline on each `docker run` / `docker exec`
# that boots or probes a container. Those literals are written for a native
# runner -- `docker run --rm <image> --help` is a 60s deadline natively and
# timed out on every arm64 leg of run 37201166208 (run 37123258798 had the same
# shape). Nothing reads the environment there, so raising KOVA_DOCKER_READY_TIMEOUT
# cannot reach them: amd64 stayed green purely because its native cost fits.
#
# So the ratio between the configured budget and the native default IS the
# emulation factor this host needs. Derive command deadlines from it rather
# than adding a second, independently-tunable knob that can drift from the
# first: 1.0 on a native runner (unchanged behaviour, byte-for-byte), and the
# qemu factor on the emulated row.
_NATIVE_READY_TIMEOUT_S = 30.0
EMULATION_FACTOR = CONTAINER_READY_TIMEOUT_S / _NATIVE_READY_TIMEOUT_S


def docker_timeout(native_seconds: float) -> float:
    """Deadline for one docker command, scaled by how slow this host is.

    ``native_seconds`` is the value the test would use on a native runner. On
    an emulated row the same command costs proportionally more wall clock, so
    the deadline scales with the same factor that sized the readiness budget.
    A caller that genuinely needs a different budget passes it explicitly and
    this is not involved.
    """
    return native_seconds * EMULATION_FACTOR


def _docker_available() -> bool:
    """Return True iff a docker CLI is on PATH and the daemon answers."""
    if shutil.which("docker") is None:
        return False
    try:
        r = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def pytest_collection_modifyitems(config, items):  # noqa: D401 - pytest hook
    """Apply docker-suite policy: timeout bump + skip on missing docker."""
    docker_ok = _docker_available()
    skip_docker = pytest.mark.skip(
        reason="Docker not available or daemon not running",
    )
    for item in items:
        if "tests/docker/" not in str(item.fspath).replace(os.sep, "/"):
            continue
        if not docker_ok:
            item.add_marker(skip_docker)


@pytest.fixture(scope="session")
def built_image() -> str:
    """Build the image once per test session.

    Override with ``KOVA_TEST_IMAGE`` env var to point at a pre-built
    image (faster local iteration).
    """
    if os.environ.get("KOVA_TEST_IMAGE"):
        return IMAGE_TAG
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", ".."),
    )
    result = subprocess.run(
        ["docker", "build", "-t", IMAGE_TAG, repo_root],
        capture_output=True, text=True, timeout=1200,
    )
    assert result.returncode == 0, (
        f"docker build failed:\n{result.stderr[-2000:]}"
    )
    return IMAGE_TAG


@pytest.fixture
def container_name(request) -> Iterator[str]:
    """Generate a unique container name and ensure cleanup on test exit."""
    safe = request.node.name.replace("[", "_").replace("]", "_")
    name = f"kova-test-{safe}"
    yield name
    subprocess.run(
        ["docker", "rm", "-f", name],
        capture_output=True, timeout=10,
    )


# ---------------------------------------------------------------------------
# docker_exec — default to the unprivileged kova user
# ---------------------------------------------------------------------------
#
# Background: every Kova runtime path inside the container drops to UID
# 10000 (the ``kova`` user) via ``s6-setuidgid kova``. ``docker exec``
# without ``-u`` runs as root, which is **not** representative of how
# production code executes. PR #30136 review caught a real regression
# this way — ``Path('/proc/1/exe').resolve()`` works as root and silently
# fails (PermissionError swallowed) for kova, so a test that ran as root
# couldn't catch a feature that was inert for the actual runtime user.
#
# Tests in this directory MUST exercise the realistic user context. The
# helpers below run every probe under ``-u kova`` unless a specific
# test explicitly opts into ``user="root"`` (rare — e.g. inspecting
# /proc/1/exe itself, chowning a volume).
# ---------------------------------------------------------------------------


def docker_exec(
    container: str,
    *args: str,
    user: str = "kova",
    timeout: float | None = None,
    extra_docker_args: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    """Run a command inside ``container`` as ``user`` (default: kova).

    Returns the CompletedProcess with text=True, capture_output=True.

    ``timeout`` defaults to the 30s native budget scaled by ``docker_timeout``
    -- 30s on a native runner, longer on an emulated one. Pass a value only when
    a specific probe needs a different budget; the default already tracks the
    host.

    Pass ``user="root"`` only when the test specifically needs root
    capabilities (e.g. reading /proc/1/exe, manipulating ownership).
    Most tests should use the default.
    """
    cmd = ["docker", "exec", "-u", user, *extra_docker_args, container, *args]
    return subprocess.run(
        cmd, capture_output=True, text=True,
        timeout=docker_timeout(30) if timeout is None else timeout,
    )


def docker_exec_sh(
    container: str,
    command: str,
    *,
    user: str = "kova",
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run ``sh -c <command>`` inside the container as ``user``.

    ``timeout`` is optional so the default tracks the host's emulation factor;
    an explicit value still wins.
    """
    return docker_exec(
        container, "sh", "-c", command, user=user, timeout=timeout,
    )


def docker_run(
    image: str,
    *args: str,
    timeout: float | None = None,
    run_args: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    """``docker run --rm <image> ...`` with a host-scaled deadline.

    Booting a container runs the whole cont-init chain before the command
    executes, so every one of these deadlines has to fit the emulated row too.
    The native value is what the test used to write literally; it is scaled by
    ``docker_timeout`` so the emulated row gets proportionally longer without a
    second knob to keep in sync. ``run_args`` carries flags that must precede
    the image (``--init``, ``--user``, ``-e``, ``-t``).
    """
    return subprocess.run(
        ["docker", "run", "--rm", *run_args, image, *args],
        capture_output=True, text=True,
        timeout=docker_timeout(60) if timeout is None else timeout,
    )


def wait_for_container_ready(
    container: str,
    *,
    deadline_s: float | None = None,
    interval_s: float = 0.25,
) -> None:
    """Poll until the container has finished s6 cont-init (stage2 + reconcile).

    The readiness signal is ``profile=default`` appearing in
    ``/opt/data/logs/container-boot.log``, which the 02-reconcile-profiles
    cont-init script writes on every boot. That log entry fires AFTER
    stage2-hook.sh completes, so by the time it appears the full
    cont-init chain (UID remap, chown, config seeding, skills sync,
    browser discovery, config migration) has run.

    Raises ``TimeoutError`` if the container never becomes ready — much
    better than a fixed ``time.sleep()`` that either wastes time on fast
    machines or flakes on slow ones.
    """
    # None means the configured default, so a caller that passes nothing gets
    # the environment's budget rather than a hardcoded one.
    # Name the budget that was actually used. Printing the raw `deadline_s`
    # printed "within Nones" for every caller that relies on the default, which
    # hid the very number anyone needs when an emulated (qemu) row times out.
    budget = CONTAINER_READY_TIMEOUT_S if deadline_s is None else deadline_s
    end = time.monotonic() + budget
    while time.monotonic() < end:
        r = docker_exec(
            container,
            "sh", "-c",
            "cat /opt/data/logs/container-boot.log 2>/dev/null",
            timeout=5,
        )
        if r.returncode == 0 and "profile=default" in r.stdout:
            return
        time.sleep(interval_s)
    # Two sources, and they must not be confused: the container's own boot log
    # from INSIDE it, and the daemon's view of the container from the runner.
    # An earlier version chained them with `||`, so when the boot log was absent
    # the in-container `docker logs` ran - there is no docker CLI or socket
    # inside the image, so it printed "Cannot connect to the Docker daemon at
    # unix:///var/run/docker.sock", which reads like the runner had lost its
    # daemon when it had not. Read them separately and label each.
    parts = []
    boot = docker_exec(
        container, "sh", "-c", "cat /opt/data/logs/container-boot.log 2>/dev/null", timeout=10)
    if (boot.stdout or "").strip():
        parts.append("container boot log:\n" + boot.stdout.strip()[-1500:])
    runner_logs = subprocess.run(
        ["docker", "logs", "--tail", "50", container],
        capture_output=True, text=True, timeout=30)
    host_out = (runner_logs.stdout or runner_logs.stderr or "").strip()
    if host_out:
        parts.append("docker logs (runner):\n" + host_out[-1500:])
    detail = "\n".join(parts)
    raise TimeoutError(
        f"container {container} did not finish cont-init within {budget}s"
        + (f"\ncontainer output:\n{detail}" if detail else "")
    )


def start_container(
    image: str,
    name: str,
    *env: str,
    cmd: str = "sleep infinity",
    timeout: float | None = None,
) -> str:
    """Start a detached container and wait for cont-init to finish.

    Args:
        image: Docker image to run.
        name: Container name (cleanup is the caller's responsibility —
            typically handled by the ``container_name`` fixture).
        env: Env vars as ``KEY=VALUE`` strings, each passed via ``-e``.
        cmd: Container CMD (default ``sleep infinity``).
        timeout: ``docker run`` subprocess timeout.

    Returns the container name. Raises on ``docker run`` failure or if
    the container never finishes cont-init within 30s.
    """
    args = ["docker", "run", "-d", "--name", name]
    for e in env:
        args.extend(["-e", e])
    args.extend([image, *cmd.split()])
    # `check=True` alone raises CalledProcessError with only the exit status.
    # Docker puts the reason on stderr - "no matching manifest", "exec format
    # error", "cannot connect to the daemon" - and losing it is what made the
    # arm64 rows report a bare `exit status 125` with nothing to act on.
    result = subprocess.run(args, capture_output=True, text=True,
                            timeout=docker_timeout(timeout or 30))
    if result.returncode:
        raise RuntimeError(
            f"docker run failed for {name} (exit {result.returncode}):\n"
            f"{(result.stderr or result.stdout or '<no output>')[-2000:]}"
        )
    wait_for_container_ready(name)
    return name


def restart_container(container: str, timeout: float | None = None) -> None:
    """Restart a container and wait for cont-init to finish.

    Equivalent to ``docker restart <container>`` followed by
    :func:`wait_for_container_ready`.

    The readiness signal (``profile=default`` in
    ``/opt/data/logs/container-boot.log``) is append-only and persists
    across restarts, so we truncate it BEFORE restarting — otherwise
    ``wait_for_container_ready`` would match the stale line from the
    previous boot and return before cont-init runs on the new boot.
    """
    docker_exec(container, "sh", "-c",
                "truncate -s 0 /opt/data/logs/container-boot.log 2>/dev/null || true",
                user="root", timeout=docker_timeout(5))
    subprocess.run(
        ["docker", "restart", container],
        check=True, capture_output=True, timeout=docker_timeout(timeout or 60),
    )
    wait_for_container_ready(container)


def poll_container(
    container: str,
    probe: str,
    *,
    deadline_s: float | None = None,
    interval_s: float = 0.5,
    user: str = "kova",
) -> tuple[bool, str]:
    """Repeatedly run ``probe`` inside the container until it exits 0 or
    ``deadline_s`` elapses.

    Returns ``(success, last_stdout)``. Useful for waiting on a process
    to appear, a port to open, a file to contain a string, etc.
    """
    # None means the configured default, so a caller that passes nothing gets
    # the environment's budget rather than a hardcoded one.
    end = time.monotonic() + (CONTAINER_READY_TIMEOUT_S if deadline_s is None else deadline_s)
    last = ""
    while time.monotonic() < end:
        r = docker_exec_sh(container, probe, user=user, timeout=10)
        last = r.stdout
        if r.returncode == 0:
            return True, last
        time.sleep(interval_s)
    return False, last


def wait_for_path(
    container: str,
    path: str,
    *,
    kind: str = "f",
    deadline_s: float | None = None,
    interval_s: float = 0.25,
) -> bool:
    """Poll ``test -<kind> <path>`` inside the container until success or timeout.

    ``kind`` is the ``test`` flag: ``'f'`` for file, ``'d'`` for directory,
    ``'e'`` for existence. Returns ``True`` on success, ``False`` on timeout.
    """
    return poll_container(
        container, f"test -{kind} {path}",
        deadline_s=deadline_s, interval_s=interval_s,
    )[0]


def wait_for_log(
    container: str,
    log_path: str,
    needle: str,
    *,
    deadline_s: float | None = None,
    interval_s: float = 0.25,
) -> str:
    """Poll until a log file inside the container contains ``needle``.

    Returns the full log on success.
    """
    # None means the configured default, so a caller that passes nothing gets
    # the environment's budget rather than a hardcoded one.
    end = time.monotonic() + (CONTAINER_READY_TIMEOUT_S if deadline_s is None else deadline_s)
    last = ""
    while time.monotonic() < end:
        r = docker_exec_sh(
            container, f"cat {log_path} 2>/dev/null", timeout=5,
        )
        if r.returncode == 0:
            last = r.stdout
            if needle in last:
                return last
        time.sleep(interval_s)
    raise AssertionError(f"Didn't see `{needle}` in {log_path} within {deadline_s} in container {container}")



def wait_for_docker_logs(
    container: str, needle: str, *, deadline_s: float = 30.0, interval_s: float = 0.5,
) -> str:
    """Poll ``docker logs`` until ``needle`` appears or deadline expires.

    Returns the full docker logs on success.
    """
    # None means the configured default, so a caller that passes nothing gets
    # the environment's budget rather than a hardcoded one.
    end = time.monotonic() + (CONTAINER_READY_TIMEOUT_S if deadline_s is None else deadline_s)
    last = ""
    while time.monotonic() < end:
        r = subprocess.run(
            ["docker", "logs", container],
            capture_output=True, text=True, timeout=10,
        )
        last = r.stdout + r.stderr
        if needle in last:
            return last
        time.sleep(interval_s)
    raise AssertionError(f"Didn't see `{needle}` in docker logs within {deadline_s} in container {container}")
