"""Measure the UI across routes the way a person perceives it.

Every real defect in the Kova redesign was invisible in the source and obvious
in a measurement: a transcript rendering 267 characters per line, an accent tint
on every text field, a window-sized blur layer mounted for the whole session.
This captures the numbers that caught all of them, per route:

  sat%      share of the viewport painted with a saturated colour. The Codex
            reference spends ~2.5%. Catches "the accent leaked somewhere it
            should not be".
  boxes     visible bordered rectangles over 150x40 - the "rectangulish" tell.
            Control interiors (checkbox marks, switch tracks) are legitimate
            and appear here too, so read the list rather than the count.
  worstCPL  characters per line in the widest long paragraph, measured with
            canvas measureText against the LIVE computed font. Readable is
            45-90. The transcript used to render 267.
  hOverflow whether the document scrolls sideways.

Needs the dev server up with its CDP port open:  py scripts/kova/ui_audit.py
"""
import json, urllib.request, base64, socket, struct, os, sys, time
targets=json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/list",timeout=10).read())
page=next(t for t in targets if t["type"]=="page")
key=base64.b64encode(os.urandom(16)).decode()
s=socket.create_connection(("127.0.0.1",9222),timeout=30)
s.sendall((f"GET /devtools/page/{page['id']} HTTP/1.1\r\nHost: 127.0.0.1:9222\r\nUpgrade: websocket\r\n"
           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
buf=b""
while b"\r\n\r\n" not in buf: buf+=s.recv(4096)
_id=[0]
def send(method,params=None):
    _id[0]+=1
    o={"id":_id[0],"method":method}
    if params: o["params"]=params
    p=json.dumps(o).encode(); m=os.urandom(4); n=len(p)
    h=b"\x81"+(bytes([0x80|n]) if n<126 else (bytes([0x80|126])+struct.pack(">H",n) if n<65536 else bytes([0x80|127])+struct.pack(">Q",n)))
    s.sendall(h+m+bytes(b^m[i%4] for i,b in enumerate(p)))
    return _id[0]
def recv():
    d=s.recv(2); ln=d[1]&0x7F
    if ln==126: ln=struct.unpack(">H",s.recv(2))[0]
    elif ln==127: ln=struct.unpack(">Q",s.recv(8))[0]
    b=b""
    while len(b)<ln: b+=s.recv(ln-len(b))
    return json.loads(b)
def call(method,params=None,tries=12):
    i=send(method,params)
    for _ in range(tries):
        m=recv()
        if m.get("id")==i: return m
    return None

# Evaluated in the page. Measures against the LIVE computed font rather than a
# hard-coded one, because the whole point is to catch a measure that is wrong
# for the font the app is actually rendering with.
PROBE = r"""JSON.stringify((()=>{
  const cvs=document.createElement('canvas').getContext('2d');
  let sat=0, boxes=0, over=0;
  for(const el of document.querySelectorAll('body, body *')){
    const r=el.getBoundingClientRect();
    if(r.width<4||r.height<4) continue;
    if(r.bottom<0||r.top>innerHeight||r.right<0||r.left>innerWidth) continue;
    const cs=getComputedStyle(el);
    const n=(cs.backgroundColor.match(/[\d.]+/g)||[]).map(Number);
    if(n.length>=3){
      const mx=Math.max(n[0],n[1],n[2]), mn=Math.min(n[0],n[1],n[2]);
      if(mx>0&&(mx-mn)/mx>0.25) sat+=r.width*r.height;
    }
    const bw=parseFloat(cs.borderTopWidth)||0;
    if(bw>0.5&&cs.borderTopStyle!=='none'&&r.width>150&&r.height>40) boxes++;
    if(el.scrollWidth>el.clientWidth+2&&el.clientWidth>0){
      const ox=cs.overflowX;
      if(ox!=='visible'&&ox!=='clip') over++;
    }
  }
  let worst=0, worstW=0, worstTxt='';
  for(const p of document.querySelectorAll('p')){
    const t=(p.textContent||'').trim();
    if(t.length<120) continue;
    const s=getComputedStyle(p), r=p.getBoundingClientRect();
    cvs.font=s.fontWeight+' '+s.fontSize+' '+s.fontFamily;
    const adv=cvs.measureText('abcdefghijklmnopqrstuvwxyz').width/26;
    const cpl=Math.round(r.width/adv);
    if(cpl>worst){worst=cpl; worstW=Math.round(r.width); worstTxt=t.slice(0,40);}
  }
  return {satPct:+(sat/(innerWidth*innerHeight)*100).toFixed(2), boxes:boxes,
    worstCPL:worst, worstColW:worstW, worstTxt:worstTxt, overflowContainers:over,
    hOverflow:document.documentElement.scrollWidth>innerWidth+2};
})())"""


ROUTES = [
    ("chat", "/#/20260927_231116_3cfc71"),
    ("capabilities", "/#/capabilities"),
    ("artifacts", "/#/artifacts"),
    ("messaging", "/#/messaging"),
    ("settings", "/#/settings"),
    ("cron", "/#/cron"),
]


def main() -> int:
    bad = []
    print("  %-14s %7s %7s %10s %11s" % ("route", "sat%", "boxes", "worstCPL", "hOverflow"))
    for name, route in ROUTES:
        call("Runtime.evaluate", {"expression": "location.hash=" + repr(route[1:])})
        time.sleep(3)
        raw = call("Runtime.evaluate", {"expression": PROBE, "returnByValue": True})
        value = raw["result"]["result"].get("value") if raw else None
        if not value:
            print("  %-14s  (no value)" % name)
            continue
        d = json.loads(value)
        print("  %-14s %7s %7d %10d %11s"
              % (name, d["satPct"], d["boxes"], d["worstCPL"], d["hOverflow"]))
        if d["hOverflow"]:
            bad.append(name + ": the document scrolls sideways")
        if d["worstCPL"] > 120:
            bad.append("%s: %d chars per line in a %dpx column" % (name, d["worstCPL"], d["worstColW"]))
        if d["satPct"] > 12:
            bad.append("%s: %s%% of the viewport is saturated" % (name, d["satPct"]))
    print()
    if bad:
        for b in bad:
            print("  ATTENTION  " + b)
        return 1
    print("  no route trips a threshold (CPL>120, sat>12%, sideways scroll)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
