"""The channel archive origin must be a host that exists, and overridable.

``kova-assets.nousresearch.com`` is NXDOMAIN. While it was hardcoded, every
channel read raised ``ChannelError("Channel read unavailable")``, which the
updater surfaced as the release-unavailable banner, so the Desktop could never
check for updates. These tests pin the two properties that fix depends on: the
default origin resolves, and a real mirror wins over it.
"""
import socket
from urllib.parse import urlsplit

import pytest

from kova_cli import source_releases


def _resolves(url: str) -> bool:
    try:
        socket.getaddrinfo(urlsplit(url).hostname, 443)
    except OSError:
        return False
    return True


def test_default_public_base_host_exists():
    """A hardcoded default is the last resort; an NXDOMAIN one fails everything."""
    assert _resolves(source_releases._PUBLIC_BASE), (
        f"{source_releases._PUBLIC_BASE} does not resolve; every channel read fails closed")


def test_public_base_prefers_the_configured_origin(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_R2_PUBLIC_URL", "https://mirror.example/bucket")
    assert source_releases._public_base() == "https://mirror.example/bucket"


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_override_falls_back_to_the_default(monkeypatch, value):
    monkeypatch.setenv("CLOUDFLARE_R2_PUBLIC_URL", value)
    assert source_releases._public_base() == source_releases._PUBLIC_BASE


def test_public_base_is_read_per_call(monkeypatch):
    """A value baked in at import time would ignore a mirror configured later."""
    assert source_releases._public_base() == source_releases._PUBLIC_BASE
    monkeypatch.setenv("CLOUDFLARE_R2_PUBLIC_URL", "https://late.example/root")
    assert source_releases._public_base() == "https://late.example/root"


@pytest.mark.real_release_channels
def test_unreachable_host_fails_closed(monkeypatch):
    """The bug's real damage: a dead host silently disabled every update check.

    ``tests/kova_cli/conftest.py`` stubs ``_resolve_channel`` for every unflagged
    test, so this opts out to reach the real reader. A transport failure must stay
    an error and must NOT degrade into ChannelNotFound, because ``main`` treats a
    missing record as "keep following the git branch" -- a distinction that only
    makes sense when the host was actually reached.
    """
    from kova_cli.release_channels import ChannelError, ChannelNotFound

    monkeypatch.setattr(source_releases, "_PUBLIC_BASE", "http://127.0.0.1:1/unreachable")
    with pytest.raises(ChannelError) as excinfo:
        source_releases.resolve_source_target("main", repository="example/kova-agent")
    assert not isinstance(excinfo.value, ChannelNotFound)