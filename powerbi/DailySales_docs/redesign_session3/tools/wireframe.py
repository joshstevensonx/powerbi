import json, os, sys, glob, html
src, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)
defn = os.path.join(src, "Report", "definition", "pages")
order = json.load(open(os.path.join(defn, "pages.json")))["pageOrder"]
FILL = {"cardVisual": "#E6F8FB", "slicer": "#FFFFFF", "shape": None, "textbox": None, "image": "#FFFFFF",
        "actionButton": "#FFFFFF"}
def title(v):
    try: return v["visual"]["visualContainerObjects"]["title"][0]["properties"]["text"]["expr"]["Literal"]["Value"].strip("'").replace("''", "'")
    except Exception: return ""
def text(v):
    try: return " ".join(r["value"] for p in v["visual"]["objects"]["general"][0]["properties"]["paragraphs"] for r in p["textRuns"])
    except Exception: return ""
for i, pid in enumerate(order):
    p = json.load(open(os.path.join(defn, pid, "page.json")))
    if p.get("type") == "Tooltip" or p["displayName"] == "Guide": continue
    W, H = p["width"], p["height"]
    vs = [json.load(open(f)) for f in glob.glob(os.path.join(defn, pid, "visuals", "*", "visual.json"))]
    vs.sort(key=lambda v: v["position"].get("z", 0))
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Segoe UI, Arial, sans-serif">',
           f'<rect width="{W}" height="{H}" fill="#F4F6F8"/>']
    for v in vs:
        ps = v["position"]; x, y, w, h = ps["x"], ps["y"], ps["width"], ps["height"]
        t = v["visual"]["visualType"]
        if t == "shape":
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{8 if w < W else 0}" fill="#FFFFFF" stroke="#E3E5E8"/>'); continue
        if t == "textbox":
            s = html.escape(text(v))[:150]
            big = 18 if "Daily Sales" in s else 10
            col = "#231F20" if big > 10 else "#55565A"
            out.append(f'<text x="{x}" y="{y + big + 2}" font-size="{big}" fill="{col}">{s}</text>'); continue
        if t == "image":
            out.append(f'<text x="{x}" y="{y + 28}" font-size="24" font-weight="700" fill="#00C1DE">1-grid</text>'); continue
        fill = FILL.get(t, "#FFFFFF")
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{"#00C1DE" if t=="slicer" else "#E3E5E8"}"/>')
        label = title(v) if t not in ("slicer",) else title(v) + " ▾"
        out.append(f'<text x="{x + 10}" y="{y + 18}" font-size="11" fill="#231F20">{html.escape(label[:int(w / 6)])}</text>')
        if t not in ("slicer", "actionButton") and h > 60:
            out.append(f'<text x="{x + 10}" y="{y + h - 10}" font-size="9" fill="#A7A8AB">{t}</text>')
    out.append("</svg>")
    fn = os.path.join(outdir, f"{i + 1:02d}_{p['displayName'].replace(' ', '_').replace('&', 'and')}.svg")
    open(fn, "w").write("\n".join(out)); print(fn)
