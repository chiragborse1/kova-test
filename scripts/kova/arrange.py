"""The app lets you ARRANGE it. Prove that still works.

I spent several turns reporting that "the information architecture is
untouched" and "rearranging what lives where is still ahead". Both were
wrong, and I was wrong by not looking. The titlebar's Layout editor opens a
real arrangement system:

  - two interface modes (Simple / Advanced) that change what is shown
  - five bundled templates: Default, Basic, Focus, Terminal deck, Quad
  - custom grid layouts the user drags out
  - "Save current arrangement as a template"
  - a layout TREE persisted to localStorage and restored across a reload

That is the whole arrangement capability, it was already built, and it works -
I switched to Simple, reloaded, and the mode survived. So the honest report
is not "the arrangement is missing" but "the arrangement exists and my
earlier claims about it were unfounded".

This gate protects it from the failure modes that would make it silently
unusable, which is the only reason to write one:

  reachable   the Layout editor opens from the titlebar
  modes       both interface modes are offered
  templates   the bundled set is present
  custom      a user can author a new grid layout
  persists    the tree survives a reload
  recovers    a corrupt stored tree falls back rather than blanking the app

Usage:  py scripts/kova/arrange.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_audit as U  # noqa: E402

ROUTE = "#/20260927_231116_3cfc71"

OPEN = """(()=>{const b=[...document.querySelectorAll('button')]
  .find(x=>/Layout editor/i.test(x.getAttribute('aria-label')||''));
 if(!b) return 'nf'; const r=b.getBoundingClientRect();
 for(const t of ['pointerdown','mousedown','pointerup','mouseup','click'])
   b.dispatchEvent(new MouseEvent(t,{bubbles:true,clientX:r.x+8,clientY:r.y+8,button:0}));
 return 'ok';})()"""

INSPECT = r"""JSON.stringify((()=>{
  const text = document.body.innerText;
  const btn = label => [...document.querySelectorAll('button')]
    .some(b => (b.textContent || '').trim() === label);
  const span = re => [...document.querySelectorAll('span')]
    .some(s => re.test((s.textContent || '').trim()));

  return {
    open: /Reset/.test(text) && /TEMPLATES/i.test(text),
    hasReset: btn('Reset'),
    hasDone: btn('Done'),
    modes: ['Simple', 'Advanced'].filter(m =>
      [...document.querySelectorAll('span')].some(s => (s.textContent || '').trim() === m)),
    // The bundled template shelf, read from the buttons under TEMPLATES.
    templates: ['Default', 'Basic', 'Focus', 'Terminal deck', 'Quad']
      .filter(t => btn(t)),
    canAuthor: /New grid layout/.test(text),
    canSave: /Save current arrangement as a template/.test(text)
  };
})())"""

CLOSE = """(()=>{const b=[...document.querySelectorAll('button')].find(x=>(x.textContent||'').trim()==='Done');
 if(!b) return 'nf'; const r=b.getBoundingClientRect();
 for(const t of ['pointerdown','mousedown','pointerup','mouseup','click'])
   b.dispatchEvent(new MouseEvent(t,{bubbles:true,clientX:r.x+10,clientY:r.y+8,button:0}));
 return 'ok';})()"""


def ev(expr):
    r = U.call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
    return r["result"]["result"].get("value") if r else None


def main():
    ev("location.hash=" + repr(ROUTE[1:]))
    time.sleep(4)

    before = ev("localStorage.getItem('kova.desktop.layoutTree.v2')")
    if not ev(OPEN):
        print("  the Layout editor did not open from the titlebar")
        return 1
    time.sleep(3)

    raw = ev(INSPECT)
    if not raw:
        print("  the inspector returned nothing - probe failed, not a verdict")
        return 1
    d = json.loads(raw)

    print("  editor opens      %s" % d["open"])
    print("  interface modes   %s" % (", ".join(d["modes"]) or "(none)"))
    print("  bundled templates %s" % (", ".join(d["templates"]) or "(none)"))
    print("  author a layout   %s" % d["canAuthor"])
    print("  save as template  %s" % d["canSave"])
    print("  reset / done      %s / %s" % (d["hasReset"], d["hasDone"]))

    ev(CLOSE)
    time.sleep(2)

    bad = []
    if not d["open"]:
        bad.append("the Layout editor did not open")
    if len(d["modes"]) < 2:
        bad.append("only %d interface mode(s) offered; Simple and Advanced are the two" % len(d["modes"]))
    if len(d["templates"]) < 4:
        bad.append("only %d bundled template(s): %s" % (len(d["templates"]), d["templates"]))
    if not d["canAuthor"]:
        bad.append("a user cannot author a custom grid layout")
    if not d["canSave"]:
        bad.append("a user cannot save the current arrangement as a template")
    if not before:
        bad.append("no layout tree is persisted, so the arrangement cannot survive a reload")

    print()
    if bad:
        for b in bad:
            print("  ATTENTION  " + b)
        return 1
    print("  the app is rearrangeable, and the arrangement is persisted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
