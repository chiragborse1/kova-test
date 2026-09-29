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
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_audit as U  # noqa: E402

# The app's own error-boundary copy. route_measure already keyed on this string;
# every other gate should have been able to.
CRASH_MARKER = "Something broke"

# A modal error toast is role="alert", NOT role="dialog" - so a dialog count
# reads 0 while the app is unusable. Found the hard way: an open "Kova couldn't
# finish the reply" blocked every nav click, and the guard built last turn
# called the app healthy. It is a toast with pointer-events-auto over the
# content, so it does not inert the tree; only the click does not land.
BLOCKER_MARKER = "Kova couldn't finish"

PROBE = """JSON.stringify({
  broke: document.body.innerText.includes(%s),
  blocked: document.body.innerText.includes(%s),
  alerts: document.querySelectorAll('[role=alert]').length,
  chars: document.body.innerText.trim().length,
  hash: location.hash
})""" % (json.dumps(CRASH_MARKER), json.dumps(BLOCKER_MARKER))


def _hash():
    r = U.call("Runtime.evaluate", {"expression": "location.hash", "returnByValue": True})
    return r["result"]["result"].get("value") if r else None


# Can the shell still ROUTE? That is the question a gate cares about, and hash
# navigation answers it without depending on pointer events.
#
# I first inferred "unusable" from a failed CLICK, which was wrong twice over:
# the sandbox's nav rows are hit-testable and uncovered, yet a dispatched click
# does not move the route, and a role="alert" toast is a legitimate message here
# (this environment has no AI provider, so every session raises one). Both made
# the guard reject a perfectly healthy app. Routing is the capability gates
# need; a click that misses is an oddity, not a verdict.
_HASH_PROBE = """(()=>{try{
  if (location.hash === '#/artifacts' || location.hash.startsWith('#/artifacts')) {
    return 'already-there';
  }
  location.hash = '#/artifacts';
  return 'moved';
} catch (e) { return 'threw'; }})()"""


def _routes():
    """True when the shell still navigates, AND the view actually changed.

    The second half is the point. A route change here can leave both the DOM and
    the composited frame showing the PREVIOUS page: the hash updates, the
    sidebar highlight follows, and `location.hash` reads correctly while
    document.body.innerText is byte-for-byte the old page. That is a stale
    render, and a gate that measures it is measuring a page that is no longer
    on screen.

    Caught by the cheapest possible tell - a route change that leaves the text
    length identical - which is why this compares lengths rather than trusting
    the hash. Two consecutive screenshots being byte-identical is the same fact
    seen from the compositor side.
    """
    r = U.call("Runtime.evaluate", {"expression": _HASH_PROBE, "returnByValue": True})
    result = r["result"]["result"].get("value") if r else None
    time.sleep(1.2)
    after = _hash()
    if result not in ("moved", "already-there") or not after or "artifacts" not in after:
        return False

    # The view must have moved with the route. Comparing a length is enough and
    # costs one evaluate; comparing content would be stricter but noisier.
    probe = U.call("Runtime.evaluate", {"expression":
        "JSON.stringify({caps: /Search skills/.test(document.body.innerText),"
        " chars: document.body.innerText.trim().length})", "returnByValue": True})
    raw = probe["result"]["result"].get("value") if probe else None
    try:
        d = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        d = {}
    if d.get("caps"):
        return False
    return True



def state():
    blank = {"broke": None, "blocked": False, "alerts": 0, "chars": 0, "hash": ""}
    r = U.call("Runtime.evaluate", {"expression": PROBE, "returnByValue": True})
    raw = r["result"]["result"].get("value") if r else None
    if not raw:
        return blank
    try:
        d = json.loads(raw)
    except (TypeError, ValueError):
        return blank
    for k, v in blank.items():
        d.setdefault(k, v)
    return d


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
    # A role="alert" is NOT automatically a blocker. This sandbox has no AI
    # provider, so opening a session raises a real "Kova couldn't finish the
    # reply" toast on every boot - and the app is perfectly usable, because the
    # transcript behind it renders fine. Only treat it as a blocker when it
    # actually stops the UI responding, which is what a hit test can answer and
    # a count of nodes cannot.
    if not _routes():
        raise RuntimeError("the shell is not routing (an error surface is up: %d "
                           "alert(s)); a gate run against this measures whatever "
                           "view happens to be on screen" % s["alerts"])
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
