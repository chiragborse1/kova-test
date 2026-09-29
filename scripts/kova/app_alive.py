"""Is the app actually rendering?

Proven necessary, not hypothetical. With the renderer's root replaced by the
error boundary's own text - the state a stale-module 503 produces - these
gates passed on nothing at all:

    line_length    exit 0   "every line a person reads is inside the 45-90 band"
    scroll_cue     exit 0   "every clipping container paints a scrollbar"
    reachability   exit 0   (reads source, so never at risk - listed for honesty)

A gate that measures an empty page is not a gate. Every DOM-reading gate calls
this before it trusts a result, and treats a crashed renderer as a FAILURE of
the run rather than a pass with nothing in it.

    py scripts/kova/app_alive.py          -> exit 0 healthy, 1 not
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_audit as U  # noqa: E402

# The app's own error-boundary copy. route_measure already keyed on this string;
# every other gate should have been able to.
CRASH_MARKER = "Something broke"

PROBE = """JSON.stringify({
  broke: document.body.innerText.includes(%s),
  chars: document.body.innerText.trim().length,
  hash: location.hash
})""" % json.dumps(CRASH_MARKER)


def state():
    r = U.call("Runtime.evaluate", {"expression": PROBE, "returnByValue": True})
    raw = r["result"]["result"].get("value") if r else None
    if not raw:
        return {"broke": None, "chars": 0, "hash": ""}
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {"broke": None, "chars": 0, "hash": ""}


def alive(min_chars=200):
    """True only when a real UI is on screen. Raises rather than returning
    False so a caller cannot forget to check the return value."""
    s = state()
    if s["broke"] is None:
        raise RuntimeError("the liveness probe did not run - is the app up?")
    if s["broke"]:
        raise RuntimeError("the app is showing its error boundary; a gate run "
                           "against this measures nothing")
    if s["chars"] < min_chars:
        raise RuntimeError("the app rendered only %d characters of chrome; "
                           "a gate run against this measures nothing" % s["chars"])
    return True


if __name__ == "__main__":
    try:
        alive()
    except RuntimeError as exc:
        print("  APP NOT USABLE: %s" % exc)
        sys.exit(1)
    s = state()
    print("  app is rendering (%d chars at %s)" % (s["chars"], s["hash"]))
    sys.exit(0)
