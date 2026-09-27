"""Tests for the Nous-Kova-3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
``"kova"`` anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``kova-brain:qwen3-14b-ctx16k`` — a tool-capable
Qwen3 wrapper that happens to live under the "kova" tag namespace.

``is_nous_kova_non_agentic`` should only match the actual Nous Research
Kova-3 / Kova-4 chat family.
"""

from __future__ import annotations

import pytest

from kova_cli.model_switch import (
    _KOVA_MODEL_WARNING,
    _check_kova_model_warning,
    is_nous_kova_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "nousresearch/hermes-3-Llama-3.1-70B",
        "nousresearch/hermes-3-Llama-3.1-405B",
        "kova-3",
        "Kova-3",
        "kova-4",
        "hermes-4-405b",
        "kova_4_70b",
        "openrouter/kova3:70b",
        "openrouter/nousresearch/hermes-4-405b",
        "OpenKova/Hermes3",
        "kova-3.1",
    ],
)
def test_matches_real_nous_kova_chat_models(model_name: str) -> None:
    assert is_nous_kova_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as Nous Kova 3/4"
    )
    assert _check_kova_model_warning(model_name) == _KOVA_MODEL_WARNING


