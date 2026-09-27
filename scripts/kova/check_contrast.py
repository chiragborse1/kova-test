def lin(c):
    c = c/255
    return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4
def L(hexs):
    h = hexs.lstrip('#')
    r,g,b = (int(h[i:i+2],16) for i in (0,2,4))
    return 0.2126*lin(r) + 0.7152*lin(g) + 0.0722*lin(b)
def ratio(a,b):
    la,lb = L(a),L(b)
    hi,lo = max(la,lb),min(la,lb)
    return (hi+0.05)/(lo+0.05)

checks = [
 ("LIGHT accent on bg",      "#6d3bf5", "#fbfafc", 4.5),
 ("LIGHT fg on bg",          "#1a1625", "#fbfafc", 4.5),
 ("LIGHT mutedFg on bg",     "#635d75", "#fbfafc", 4.5),
 ("LIGHT primaryFg on primary","#ffffff","#6d3bf5", 4.5),
 ("DARK accent on bg",       "#9d7bff", "#0b0910", 4.5),
 ("DARK fg on bg",           "#ece9f5", "#0b0910", 4.5),
 ("DARK mutedFg on bg",      "#9a93ad", "#0b0910", 4.5),
 ("DARK primaryFg on primary","#150f24","#9d7bff", 4.5),
 ("LIGHT destructive on bg", "#c62f4b", "#fbfafc", 4.5),
 ("DARK destructive on bg",  "#ff6b83", "#0b0910", 4.5),
]
allok=True
for name,fg,bg,need in checks:
    r = ratio(fg,bg)
    ok = r >= need
    allok &= ok
    print(f"  {'PASS' if ok else 'FAIL'}  {name:32} {r:5.2f}:1  (need {need})")
print()
print("ALL PASS" if allok else "SOME FAIL - palette needs adjusting")
