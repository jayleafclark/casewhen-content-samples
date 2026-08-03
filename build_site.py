#!/usr/bin/env python3
"""
build_site.py — generate the CaseWhen 6-month content site from the real calendar
tables + a copy store of finished, gated post text.

- Reads the per-platform idea tables (content/w-platform-batches/*.csv).
- Lays out a 6-month library per platform at the cadence from 12-distribution-map:
    Blog        1/day EN  +  Mon/Wed/Fri DE
    LinkedIn    Austin EN Mon/Wed/Fri  +  Saju DE Tue/Thu/Sat (different order)
    Short-form  EN Tue/Thu/Sat + DE Mon/Wed  (title + caption + on-screen text)
    X/Twitter   weekly (Mon)
    Quote card  weekly (Mon)
- Each slot renders FINISHED gated copy if present in copy-store.json (keyed
  "<platform>:<n>"), otherwise the scheduled plan (keyword, SEO title, hook, format).
- Emits index.html (the pain page + nav) and one page per platform. Mobile-first.

Run:  python build_site.py
"""
import csv, json, html, re
from pathlib import Path

ROOT = Path(r"J:\Claude Code\casewhen-research\content\w-platform-batches")
OUT = Path(__file__).resolve().parent
COPY = json.loads((OUT / "copy-store.json").read_text(encoding="utf-8")) if (OUT / "copy-store.json").exists() else {}

def rows(fn):
    with open(ROOT / fn, encoding="utf-8") as fh:
        r = list(csv.DictReader(fh))
    return r

def esc(s): return html.escape((s or "").strip())

# weekday of day d (day 1 = Monday). 0=Mon..6=Sun
def wd(d): return (d - 1) % 7
WD_NAME = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

def schedule(table, lang, days, cadence):
    """Assign the first N matching-language rows to calendar days at a cadence."""
    pool = [r for r in table if (r.get("lang") or "").upper() == lang]
    out, i = [], 0
    for d in range(1, days + 1):
        if wd(d) in cadence and i < len(pool):
            out.append((d, pool[i])); i += 1
    return out

DAYS = 30
blog = rows("01-blog-website.csv")
li   = rows("02-linkedin.csv")
xt   = rows("05-x-twitter.csv")
sf   = rows("04-short-form-video.csv")

PLATFORMS = {
    "blog": {
        "title": "Blog", "tag": "casewhen.co",
        "blurb": "One English article a day, three German a week. Each targets one real search term, "
                 "answers it in the first lines for Google and AI answers, and carries a named founder byline.",
        "slots": ([("EN", d, r) for d, r in schedule(blog, "EN", DAYS, {0,1,2,3,4,5,6})]
                  + [("DE", d, r) for d, r in schedule(blog, "DE", DAYS, {0,2,4})]),
    },
    "linkedin": {
        "title": "LinkedIn", "tag": "Austin (EN) · Saju (DE)",
        "blurb": "Austin posts in English on Monday, Wednesday, Friday. Saju posts in German on a "
                 "different rhythm (Tuesday, Thursday, Saturday). A flat declarative hook, one real "
                 "number, a question that pulls a reply. Link goes in the first comment.",
        "slots": ([("EN", d, r) for d, r in schedule(li, "EN", DAYS, {0,2,4})]
                  + [("DE", d, r) for d, r in schedule(li, "DE", DAYS, {1,3,5})]),
    },
    "shortform": {
        "title": "Short-form scripts", "tag": "script · caption · on-screen text",
        "blurb": "We can't render the video here, so each card is the full script: the spoken hook "
                 "that carries the search term, the on-screen text, and the platform caption with the "
                 "keyword. Payoff in the first two seconds, one idea. Every one is reposted to X and "
                 "Threads as well as YouTube Shorts, TikTok, and Reels.",
        "slots": ([("EN", d, r) for d, r in schedule(sf, "EN", DAYS, {1,3,5})]
                  + [("DE", d, r) for d, r in schedule(sf, "DE", DAYS, {0,2})]),
    },
    "x": {
        "title": "X / Twitter", "tag": "one native post a day + reposts to X and Threads",
        "blurb": "One native post every day, plus every short-form video and every carousel "
                 "graphic reposted to X and Threads (the same asset, a platform-native caption). This "
                 "is the cheapest reach we have: content made once, shown on three more surfaces.",
        "slots": [("EN", d, r) for d, r in schedule(xt, "EN", DAYS, {0,1,2,3,4,5,6})],
    },
}

# ---- HTML ----
CSS = """
:root{--ink:#141a19;--bg:#fbfcfc;--card:#fff;--line:#e2e8e6;--mut:#5c6866;--faint:#93a09c;
--brand:#1D967C;--dark:#11493F;--mid:#7AC4B5;--pale:#D8F3EE;--neutral:#E9ECE8}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;overflow-x:hidden}
body{margin:0;font-family:'NM',ui-sans-serif,-apple-system,'Segoe UI',sans-serif;color:var(--ink);
background:var(--bg);line-height:1.6;-webkit-font-smoothing:antialiased;overflow-x:hidden;max-width:100%}
p,h1,h2,h3,li,td,th{overflow-wrap:break-word}
@font-face{font-family:'NM';src:url('fonts/nm-book.woff2') format('woff2');font-weight:400;font-display:swap}
@font-face{font-family:'NM';src:url('fonts/nm-medium.woff2') format('woff2');font-weight:500;font-display:swap}
@font-face{font-family:'NM';src:url('fonts/nm-bold.woff2') format('woff2');font-weight:700;font-display:swap}
.wrap{max-width:1060px;margin:0 auto;padding:0 20px}
h1,h2,h3{font-weight:700;letter-spacing:-.02em;line-height:1.12;margin:0}
a{color:var(--dark)}
/* top nav */
.top{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.92);backdrop-filter:blur(8px);
border-bottom:1px solid var(--line)}
.top .wrap{display:flex;align-items:center;gap:16px;padding:12px 20px;flex-wrap:wrap}
.top img{height:24px}
.nav{display:flex;gap:4px;margin-left:auto;flex-wrap:wrap}
.nav a{font-size:13.5px;color:var(--mut);text-decoration:none;padding:7px 12px;border-radius:8px;white-space:nowrap}
.nav a:hover{background:var(--pale);color:var(--dark)}
.nav a.on{background:var(--dark);color:#fff}
/* hero */
.hero{padding:56px 0 34px;border-bottom:1px solid var(--line)}
.hero .eb{font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--brand);margin-bottom:12px}
.hero h1{font-size:clamp(29px,5.4vw,50px);max-width:17ch}
.hero p{font-size:clamp(16px,2.2vw,18.5px);color:var(--mut);max-width:60ch;margin:18px 0 0}
/* cadence cards on home */
.cad{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-top:30px}
.cad a{display:block;text-decoration:none;color:inherit;border:1px solid var(--line);border-radius:14px;
padding:18px;background:var(--card);transition:transform .12s,box-shadow .12s}
.cad a:hover{transform:translateY(-2px);box-shadow:0 10px 30px rgba(17,73,63,.10)}
.cad .n{font-size:30px;font-weight:700;color:var(--dark);letter-spacing:-.03em}
.cad .l{font-weight:600;margin-top:2px}
.cad .s{font-size:12.5px;color:var(--faint);margin-top:3px}
/* section header */
.ph{padding:40px 0 8px}
.ph .eb{font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--brand)}
.ph h2{font-size:clamp(24px,3.4vw,34px);margin:6px 0 0}
.ph p{color:var(--mut);max-width:64ch;margin:12px 0 0;font-size:15.5px}
.count{font-size:12.5px;color:var(--faint);margin-top:10px}
/* post cards */
.days{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;padding:24px 0 60px}
.card{border:1px solid var(--line);border-radius:16px;background:var(--card);overflow:hidden;display:flex;flex-direction:column;min-width:0}
.card.full{grid-column:1/-1}
.card .bar{display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid var(--line);flex-wrap:wrap;min-width:0}
.day{font-size:11px;font-weight:700;letter-spacing:.03em;background:var(--dark);color:#fff;border-radius:7px;padding:4px 8px}
.lang{font-size:11px;font-weight:700;border-radius:7px;padding:4px 8px}
.lang.en{background:var(--pale);color:var(--dark)}.lang.de{background:#e7efe9;color:#2c5a4c}
.who{font-size:12px;color:var(--faint)}
.kw{margin-left:auto;font-size:11.5px;color:var(--dark);background:#eef5f2;border:1px solid var(--mid);border-radius:20px;padding:3px 10px;font-weight:500;white-space:normal;overflow-wrap:anywhere;max-width:100%}
.card .body{padding:15px 16px 16px;font-size:14px;color:#2d3330}
.plan .t{font-weight:700;font-size:15px;color:var(--ink);margin:0 0 8px}
.plan .row{display:flex;gap:7px;font-size:12px;color:var(--mut);margin:4px 0}
.plan .row b{color:var(--faint);font-weight:600;flex:none;width:64px;text-transform:uppercase;letter-spacing:.04em;font-size:10px;padding-top:2px}
.state{margin-top:12px;font-size:11.5px;color:var(--faint);border-top:1px dashed var(--line);padding-top:10px}
.done .hook{font-weight:700;font-size:15.5px;display:block;margin-bottom:8px}
.done .txt{white-space:pre-line}
.done .close{margin-top:10px;color:var(--dark);font-weight:500}
.done .meta{margin-top:12px;border-top:1px solid var(--line);padding-top:9px;font-size:11px;color:var(--faint);display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
.ship{color:var(--brand);font-weight:700}
/* short-form script */
.script .sk-hook{font-weight:700;font-size:15.5px;margin:2px 0 4px}
.script .sk-os{font-size:11.5px;color:var(--dark);background:var(--pale);border-radius:6px;padding:3px 8px;display:inline-block;margin-bottom:10px}
.beat{display:grid;grid-template-columns:52px minmax(0,1fr);gap:10px;padding:9px 0;border-top:1px solid var(--line)}
.beat .t{font-size:10.5px;font-weight:700;color:var(--faint);letter-spacing:.03em;padding-top:2px}
.beat .sp{font-size:13.5px;color:#2d3330}
.beat .os{font-size:11px;color:var(--dark);margin-top:4px}
.beat .os b{font-weight:600;color:var(--faint);text-transform:uppercase;letter-spacing:.04em;font-size:9.5px}
.beat .pr{font-size:11px;color:var(--faint);margin-top:3px;font-style:italic}
.cap{margin-top:12px;background:#f4f8f6;border-radius:8px;padding:10px 12px;font-size:12.5px;color:#2d3330}
.cap b{color:var(--faint);text-transform:uppercase;letter-spacing:.04em;font-size:9.5px;display:block;margin-bottom:3px}
/* full blog article */
.article{max-width:none}
.article h1{font-size:clamp(22px,3vw,30px);margin:2px 0 10px}
.article h2{font-size:19px;margin:22px 0 6px;color:var(--dark)}
.article p{font-size:14.5px;color:#33372f;margin:0 0 11px}
.article .qa{background:var(--pale);border-left:3px solid var(--brand);border-radius:0 8px 8px 0;padding:12px 14px;font-size:14px;margin:0 0 16px}
.article table{width:100%;border-collapse:collapse;margin:12px 0;font-size:12.5px}
.article th{text-align:left;background:var(--neutral);padding:7px 9px;font-size:11.5px}
.article td{border-top:1px solid var(--line);padding:7px 9px;vertical-align:top}
.article ol,.article ul{padding-left:20px}.article li{font-size:14px;margin:4px 0}
.article .fm{font-size:11px;color:var(--faint);border-bottom:1px solid var(--line);padding-bottom:8px;margin-bottom:14px;display:flex;gap:10px;flex-wrap:wrap}
/* visuals page */
.vsec{padding:26px 0;border-top:1px solid var(--line)}
.vsec:first-of-type{border-top:0}
.vname{font-weight:700;font-size:17px;margin:0 0 3px}
.vname span{color:var(--faint);font-weight:400;font-size:13.5px}
.vgal{display:grid;gap:16px;margin-top:14px;grid-template-columns:repeat(4,minmax(0,1fr))}
.vgal.wide{grid-template-columns:repeat(2,minmax(0,1fr))}
.vgal img{width:100%;height:auto;border-radius:12px;box-shadow:0 8px 30px rgba(17,73,63,.13);display:block}
.vstrip{display:flex;gap:14px;overflow-x:auto;margin-top:14px;padding-bottom:12px;scroll-snap-type:x mandatory}
.vstrip img{flex:none;width:200px;height:auto;border-radius:12px;box-shadow:0 8px 30px rgba(17,73,63,.13);scroll-snap-align:start}
.vhint{font-size:11.5px;color:var(--faint);margin-top:8px}
@media(max-width:760px){.vgal{grid-template-columns:repeat(2,minmax(0,1fr))}.vgal.wide{grid-template-columns:1fr}}
.foot{padding:30px 0 50px;color:var(--mut);font-size:13px;border-top:1px solid var(--line)}
@media(max-width:760px){
 .cad{grid-template-columns:repeat(2,minmax(0,1fr))}
 .days{grid-template-columns:minmax(0,1fr)}
 .top .wrap{gap:8px}
 .nav{width:100%;margin-left:0;flex-wrap:wrap;gap:6px}
 .hero{padding:40px 0 26px}
}
"""

def nav(active):
    items = [("index.html","Home"),("strategy.html","Strategy")] + [(f"{k}.html", v["title"]) for k, v in PLATFORMS.items()] + [("youtube.html","YouTube"),("visuals.html","Visuals"),("seo.html","SEO"),("funnels.html","Funnels"),("pricing.html","Pricing")]
    return "".join(f'<a href="{h}" class="{"on" if h==active else ""}">{esc(t)}</a>' for h, t in items)

def shell(active, title, inner):
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>CaseWhen · {esc(title)}</title>
<style>{CSS}</style><link rel="stylesheet" href="annotate.css"></head><body>
<header class="top"><div class="wrap"><img src="img/wordmark.png" alt="CaseWhen">
<nav class="nav">{nav(active)}</nav></div></header>
{inner}
<footer class="foot"><div class="wrap">A 6-month content plan built from the keyword calendar. Every
finished post clears the ship gate (plain language, a concrete specific, external-facing only, and the
per-platform format) before it appears as done. Internal preview · not indexed.</div></footer>
<script src="annotate.js"></script>
</body></html>"""

CONTENT = Path(r"J:\Claude Code\casewhen-research\content\w-batch02-presentation")
_REPO = Path(r"J:\Claude Code\casewhen-research")
def reposrc(f):
    """Repo-relative source path for a content file, for the AI-editor data-src."""
    try: return str(Path(f).resolve().relative_to(_REPO)).replace("\\", "/")
    except Exception: return ""

def md_to_html(md):
    """Light markdown -> HTML for a finished blog article (front-matter already handled)."""
    # split front-matter (KEY: value before first '---')
    fm = {}
    if "---" in md:
        head, _, md = md.partition("---")
        for ln in head.splitlines():
            m = re.match(r"^([A-Za-z][\w ()',.&/-]*?):\s*(.*)$", ln)
            if m: fm[re.sub(r"\s*\(.*?\)", "", m.group(1)).strip().upper()] = m.group(2).strip()
    out = []
    fmbar = f'<div class="fm"><b>{esc(fm.get("BYLINE",""))}</b><span>{esc(fm.get("KEYWORD","").split("|")[0])}</span><span>{esc(fm.get("SCHEMA",""))}</span></div>'
    out.append(fmbar)
    out.append(f'<h1>{esc(fm.get("H1", fm.get("META_TITLE","")))}</h1>')
    blocks = re.split(r"\n\s*\n", md.strip())
    tbl = []
    for blk in blocks:
        b = blk.strip()
        if not b or b == "---":
            continue
        if b.upper().startswith("QUICK ANSWER"):
            txt = b.split(":", 1)[1].strip() if ":" in b else b
            out.append(f'<div class="qa"><b>Quick answer.</b> {esc(txt)}</div>'); continue
        if b.startswith("## "):
            out.append(f'<h2>{esc(b[3:].strip())}</h2>'); continue
        if b.startswith("|"):  # table
            rows = [r for r in b.splitlines() if r.strip().startswith("|")]
            rows = [r for r in rows if not re.match(r"^\s*\|[\s|:-]+\|\s*$", r)]
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
            if cells:
                h = "".join(f"<th>{esc(x)}</th>" for x in cells[0])
                body = "".join("<tr>"+"".join(f"<td>{esc(x)}</td>" for x in row)+"</tr>" for row in cells[1:])
                out.append(f'<table><tr>{h}</tr>{body}</table>')
            continue
        debold = lambda s: re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        if re.match(r"^\d+\.\s", b):
            items = "".join("<li>%s</li>" % esc(debold(re.sub(r"^\d+\.\s", "", x))) for x in b.splitlines() if x.strip())
            out.append(f"<ol>{items}</ol>"); continue
        if b.startswith("- "):
            items = "".join("<li>%s</li>" % esc(debold(x[2:])) for x in b.splitlines() if x.strip().startswith("- "))
            out.append(f"<ul>{items}</ul>"); continue
        # paragraph (strip bold markers for plain render)
        out.append(f'<p>{esc(re.sub(r"\*\*(.+?)\*\*", r"\1", b))}</p>')
    return f'<div class="body article annotatable">{"".join(out)}</div>'

def render_script(c):
    beats = ""
    for bt in c.get("beats", []):
        beats += (f'<div class="beat"><div class="t">{esc(bt.get("t"))}</div><div>'
                  f'<div class="sp">{esc(bt.get("spoken"))}</div>'
                  f'<div class="os"><b>on-screen</b> {esc(bt.get("screen"))}</div>'
                  f'<div class="pr">{esc(bt.get("prod"))}</div></div></div>')
    cap = (f'<div class="cap"><b>caption</b>{esc(c.get("caption",""))}</div>' if c.get("caption") else "")
    return (f'<div class="body script annotatable"><div class="sk-hook">{esc(c["hook"])}</div>'
            f'<span class="sk-os">frame 1: {esc(c.get("onscreen",""))}</span>{beats}{cap}'
            f'<div class="meta"><span class="ship">SHIP ✓ gated</span><span>{esc(c.get("note",""))}</span></div></div>')

CATS = ["AI & Copilot","Migration","Governance & trust","Pricing & licensing","Close & finance",
        "Dashboards & adoption","Fabric & Azure","KPI & modeling","Hiring & consulting"]
def categorize(c, kw, r=None):
    """Map a post to one content category from its cluster/note/keyword."""
    blob = " ".join(str(x) for x in [
        (c or {}).get("cluster",""), (c or {}).get("note",""), (c or {}).get("keyword",""),
        kw, (r or {}).get("cluster","")]).lower()
    tests = [
        ("AI & Copilot", ["copilot","ai/","ai ","genai"," ki ","künstliche","natural language","fabric ai","ai readiness","ai-ready"]),
        ("Migration", ["migrat","tableau","qlik","cognos","businessobjects","sap bo","wechsel","umzug","move off","move to power"]),
        ("Governance & trust", ["governance","single source","source of truth","trust","vertrau","row-level","row level","permission","berechtigung","silo"]),
        ("Pricing & licensing", ["pricing","price","cost","license","licence","premium","per user","per-user","capacity","preis","lizenz","kosten"]),
        ("Close & finance", ["close","month-end","monthly close","excel","fp&a","reconcil","abschluss","finance","controlling","kennzahl"]),
        ("Dashboards & adoption", ["dashboard","adoption","self-service","self serve","bottleneck","nobody uses","citizen"]),
        ("Fabric & Azure", ["fabric","onelake","lakehouse","synapse","azure","data factory","adf","databricks","warehouse"]),
        ("KPI & modeling", ["kpi","dax","measure","data model","datenmodell","semantic","star schema","sternschema","snowflake","rankx","modeling"]),
        ("Hiring & consulting", ["consultant","consulting","consultancy","hire","expert","agency","beratung","dienstleister","berater","in-house","vendor"]),
    ]
    for name, kws in tests:
        if any(w in blob for w in kws): return name
    return "Governance & trust"

def card(platform, idx, lang, day, r, detail=None):
    key = f"{platform}:{idx}"
    c = COPY.get(key)
    # a merged social post carries its own real topic/lang; prefer it over the slot's
    if c and c.get("keyword"):
        lang = (c.get("lang") or lang).upper()
    who = (c.get("who") if c and c.get("who") else ("Austin" if lang == "EN" else "Saju"))
    kw = esc(c.get("keyword") if c and c.get("keyword") else r.get("primary_keyword"))
    cat = categorize(c, c.get("keyword") if c else "", r)
    open_lnk = f'<a class="openp" href="{detail}">Open &amp; review &rarr;</a>' if detail else ''
    bar = (f'<div class="bar"><span class="cat">{esc(cat)}</span>'
           f'<span class="lang {lang.lower()}">{lang}</span>'
           f'<span class="who">{who}</span><span class="kw">{kw}</span>{open_lnk}</div>')
    if c and c.get("article_file"):  # full blog article
        md = (CONTENT / c["article_file"]).read_text(encoding="utf-8")
        body = md_to_html(md)
    elif c and c.get("format") == "script":  # short-form script
        body = render_script(c)
    elif c:  # finished short text (LinkedIn / X / blog summary)
        hook_t = (c.get("hook") or "").strip()
        txt_t = (c.get("body") or "").strip()
        # X posts store the whole post in body (hook included); don't print the hook twice
        if hook_t and txt_t.startswith(hook_t):
            txt_t = txt_t[len(hook_t):].lstrip(" \n")
        body = f'<div class="body done annotatable"><span class="hook">{esc(hook_t)}</span>' \
               f'<div class="txt">{esc(txt_t)}</div>'
        if c.get("close"): body += f'<div class="close">{esc(c["close"])}</div>'
        body += f'<div class="meta"><span class="ship">SHIP ✓ gated</span>' \
                f'<span>{esc(c.get("note",""))}</span></div></div>'
    else:  # scheduled plan
        body = ('<div class="body plan">'
                f'<div class="t">{esc(r.get("title_seo_harness"))}</div>'
                f'<div class="row"><b>Keyword</b><span>{kw}</span></div>'
                f'<div class="row"><b>Cluster</b><span>{esc(r.get("cluster"))}</span></div>'
                f'<div class="row"><b>Format</b><span>{esc(r.get("format"))}</span></div>'
                f'<div class="row"><b>Hook</b><span>{esc(r.get("hook_type"))}</span></div>'
                '<div class="state">Scheduled · finished copy being written through the ship gate</div></div>')
    full = " full" if (c and c.get("article_file")) else ""
    _catl = categorize(c, c.get("keyword") if c else "", r)
    _src = esc((c or {}).get("_src", ""))
    return f'<article class="card{full}" data-lang="{lang.upper()}" data-cat="{esc(_catl)}" data-src="{_src}">{bar}{body}</article>'

def filter_bar(cats_present):
    """EN/DE + category filter, client-side, no dependencies."""
    catbtns = "".join(f'<button class="fbtn" data-f="cat" data-v="{esc(c)}">{esc(c)}</button>' for c in CATS if c in cats_present)
    return (
      '<div class="wrap"><div class="filters">'
      '<div class="fgroup"><span class="flab">Language</span>'
      '<button class="fbtn on" data-f="lang" data-v="ALL">All</button>'
      '<button class="fbtn" data-f="lang" data-v="EN">English</button>'
      '<button class="fbtn" data-f="lang" data-v="DE">Deutsch</button></div>'
      '<div class="fgroup"><span class="flab">Category</span>'
      '<button class="fbtn on" data-f="cat" data-v="ALL">All</button>' + catbtns +
      '</div><span class="fcount" id="fcount"></span></div></div>'
      '<script>(function(){var st={lang:"ALL",cat:"ALL"};'
      'function apply(){var cards=document.querySelectorAll(".card"),n=0;'
      'cards.forEach(function(c){var okL=st.lang=="ALL"||c.dataset.lang==st.lang,'
      'okC=st.cat=="ALL"||c.dataset.cat==st.cat;var v=okL&&okC;c.style.display=v?"":"none";if(v)n++;});'
      'var fc=document.getElementById("fcount");if(fc)fc.textContent=n+" shown";}'
      'document.querySelectorAll(".fbtn").forEach(function(b){b.addEventListener("click",function(){'
      'var f=b.dataset.f;st[f]=b.dataset.v;'
      'document.querySelectorAll(\'.fbtn[data-f="\'+f+\'"]\').forEach(function(x){x.classList.remove("on");});'
      'b.classList.add("on");apply();});});apply();})();</script>')

FILTCSS = ".filters{display:flex;flex-wrap:wrap;gap:18px;align-items:center;margin:0 0 22px;padding:14px 16px;background:var(--panel);border:1px solid var(--line);border-radius:12px}.fgroup{display:flex;gap:6px;align-items:center;flex-wrap:wrap}.flab{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--faint);margin-right:4px}.fbtn{font:inherit;font-size:13px;font-weight:600;padding:5px 12px;border-radius:999px;border:1px solid var(--line);background:transparent;color:var(--mut);cursor:pointer;transition:all .12s}.fbtn:hover{border-color:var(--dark);color:var(--ink)}.fbtn.on{background:var(--dark);border-color:var(--dark);color:#fff}.fcount{margin-left:auto;font-size:13px;color:var(--faint)}.openp{margin-left:auto;font-size:12px;font-weight:700;color:var(--brand);text-decoration:none;white-space:nowrap;border:1px solid var(--line);border-radius:999px;padding:3px 10px;transition:all .12s}.openp:hover{background:var(--dark);border-color:var(--dark);color:#fff}"

def platform_page(k, cfg):
    slots = sorted(cfg["slots"], key=lambda s: (s[1], s[0]))
    done = sum(1 for i,(lang,day,r) in enumerate(slots) if f"{k}:{i}" in COPY)
    cats_present = set()
    card_list = []
    for i,(lang,day,r) in enumerate(slots):
        c = COPY.get(f"{k}:{i}")
        cats_present.add(categorize(c, c.get("keyword") if c else "", r))
        # only social platforms get per-post detail pages; blog's real detail pages are its articles
        if k in ("linkedin", "shortform", "x") and c:
            slug = f"{k}-post-{i}.html"
            card_list.append(card(k, i, lang, day, r, detail=slug))
            focused = card(k, i, lang, day, r)
            dinner = (f'<section class="ph"><div class="wrap"><a href="{k}.html" style="font-size:13px;color:var(--faint);text-decoration:none">&larr; all {esc(cfg["title"])}</a>'
                      f'<p style="color:var(--faint);font-size:13px;margin:10px 0 0"><b>Highlight any line</b> and an &ldquo;+ Add note&rdquo; button pops up. Write what should change; add your API key in the &#9998; Review panel (corner) to get an instant AI edit, or export the notes for the repo editor.</p></div></section>'
                      f'<div class="wrap" style="max-width:720px;margin:0 auto">{focused}</div>')
            (OUT / slug).write_text(shell(f"{k}.html", cfg["title"] + " · post", f"<style>{FILTCSS}</style>{dinner}"), encoding="utf-8")
        else:
            card_list.append(card(k, i, lang, day, r))
    cards = "".join(card_list)
    inner = f"""<section class="ph"><div class="wrap"><div class="eb">6-month plan</div>
<h2>{esc(cfg['title'])}</h2><p>{esc(cfg['blurb'])}</p>
<div class="count">{len(slots)} posts across 6 months · {done} finished and gated · {cfg['tag']}</div></div></section>
{filter_bar(cats_present)}
<div class="wrap"><div class="days">{cards}</div></div>"""
    (OUT / f"{k}.html").write_text(shell(f"{k}.html", cfg["title"], f"<style>{FILTCSS}</style>{inner}"), encoding="utf-8")
    return len(slots), done

FONTFACE = """
@font-face{font-family:'NM';src:url('fonts/nm-book.woff2') format('woff2');font-weight:400}
@font-face{font-family:'NM';src:url('fonts/nm-medium.woff2') format('woff2');font-weight:500}
@font-face{font-family:'NM';src:url('fonts/nm-bold.woff2') format('woff2');font-weight:700}
"""
REVEAL_JS = """
<script>
document.documentElement.classList.add('janim');
const _els=document.querySelectorAll('[data-r]');
const io=new IntersectionObserver((es)=>{es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}})},{threshold:.12});
_els.forEach(el=>io.observe(el));
setTimeout(()=>_els.forEach(el=>el.classList.add('in')),1400);
</script>"""

# ============================================================================
# FUNNEL LADDER  ·  six fully-branded landing pages mapped to the value ladder
# Neue Montreal everywhere · brand ramp · CaseWhen wordmark in a sticky header
# ============================================================================

LADDER = [
    ("scorecard.html",          "Governance &amp; Cost Scorecard", "Free"),
    ("fix-kit.html",            "Star Schema Fix Kit",             "&euro;49"),
    ("course.html",             "Foundations to Fabric",           "&euro;299"),
    ("dashboard-in-a-day.html", "Dashboard-in-a-Day",              "&euro;1,500"),
    ("team-enablement.html",    "Team Enablement",                 "&euro;4,500"),
    ("calculator.html",         "Cost Calculator",                 "Free"),
]

FUNNEL_CSS = r"""
@font-face{font-family:'NM';src:url('fonts/nm-book.woff2') format('woff2');font-weight:400;font-display:swap}
@font-face{font-family:'NM';src:url('fonts/nm-medium.woff2') format('woff2');font-weight:500;font-display:swap}
@font-face{font-family:'NM';src:url('fonts/nm-bold.woff2') format('woff2');font-weight:700;font-display:swap}
:root{
  --accent:#1D967C;--accent-d:#17836c;
  --dark:#11493F;--hero:#0e2f28;--hero2:#123c33;
  --mint:#7AC4B5;--pale:#D8F3EE;--neutral:#E9ECE8;
  --ink:#1A1615;--muted:#5b6b65;--faint:#93a09c;
  --line:#e3ece9;--bg:#ffffff;--bg2:#f5faf8;--terra:#CE8168;
}
*{box-sizing:border-box}
html{overflow-x:hidden;scroll-behavior:smooth}
body{margin:0;font-family:'NM',ui-sans-serif,-apple-system,'Segoe UI',sans-serif;color:var(--ink);background:var(--bg);line-height:1.6;-webkit-font-smoothing:antialiased;overflow-x:hidden}
a{color:inherit;text-decoration:none}
img{max-width:100%}
h1,h2,h3,h4{margin:0;font-family:'NM';font-weight:700;letter-spacing:-.02em;line-height:1.12}
p{margin:0}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px}
.narrow{max-width:768px;margin:0 auto}

/* fail-safe reveal */
html.reveal-on [data-r]{opacity:0;transform:translateY(20px);transition:opacity .7s ease,transform .7s cubic-bezier(.2,.8,.2,1)}
html.reveal-on [data-r].in{opacity:1;transform:none}
@media(prefers-reduced-motion:reduce){html.reveal-on [data-r]{opacity:1!important;transform:none!important;transition:none!important}}

/* sticky header + wordmark + ladder nav */
.fhead{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.9);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.fhead .fwrap{max-width:1200px;margin:0 auto;display:flex;align-items:center;gap:18px;padding:11px 24px;flex-wrap:wrap}
.fhead .brand img{height:26px;display:block}
.fladder{display:flex;gap:5px;margin-left:auto;overflow-x:auto;scrollbar-width:none;max-width:100%}
.fladder::-webkit-scrollbar{display:none}
.fpill{flex:none;font-size:12.5px;color:var(--muted);padding:7px 13px;border-radius:20px;white-space:nowrap;transition:background .15s,color .15s}
.fpill:hover{background:var(--pale);color:var(--dark)}
.fpill b{color:var(--faint);font-weight:600;margin-left:6px;font-size:11px}
.fpill.on{background:var(--dark);color:#fff}
.fpill.on b{color:var(--mint)}
@media(max-width:920px){.fladder{width:100%;margin-left:0;order:3;padding-top:2px}}

/* hero */
.hero{background:linear-gradient(158deg,var(--hero),var(--hero2));color:#eafaf5;padding:82px 24px 78px;position:relative;overflow:hidden}
.hero::after{content:"";position:absolute;inset:auto -12% -55% 38%;height:85%;background:radial-gradient(55% 100% at 50% 0%,rgba(122,196,181,.16),transparent 72%);pointer-events:none}
.hwrap{max-width:1080px;margin:0 auto;position:relative;z-index:1}
.hero.split .hwrap{display:grid;grid-template-columns:minmax(0,1.02fr) minmax(0,.98fr);gap:48px;align-items:center}
.hero.center .hwrap{max-width:800px;text-align:center}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--mint)}
.hero h1{font-size:clamp(32px,5.3vw,53px);color:#fff;margin:16px 0 0}
.hero .sub{font-size:clamp(16px,2.2vw,19px);color:#c4ddd4;margin:20px 0 0;max-width:52ch}
.hero.center .sub{margin-left:auto;margin-right:auto}
.pricetag{display:inline-flex;align-items:baseline;gap:10px;margin-top:22px;background:rgba(122,196,181,.12);border:1px solid rgba(122,196,181,.3);border-radius:14px;padding:11px 18px}
.pricetag .now{font-family:'NM';font-weight:700;font-size:30px;color:#fff;letter-spacing:-.02em}
.pricetag .was{font-size:16px;color:#8fb3a8;text-decoration:line-through}
.pricetag .per{font-size:13px;color:#9fc2b8}
.btnrow{display:flex;gap:12px;flex-wrap:wrap;margin-top:30px}
.hero.center .btnrow{justify-content:center}
.cta{display:inline-block;background:var(--accent);color:#fff;font-weight:700;font-size:16px;border:0;border-radius:12px;padding:15px 30px;cursor:pointer;box-shadow:0 16px 40px rgba(29,150,124,.3);transition:transform .15s,box-shadow .15s;font-family:'NM'}
.cta:hover{transform:translateY(-2px);box-shadow:0 20px 52px rgba(29,150,124,.42)}
.cta.ghost{background:rgba(255,255,255,.08);box-shadow:none;border:1px solid rgba(255,255,255,.24);color:#eafaf5}
.cta.ghost:hover{background:rgba(255,255,255,.16)}
.cta.solid-d{background:var(--dark);box-shadow:0 16px 40px rgba(17,73,63,.25)}
.heronote{font-size:13px;color:#9fc2b8;margin-top:16px}
.heronote b{color:var(--mint);font-weight:600}

/* section base */
section{padding:78px 0}
.band{background:var(--bg2)}
.deep{background:var(--dark);color:#eafaf5}
.deep h2,.deep h3{color:#fff}
.kicker{font-size:12px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--accent)}
.deep .kicker{color:var(--mint)}
h2.h2{font-size:clamp(25px,4vw,37px);margin:12px 0 0}
.lead{font-size:17px;color:var(--muted);margin-top:16px;max-width:62ch}
.deep .lead{color:#bcd8cf}
.center-head{text-align:center}
.center-head .lead{margin-left:auto;margin-right:auto}

/* feature grids */
.grid{display:grid;gap:18px;margin-top:38px}
.g2{grid-template-columns:1fr}
.g3{grid-template-columns:1fr}
.g4{grid-template-columns:1fr 1fr}
@media(min-width:740px){.g2{grid-template-columns:1fr 1fr}.g3{grid-template-columns:repeat(3,1fr)}.g4{grid-template-columns:repeat(4,1fr)}}
.feat{background:#fff;border:1px solid var(--line);border-radius:16px;padding:26px 24px}
.deep .feat{background:rgba(255,255,255,.05);border-color:rgba(255,255,255,.12)}
.feat .ic{display:inline-flex;align-items:center;justify-content:center;width:42px;height:42px;border-radius:11px;background:var(--pale);color:var(--dark);font-weight:700;font-size:17px;margin-bottom:15px}
.deep .feat .ic{background:rgba(122,196,181,.16);color:var(--mint)}
.feat h3{font-size:18px;margin:0 0 8px}
.feat p{font-size:14.5px;color:var(--muted)}
.deep .feat p{color:#bcd8cf}

/* checklist */
.checks{display:grid;gap:12px;margin-top:30px;grid-template-columns:1fr}
@media(min-width:740px){.checks{grid-template-columns:1fr 1fr}}
.chk{display:flex;gap:12px;align-items:flex-start;background:#fff;border:1px solid var(--line);border-radius:13px;padding:16px 18px}
.chk .cm{flex:0 0 auto;width:24px;height:24px;border-radius:50%;background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800}
.chk b{font-size:15px;display:block;margin-bottom:2px}
.chk span{font-size:13.5px;color:var(--muted)}

/* mock panel wrapper */
.mock{background:#fff;border:1px solid var(--line);border-radius:20px;box-shadow:0 40px 90px rgba(17,73,63,.14);overflow:hidden}
.mock .mbar{display:flex;align-items:center;gap:7px;padding:12px 16px;background:var(--bg2);border-bottom:1px solid var(--line)}
.mock .dot{width:10px;height:10px;border-radius:50%;background:#d4ded9}
.mock .mtitle{font-size:12px;color:var(--faint);margin-left:8px;font-weight:600}
.mock .mbody{padding:22px}

/* scorecard result mock */
.dial{text-align:center;margin-bottom:6px}
.dial .ring{--p:0;width:150px;height:150px;border-radius:50%;margin:0 auto;background:conic-gradient(var(--accent) calc(var(--p)*1%),#eef4f1 0);display:flex;align-items:center;justify-content:center;position:relative}
.dial .ring::before{content:"";position:absolute;inset:14px;border-radius:50%;background:#fff}
.dial .ring .val{position:relative;z-index:1;font-family:'NM';font-weight:700;font-size:36px;color:var(--dark);letter-spacing:-.02em}
.dial .ring .val small{font-size:15px;color:var(--faint);font-weight:500}
.dial .tier{font-weight:700;font-size:17px;margin-top:12px;color:var(--dark)}
.bench{margin-top:20px}
.bench .lbl{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);margin-bottom:6px}
.bench .track{height:10px;border-radius:6px;background:var(--neutral);position:relative}
.bench .fill{height:100%;border-radius:6px;background:var(--accent)}
.bench .peer{position:absolute;top:-4px;width:3px;height:18px;background:var(--dark);border-radius:2px}
.risks{margin-top:20px;border-top:1px solid var(--line);padding-top:16px}
.risks .rk{display:flex;gap:11px;align-items:flex-start;font-size:13.5px;margin:9px 0}
.risks .rk .n{flex:0 0 auto;width:22px;height:22px;border-radius:6px;background:var(--terra);color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center}
.risks .rk b{color:var(--ink)}
.risks .rk span{color:var(--muted)}

/* interactive quiz card (hero) */
.quiz{background:#fff;color:var(--ink);border-radius:20px;padding:24px 22px;box-shadow:0 40px 90px rgba(0,0,0,.34)}
.quiz .qh{font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--accent)}
.quiz h3{font-size:19px;margin:6px 0 2px;color:var(--ink)}
.quiz .qmini{font-size:13px;color:var(--muted);margin-bottom:8px}
.q{border-top:1px solid #eef2f0;padding:13px 0}
.q:first-of-type{border-top:0}
.q h4{font-size:14px;font-weight:700;margin:0 0 8px;color:var(--ink)}
.opts{display:flex;gap:7px;flex-wrap:wrap}
.opt{font-size:12.5px;border:1px solid var(--line);border-radius:9px;padding:8px 12px;cursor:pointer;transition:all .15s;user-select:none}
.opt:hover{border-color:var(--accent)}
.opt.sel{background:var(--dark);color:#fff;border-color:var(--dark)}
.qresult{margin-top:14px;border-top:2px solid #eef2f0;padding-top:14px}
.qresult .rrow{display:flex;justify-content:space-between;font-size:10.5px;color:var(--faint);font-weight:700;text-transform:uppercase;letter-spacing:.05em}
.qmeter{height:12px;border-radius:8px;background:linear-gradient(90deg,var(--terra),#e6c07a 52%,var(--accent));position:relative;margin:10px 0}
.qneedle{position:absolute;top:-5px;width:4px;height:22px;background:var(--ink);border-radius:3px;left:8%;transition:left 1s cubic-bezier(.2,.8,.2,1)}
.qtier{font-family:'NM';font-weight:700;font-size:22px;margin:6px 0 2px;color:var(--muted)}
.qnote{font-size:13px;color:var(--muted)}

/* email capture */
.formcard{max-width:520px;margin:0 auto;background:#fff;border:1px solid var(--line);border-radius:20px;padding:30px 26px;box-shadow:0 24px 60px rgba(17,73,63,.1)}
.formcard label{display:block;font-size:13px;font-weight:700;margin-bottom:8px}
.formcard input{width:100%;border:1px solid #cfe0da;border-radius:12px;padding:14px 15px;font-size:15px;font-family:inherit;color:var(--ink)}
.formcard input:focus{outline:2px solid var(--accent);border-color:var(--accent)}
.formcard .go{width:100%;margin-top:14px;background:var(--accent);color:#fff;border:0;border-radius:12px;padding:15px;font-size:16px;font-weight:700;cursor:pointer;font-family:'NM';transition:background .15s}
.formcard .go:hover{background:var(--accent-d)}
.formcard .fine{font-size:12px;color:var(--muted);margin-top:12px;text-align:center}
.mockmsg{display:none;margin-top:14px;font-size:14px;color:var(--dark);background:var(--pale);border-radius:11px;padding:13px 15px;text-align:center;font-weight:600}

/* pricing / offer card */
.buybox{max-width:560px;margin:36px auto 0;background:#fff;border:1px solid var(--line);border-radius:20px;padding:30px 28px;box-shadow:0 30px 70px rgba(17,73,63,.12)}
.buybox .bprice{display:flex;align-items:baseline;gap:12px}
.buybox .bprice .n{font-family:'NM';font-weight:700;font-size:44px;color:var(--dark);letter-spacing:-.02em}
.buybox .bprice .w{font-size:19px;color:var(--faint);text-decoration:line-through}
.buybox .bprice .per{font-size:14px;color:var(--muted)}
.buylist{margin:20px 0 0;padding:0;list-style:none}
.buylist li{display:flex;gap:10px;align-items:flex-start;font-size:14.5px;color:var(--ink);padding:8px 0;border-top:1px solid var(--line)}
.buylist li:first-child{border-top:0}
.buylist li::before{content:"\2713";color:var(--accent);font-weight:800;flex:0 0 auto}
.bump{margin-top:20px;background:#fffdf7;border:1px dashed #e6c07a;border-radius:14px;padding:16px 18px;display:flex;gap:12px;align-items:flex-start}
.bump .bx{flex:0 0 auto;width:22px;height:22px;border:2px solid var(--accent);border-radius:6px;margin-top:1px;position:relative}
.bump .bx::after{content:"\2713";position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--accent);font-weight:800;font-size:14px}
.bump b{font-size:14.5px}
.bump .bp{font-weight:700;color:var(--dark)}
.bump p{font-size:13px;color:var(--muted);margin-top:3px}
.buybox .go{width:100%;margin-top:22px;background:var(--accent);color:#fff;border:0;border-radius:12px;padding:16px;font-size:16px;font-weight:700;cursor:pointer;font-family:'NM';transition:background .15s}
.buybox .go:hover{background:var(--accent-d)}
.buybox .guff{font-size:12.5px;color:var(--muted);margin-top:12px;text-align:center}

/* file list mock */
.filelist{list-style:none;margin:0;padding:0}
.filelist li{display:flex;gap:12px;align-items:center;padding:12px 4px;border-top:1px solid var(--line);font-size:14px;min-width:0}
.filelist li:first-child{border-top:0}
.filelist .fn{min-width:0}
.filelist .fn b,.filelist .fn span{overflow-wrap:anywhere}
.filelist .ft{flex:0 0 auto;width:40px;height:40px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;color:#fff;letter-spacing:.02em}
.filelist .ft.pbix{background:#f2c811;color:#3a2f00}
.filelist .ft.pdf{background:var(--terra)}
.filelist .ft.dax{background:var(--dark)}
.filelist .ft.xls{background:var(--accent)}
.filelist .fn b{display:block;font-weight:700;color:var(--ink)}
.filelist .fn span{font-size:12.5px;color:var(--muted)}
.filelist .fsz{margin-left:auto;font-size:12px;color:var(--faint)}

/* pillars */
.pillar{background:#fff;border:1px solid var(--line);border-radius:18px;padding:28px 24px;position:relative;overflow:hidden}
.pillar::before{content:"";position:absolute;top:0;left:0;right:0;height:5px;background:var(--ac)}
.pillar .pn{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--ac)}
.pillar h3{font-size:20px;margin:8px 0 8px}
.pillar p{font-size:14.5px;color:var(--muted)}
.pillar ul{margin:14px 0 0;padding-left:18px}
.pillar li{font-size:13.5px;color:var(--ink);margin:5px 0}

/* curriculum / module list */
.modules{margin-top:34px;border:1px solid var(--line);border-radius:16px;overflow:hidden;background:#fff}
.mod{display:flex;gap:16px;padding:20px 22px;border-top:1px solid var(--line)}
.mod:first-child{border-top:0}
.mod .mnum{flex:0 0 auto;width:34px;height:34px;border-radius:9px;background:var(--pale);color:var(--dark);font-weight:700;display:flex;align-items:center;justify-content:center;font-size:14px}
.mod h4{font-size:16px;margin:0 0 4px}
.mod p{font-size:13.5px;color:var(--muted)}
.mod .mlen{margin-left:auto;font-size:12px;color:var(--faint);white-space:nowrap;padding-top:8px}

/* agenda timeline */
.agenda{margin-top:34px;position:relative}
.agenda::before{content:"";position:absolute;left:19px;top:8px;bottom:8px;width:2px;background:var(--line)}
.ag{display:flex;gap:18px;padding:12px 0;position:relative}
.ag .agt{flex:0 0 auto;width:40px;height:40px;border-radius:50%;background:var(--dark);color:#fff;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;z-index:1;text-align:center;line-height:1.1}
.ag .agc h4{font-size:16px;margin:6px 0 4px}
.ag .agc p{font-size:14px;color:var(--muted)}

/* tiers (packages) */
.tiers{display:grid;gap:20px;margin-top:38px;grid-template-columns:1fr}
@media(min-width:860px){.tiers{grid-template-columns:repeat(3,1fr);align-items:start}}
.tier{background:#fff;border:1px solid var(--line);border-radius:18px;padding:28px 24px;display:flex;flex-direction:column}
.tier.feature{border-color:var(--accent);box-shadow:0 24px 60px rgba(29,150,124,.16);position:relative}
.tier .flag{position:absolute;top:-12px;left:24px;background:var(--accent);color:#fff;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:5px 12px;border-radius:20px}
.tier .tn{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.tier h3{font-size:21px;margin:8px 0 8px}
.tier .tp{font-family:'NM';font-weight:700;font-size:30px;color:var(--dark);letter-spacing:-.02em}
.tier .tp small{font-size:14px;color:var(--muted);font-weight:500}
.tier .td{font-size:14px;color:var(--muted);margin:10px 0 16px}
.tier ul{list-style:none;margin:0 0 22px;padding:0}
.tier li{display:flex;gap:9px;align-items:flex-start;font-size:14px;padding:7px 0;border-top:1px solid var(--line)}
.tier li:first-child{border-top:0}
.tier li::before{content:"\2713";color:var(--accent);font-weight:800;flex:0 0 auto}
.tier .tcta{margin-top:auto;text-align:center;background:var(--pale);color:var(--dark);border-radius:11px;padding:13px;font-weight:700;font-size:14.5px}
.tier.feature .tcta{background:var(--accent);color:#fff}

/* calculator */
.calc{background:#fff;border:1px solid var(--line);border-radius:20px;padding:28px 26px;box-shadow:0 30px 70px rgba(17,73,63,.12)}
.calc .row{margin:20px 0}
.calc label{font-size:14px;font-weight:600;display:flex;justify-content:space-between}
.calc label b{color:var(--dark)}
.calc input[type=range]{width:100%;margin-top:10px;accent-color:var(--accent)}
.readout{margin-top:22px;background:var(--dark);color:#fff;border-radius:16px;padding:24px;text-align:center}
.readout .big{font-family:'NM';font-weight:700;font-size:clamp(38px,9vw,64px);letter-spacing:-.03em;line-height:1}
.readout .rl{color:#9fc2b8;font-size:13px;margin-top:6px}
.rsplit{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}
.rsplit .s{flex:1;min-width:130px;background:rgba(255,255,255,.08);border-radius:11px;padding:13px}
.rsplit .s b{display:block;color:#fff;font-size:19px;font-weight:700}
.rsplit .s span{font-size:12px;color:#cfe3dc}
.rrec{margin-top:14px;font-size:14px;color:#eafaf5;background:rgba(122,196,181,.14);border-radius:11px;padding:13px}

/* proof / logos */
.proof{display:grid;gap:18px;margin-top:34px;grid-template-columns:1fr}
@media(min-width:740px){.proof{grid-template-columns:1fr 1fr}}
.quote{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);border-radius:16px;padding:24px 22px}
.quote p{font-size:16px;color:#eafaf5}
.quote .who{font-size:13px;color:var(--mint);margin-top:14px;font-weight:600}
.cred{margin-top:28px;padding:20px 22px;border-radius:16px;background:rgba(122,196,181,.1);border:1px solid rgba(122,196,181,.24);font-size:14.5px;color:#cfe7df}
.cred b{color:#fff}
.logos{display:flex;gap:24px;flex-wrap:wrap;align-items:center;margin-top:14px;font-weight:800;color:#eafaf5;font-size:17px;opacity:.85}

/* faq */
.faq{margin-top:30px}
.qa{border-bottom:1px solid var(--line)}
.qa summary{list-style:none;cursor:pointer;padding:18px 0;font-size:16px;font-weight:700;display:flex;justify-content:space-between;gap:16px;align-items:flex-start}
.qa summary::-webkit-details-marker{display:none}
.qa summary .pl{flex:0 0 auto;color:var(--accent);font-weight:800;transition:transform .2s}
.qa[open] summary .pl{transform:rotate(45deg)}
.qa .a{font-size:14.5px;color:var(--muted);padding:0 0 18px;max-width:66ch}

/* bridge to next rung */
.bridge{max-width:760px;margin:0 auto;background:#fff;border:1px solid var(--line);border-radius:18px;padding:26px 26px;display:flex;gap:20px;align-items:center;flex-wrap:wrap;box-shadow:0 20px 50px rgba(17,73,63,.08)}
.bridge .bt{flex:1;min-width:240px}
.bridge .bk{font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--accent)}
.bridge h3{font-size:20px;margin:6px 0 6px}
.bridge p{font-size:14px;color:var(--muted)}
.bridge a{flex:0 0 auto}

/* final */
.final{background:linear-gradient(158deg,var(--hero),var(--hero2));color:#eafaf5;text-align:center;padding:88px 24px}
.final h2{font-size:clamp(26px,4.4vw,40px);color:#fff}
.final p{color:#c4ddd4;font-size:17px;margin:16px auto 0;max-width:52ch}

footer.ffoot{background:#0a241e;color:#7fa79b;font-size:12.5px;text-align:center;padding:34px 24px}
footer.ffoot a{color:var(--mint)}
footer.ffoot img{height:20px;opacity:.8;margin-bottom:12px}

/* ---- responsive ---- */
@media(max-width:860px){
  .hero.split .hwrap{grid-template-columns:minmax(0,1fr);gap:32px}
  .hero{padding:64px 22px 58px}
  section{padding:60px 0}
  .mock,.calc,.quiz,.buybox,.formcard{max-width:100%}
  .hero h1{font-size:clamp(30px,7.6vw,42px)}
}
@media(max-width:560px){
  .grid.g4{grid-template-columns:1fr}
  .fhead .fwrap{gap:10px;padding:11px 18px}
  .pricetag{flex-wrap:wrap;row-gap:2px}
  .bridge{padding:22px 20px}
  .filelist .fsz{display:none}
  .wrap{padding:0 20px}
}
"""

REVEAL_SCRIPT = """<script>
document.documentElement.classList.add('reveal-on');
var _r=[].slice.call(document.querySelectorAll('[data-r]'));
function _show(el){el.classList.add('in');}
var _vh=window.innerHeight||800;
// reveal anything already in (or just below) the viewport synchronously — no hero flash
_r.forEach(function(el){if(el.getBoundingClientRect().top < _vh*1.15)_show(el);});
if('IntersectionObserver' in window){
 var _io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){_show(e.target);_io.unobserve(e.target);}});},{threshold:.12});
 _r.forEach(function(el){if(el.className.indexOf('in')<0)_io.observe(el);});
}else{_r.forEach(_show);}
setTimeout(function(){_r.forEach(_show);},1000);
</script>"""

def _fav(emoji):
    return ("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
            "<text y='.9em' font-size='90'>" + emoji + "</text></svg>")

def fhead(active):
    pills = "".join(
        f'<a class="fpill {"on" if href==active else ""}" href="{href}">{name}<b>{price}</b></a>'
        for href, name, price in LADDER)
    return (f'<header class="fhead"><div class="fwrap">'
            f'<a class="brand" href="funnels.html"><img src="img/wordmark.png" alt="CaseWhen"></a>'
            f'<nav class="fladder">{pills}</nav></div></header>')

def funnel_page(slug, title, emoji, hero, body, extra_css="", extra_js=""):
    foot = ('<footer class="ffoot"><img src="img/wordmark.png" alt="CaseWhen"><br>'
            'CaseWhen &middot; Power BI, Fabric and Azure BI, Berlin &middot; '
            '<a href="funnels.html">back to the funnel</a></footer>')
    html_doc = f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<link rel="icon" href="{_fav(emoji)}">
<title>CaseWhen &middot; {esc(title)}</title>
<style>{FUNNEL_CSS}{extra_css}</style></head><body>
{fhead(slug)}
{hero}
{body}
{foot}
{REVEAL_SCRIPT}{extra_js}
</body></html>"""
    (OUT/slug).write_text(html_doc, encoding="utf-8")

# ---------- shared content blocks ----------

def proof_block(kicker="Who's behind it", head="Built by people who've fixed this before",
                q1=None, q2=None):
    q1 = q1 or ("\"We thought our reporting was fine until CaseWhen flagged that nobody actually owned "
                "the revenue number. Two weeks later finance and sales finally agreed on one figure.\"",
                "Group Controller, mid-market manufacturer")
    q2 = q2 or ("\"I forwarded their one-pager to our CFO before I'd finished my coffee. He read it, got "
                "it, and asked me to book the review. Nothing has landed a technical point that fast.\"",
                "Head of Finance, Berlin SaaS company")
    return f"""<section class="deep"><div class="wrap" data-r>
<div class="kicker">{esc(kicker)}</div><h2 class="h2">{esc(head)}</h2>
<div class="proof">
 <div class="quote"><p>{q1[0]}</p><div class="who">{esc(q1[1])}</div></div>
 <div class="quote"><p>{q2[0]}</p><div class="who">{esc(q2[1])}</div></div>
</div>
<div class="cred">CaseWhen is a Berlin Power BI and Fabric consultancy run by <b>Microsoft-certified</b>
BI engineers. We've built and repaired reporting foundations for teams at <b>Schindler</b> and
<b>Ipsen</b>, so the checks and templates here aren't theory. They're what we reach for on day one.
<div class="logos"><span>Schindler</span><span>Ipsen</span><span>WellBeauty</span></div></div>
</div></section>"""

def bridge_block(kicker, head, text, href, label):
    return f"""<section class="band"><div class="wrap" data-r>
<div class="bridge"><div class="bt"><div class="bk">{esc(kicker)}</div>
<h3>{esc(head)}</h3><p>{esc(text)}</p></div>
<a class="cta solid-d" href="{href}">{esc(label)}</a></div></div></section>"""

def faq_block(items):
    qa = "".join(
        f'<details class="qa"><summary>{esc(q)}<span class="pl">+</span></summary>'
        f'<div class="a">{esc(a)}</div></details>' for q, a in items)
    return f"""<section><div class="wrap narrow" data-r>
<div class="center-head"><div class="kicker">Questions</div>
<h2 class="h2">The honest answers</h2></div>
<div class="faq">{qa}</div></div></section>"""

def final_cta(head, sub, href, label, note):
    return f"""<section class="final" data-r>
<h2>{esc(head)}</h2><p>{esc(sub)}</p>
<div class="btnrow" style="justify-content:center"><a class="cta" href="{href}">{esc(label)}</a></div>
<div class="heronote" style="color:#9fc2b8">{esc(note)}</div></section>"""

# ============================================================================
# RUNG 0  ·  Governance & Cost Scorecard  (free, email capture)
# ============================================================================
def scorecard_page():
    hero = """<section class="hero split"><div class="hwrap">
 <div data-r>
  <div class="eyebrow">Free &middot; Governance &amp; Cost Scorecard</div>
  <h1>Score your Power BI on governance and cost in five minutes.</h1>
  <p class="sub">Answer a short set of questions and get an instant score out of 100, how you compare
  to peers, and the top three risks in your setup. It's email only, and the one-page result is built
  to forward straight to your CFO.</p>
  <div class="btnrow"><a class="cta" href="#capture">Get my score</a>
  <a class="cta ghost" href="#what">See what's in it</a></div>
  <div class="heronote">You get: <b>a score out of 100</b>, a <b>peer benchmark</b>, and your
  <b>top three risks</b>. No call, no pitch.</div>
 </div>
 <div class="quiz" data-r>
  <div class="qh">Try it now</div>
  <h3>Rate your reporting foundation</h3>
  <div class="qmini">Pick one answer per row. Your score updates as you go.</div>
  <div class="q"><h4>1. Can you name the one person who owns the revenue number on your board report?</h4>
   <div class="opts"><div class="opt" data-q="0" data-v="2">Yes, one named owner</div><div class="opt" data-q="0" data-v="1">Sort of</div><div class="opt" data-q="0" data-v="0">No</div></div></div>
  <div class="q"><h4>2. How do report changes reach the live dashboard?</h4>
   <div class="opts"><div class="opt" data-q="1" data-v="2">Dev, test, then live</div><div class="opt" data-q="1" data-v="1">Straight to live</div><div class="opt" data-q="1" data-v="0">Not sure</div></div></div>
  <div class="q"><h4>3. When did you last test row-level security on a real user?</h4>
   <div class="opts"><div class="opt" data-q="2" data-v="2">This quarter</div><div class="opt" data-q="2" data-v="1">At launch only</div><div class="opt" data-q="2" data-v="0">Never</div></div></div>
  <div class="q"><h4>4. Do you know if a Fabric capacity would be cheaper than your per-user licences?</h4>
   <div class="opts"><div class="opt" data-q="3" data-v="2">Yes, we've run the math</div><div class="opt" data-q="3" data-v="1">Roughly</div><div class="opt" data-q="3" data-v="0">No idea</div></div></div>
  <div class="qresult">
   <div class="rrow"><span>At risk</span><span>Functional</span><span>Board-ready</span></div>
   <div class="qmeter"><div class="qneedle" id="qneedle"></div></div>
   <div class="qtier" id="qtier">Answer the four questions</div>
   <div class="qnote" id="qnote">Then drop your email below for the full score and your top three risks.</div>
  </div>
 </div>
</div></section>"""

    body = f"""
<section id="what"><div class="wrap" data-r>
 <div class="center-head"><div class="kicker">What you actually get</div>
 <h2 class="h2">A real read on your reporting, in the time it takes to get a coffee</h2>
 <p class="lead">Most maturity checks are a sales call in disguise. This one isn't. You walk away with
 something you can use, whether or not you ever talk to us.</p></div>
 <div class="grid g3">
  <div class="feat"><div class="ic">/100</div><h3>A score out of 100</h3>
   <p>One number that grades your setup across ownership, change control, security, and licensing cost.
   It's the same read a technical reviewer forms in their first ten minutes, just faster and free.</p></div>
  <div class="feat"><div class="ic">vs</div><h3>A peer benchmark</h3>
   <p>See where you land against other Power BI teams of your size. Above the line, at it, or below it,
   so you know whether this is urgent or just worth a note.</p></div>
  <div class="feat"><div class="ic">3</div><h3>Your top three risks</h3>
   <p>The three places your numbers are most likely to go wrong, named and ranked. The one-page result
   spells out what to fix first, in the order that matters.</p></div>
 </div>
</div></section>

<section class="band"><div class="wrap" data-r>
 <div class="center-head"><div class="kicker">The result</div>
 <h2 class="h2">What lands in your inbox</h2>
 <p class="lead">A single page you can read in a minute and forward without explaining. No screenshots of
 your data, no jargon.</p></div>
 <div style="max-width:560px;margin:38px auto 0">
  <div class="mock">
   <div class="mbar"><span class="dot"></span><span class="dot"></span><span class="dot"></span>
    <span class="mtitle">CaseWhen &middot; Governance &amp; Cost Scorecard</span></div>
   <div class="mbody">
    <div class="dial"><div class="ring" style="--p:62"><span class="val">62<small>/100</small></span></div>
     <div class="tier">Functional, with two soft spots</div></div>
    <div class="bench"><div class="lbl"><span>Your score</span><span>Peer median 71</span></div>
     <div class="track"><div class="fill" style="width:62%"></div><div class="peer" style="left:71%"></div></div></div>
    <div class="risks">
     <div class="rk"><span class="n">1</span><div><b>No named owner for the revenue metric.</b>
      <span>Finance and sales can reconcile to different numbers.</span></div></div>
     <div class="rk"><span class="n">2</span><div><b>Changes ship straight to live.</b>
      <span>No dev or test step means a broken measure reaches the board.</span></div></div>
     <div class="rk"><span class="n">3</span><div><b>Licensing past the crossover.</b>
      <span>At 400+ viewers a Fabric capacity likely beats your per-user Pro spend.</span></div></div>
    </div>
   </div>
  </div>
 </div>
</div></section>

{proof_block()}

<section id="capture"><div class="wrap" data-r>
 <div class="center-head"><div class="kicker">Get your score</div>
 <h2 class="h2">Send me my scorecard</h2>
 <p class="lead">Email only. Your score, your peer benchmark, and your top three risks land in about a
 minute. That's the whole cost.</p></div>
 <form class="formcard" style="margin-top:34px" onsubmit="return mockSend(event)">
  <label for="email">Work email</label>
  <input id="email" type="email" placeholder="you@company.com" autocomplete="email" required>
  <button class="go" type="submit">Get my score</button>
  <div class="fine">We'll sign your NDA on request. No spam, no sales sequence, one email.</div>
  <div class="mockmsg" id="mockmsg">This is a mockup, so nothing actually sends. On the live page your
  scorecard would be on its way.</div>
 </form>
</div></section>

{faq_block([
 ("Do I need to give you access to my Power BI?","No. The scorecard runs on your answers and nothing else. We never touch your workspace, your semantic model, or your data to produce the result."),
 ("How can a short quiz tell me anything real?","Because these questions map to where trusted numbers actually go soft: ownership, change control, security, and licensing cost. If those are shaky, the reporting is shaky, and the score maps straight onto how a reviewer would grade you on day one."),
 ("Is this just a way to sell me a project?","The result is useful whether you ever talk to us or not, and plenty of people take it and fix things on their own. If your foundation is soft we do offer a fixed-price review, but that's your call to make later."),
 ("Does it really cover cost?","Yes. One of the four checks is licensing, because past roughly 350 viewers a Fabric capacity usually starts beating a stack of per-user Pro licences. If you're near that line the result flags it, and the cost calculator does the exact math."),
])}

{bridge_block("Next rung", "Scored low on the model? Start with the Fix Kit.",
   "If the scorecard flags your data model, the 49 euro Star Schema Fix Kit gives you the template, the measures, and the checklist to repair it yourself this week.",
   "fix-kit.html", "See the Fix Kit")}

{final_cta("Two minutes now, or find out in the boardroom",
   "You already know which question made you pause. Get the score, get your top three risks, and fix the soft one before someone else spots it.",
   "#capture", "Get my score", "Free · Instant score · A one-page result you can forward")}
"""
    js = """<script>
var ans={};
document.querySelectorAll('.opt').forEach(function(o){o.addEventListener('click',function(){
 var q=o.dataset.q;document.querySelectorAll('.opt[data-q="'+q+'"]').forEach(function(x){x.classList.remove('sel');});
 o.classList.add('sel');ans[q]=+o.dataset.v;render();});});
function render(){var ks=Object.keys(ans);if(!ks.length)return;var s=0;ks.forEach(function(k){s+=ans[k];});
 var pct=Math.round(s/8*100);document.getElementById('qneedle').style.left=Math.max(4,Math.min(96,pct))+'%';
 var t=document.getElementById('qtier'),n=document.getElementById('qnote');
 if(ks.length<4){t.textContent='Keep going ('+ks.length+' of 4)';t.style.color='#94a29c';return;}
 if(pct<40){t.textContent='At risk';t.style.color='#CE8168';n.textContent='A board could poke a hole in this. Your result ranks which risk to shore up first.';}
 else if(pct<75){t.textContent='Functional';t.style.color='#b8862f';n.textContent='It holds day to day, but a couple of gaps could bite. Your result ranks them.';}
 else{t.textContent='Board-ready';t.style.color='#1D967C';n.textContent='Solid. Your result confirms it and flags the one thing worth watching.';}}
function mockSend(e){e.preventDefault();document.getElementById('mockmsg').style.display='block';return false;}
</script>"""
    funnel_page("scorecard.html", "Governance & Cost Scorecard", "\U0001F4CA", hero, body, extra_js=js)

# ============================================================================
# RUNG 1  ·  Star Schema Fix Kit  (49 euro tripwire, +19 euro DAX bump)
# ============================================================================
def fixkit_page():
    hero = """<section class="hero split"><div class="hwrap">
 <div data-r>
  <div class="eyebrow">Tripwire &middot; Star Schema Fix Kit</div>
  <h1>Rebuild your Power BI model the right way, this week.</h1>
  <p class="sub">A done-for-you starter kit that turns a tangled, slow model into a clean star schema.
  A 45-minute walkthrough, a ready .pbix template, 25 tested DAX measures, and a governance checklist.
  You copy the pattern into your own report and the numbers start behaving.</p>
  <div class="pricetag"><span class="now">&euro;49</span><span class="per">one-off, yours to keep</span></div>
  <div class="btnrow"><a class="cta" href="#buy">Get the Fix Kit</a>
  <a class="cta ghost" href="#inside">See what's inside</a></div>
 </div>
 <div class="mock" data-r>
  <div class="mbar"><span class="dot"></span><span class="dot"></span><span class="dot"></span>
   <span class="mtitle">star-schema-fix-kit.zip</span></div>
  <div class="mbody"><ul class="filelist">
   <li><span class="ft pbix">PBIX</span><span class="fn"><b>star-schema-template.pbix</b><span>Fact + dimensions, a proper date table, relationships done right</span></span><span class="fsz">1 file</span></li>
   <li><span class="ft dax">DAX</span><span class="fn"><b>25-measures.dax</b><span>Time intelligence, ratios, running totals, all tested</span></span><span class="fsz">25</span></li>
   <li><span class="ft pdf">PDF</span><span class="fn"><b>governance-checklist.pdf</b><span>The 12 things to lock before anyone trusts the report</span></span><span class="fsz">2 pp</span></li>
   <li><span class="ft xls">MP4</span><span class="fn"><b>walkthrough.mp4</b><span>45 minutes, screen by screen, no filler</span></span><span class="fsz">45m</span></li>
  </ul></div>
 </div>
</div></section>"""

    body = f"""
<section id="inside"><div class="wrap" data-r>
 <div class="center-head"><div class="kicker">What's in the kit</div>
 <h2 class="h2">Everything you need to fix the model, in one download</h2>
 <p class="lead">No theory, no long course. Four things you can put to work the same afternoon you buy them.</p></div>
 <div class="grid g4">
  <div class="feat"><div class="ic">1</div><h3>45-minute walkthrough</h3>
   <p>Screen by screen, we rebuild a messy model into a star schema and explain every move, so you can
   repeat it on your own report.</p></div>
  <div class="feat"><div class="ic">2</div><h3>.pbix template</h3>
   <p>A ready Power BI file with the fact table, dimensions, a proper date table, and relationships set
   up the way they should be. Open it and copy the pattern.</p></div>
  <div class="feat"><div class="ic">3</div><h3>25 DAX measures</h3>
   <p>Time intelligence, ratios, running totals, and the ones people always get wrong, all written and
   tested. Paste them in and adjust the column names.</p></div>
  <div class="feat"><div class="ic">4</div><h3>Governance checklist</h3>
   <p>The twelve things to lock down before anyone trusts the report: ownership, security, refresh, and
   naming. One page, plain language.</p></div>
 </div>
</div></section>

<section class="band"><div class="wrap narrow" data-r>
 <div class="center-head"><div class="kicker">Why it works</div>
 <h2 class="h2">A star schema is the fix behind most "slow, wrong" reports</h2>
 <p class="lead">When a model is flat and tangled, DAX gets slow, totals stop reconciling, and Copilot
 returns nonsense. The star schema is the shape that fixes all three at once. This kit hands you the
 shape, the measures that assume it, and the checklist that keeps it clean.</p></div>
 <div class="checks">
  <div class="chk"><div class="cm">&#10003;</div><div><b>Reports get faster</b><span>Measures fold and evaluate against a clean model instead of fighting a flat one.</span></div></div>
  <div class="chk"><div class="cm">&#10003;</div><div><b>Numbers reconcile</b><span>One fact table and clear dimensions mean two teams stop getting two answers.</span></div></div>
  <div class="chk"><div class="cm">&#10003;</div><div><b>Copilot behaves</b><span>A well-named star schema is what AI needs to return the one correct number.</span></div></div>
  <div class="chk"><div class="cm">&#10003;</div><div><b>You keep the skill</b><span>You don't rent a fix, you learn the pattern and reuse it on every future report.</span></div></div>
 </div>
</div></section>

<section id="buy"><div class="wrap" data-r>
 <div class="center-head"><div class="kicker">Get it now</div>
 <h2 class="h2">One download, 49 euro, yours to keep</h2></div>
 <div class="buybox">
  <div class="bprice"><span class="n">&euro;49</span><span class="per">one-off &middot; instant download</span></div>
  <ul class="buylist">
   <li>45-minute step-by-step walkthrough</li>
   <li>.pbix star schema template with a date table</li>
   <li>25 tested DAX measures</li>
   <li>12-point governance checklist</li>
  </ul>
  <div class="bump"><div class="bx"></div><div>
   <b>Add the <span class="bp">DAX Performance Pack</span> for +&euro;19</b>
   <p>15 optimized measure patterns and a query-folding cheat sheet, for when the model is clean but the
   report still drags. Most people add this.</p></div></div>
  <button class="go" type="button" onclick="alert('Mockup only — the live page takes payment and delivers the download.')">Get the Fix Kit · &euro;49</button>
  <div class="guff">Instant download. If it doesn't save you an afternoon, reply and we'll refund you, no questions.</div>
 </div>
</div></section>

{bridge_block("Next rung", "Want the whole method, not just the model?",
   "The Fix Kit repairs one report. The Foundations-to-Fabric course teaches the full method across modeling, DAX, and governance, so you can do it on any report you own.",
   "course.html", "See the course")}

{faq_block([
 ("What version of Power BI do I need?","Power BI Desktop, any current version. The template and measures work in the free Desktop app; you don't need a paid licence to open and learn from them."),
 ("Is this a subscription?","No. It's a one-off 49 euro purchase and the files are yours to keep and reuse on as many reports as you like."),
 ("I'm not a DAX expert. Will I keep up?","Yes. The walkthrough assumes you can build a basic report but explains every model and measure decision as it goes. The 25 measures are copy-paste ready."),
 ("What's the difference between this and the course?","The Fix Kit is a focused template to repair one model fast. The course is the full method with more depth on DAX and governance plus the Fabric look. Buy the kit if you need a fix this week."),
])}

{final_cta("Stop fighting a flat model",
   "For the price of a decent lunch, get the template, the measures, and the checklist, and rebuild your report the right way this week.",
   "#buy", "Get the Fix Kit · €49", "One-off · Instant download · Refund if it doesn't save you time")}
"""
    funnel_page("fix-kit.html", "Star Schema Fix Kit", "\U0001F527", hero, body)

# ============================================================================
# RUNG 2  ·  Foundations-to-Fabric Course  (299 euro, intro 199 euro)
# ============================================================================
def course_page():
    hero = """<section class="hero split"><div class="hwrap">
 <div data-r>
  <div class="eyebrow">Course &middot; Foundations to Fabric</div>
  <h1>Model it, measure it, govern it. The full Power BI method.</h1>
  <p class="sub">A self-paced course on the three things that decide whether a Power BI report can be
  trusted: a clean star-schema model, DAX that performs, and governance that holds. It ends with a first
  look at Microsoft Fabric, so you're ready for what's next.</p>
  <div class="pricetag"><span class="now">&euro;199</span><span class="was">&euro;299</span>
   <span class="per">intro price, lifetime access</span></div>
  <div class="btnrow"><a class="cta" href="#enroll">Enroll now</a>
  <a class="cta ghost" href="#curriculum">See the curriculum</a></div>
  <div class="heronote"><b>~6 to 8 hours</b>, watch at your own pace, keep it for good.</div>
 </div>
 <div class="mock" data-r>
  <div class="mbar"><span class="dot"></span><span class="dot"></span><span class="dot"></span>
   <span class="mtitle">Foundations to Fabric &middot; curriculum</span></div>
  <div class="mbody"><ul class="filelist">
   <li><span class="ft dax">01</span><span class="fn"><b>Modeling &amp; star schema</b><span>Power Query, fact and dimension design, date tables</span></span><span class="fsz">2h</span></li>
   <li><span class="ft pbix">02</span><span class="fn"><b>Performant DAX</b><span>Context, iterators, time intelligence, tuning</span></span><span class="fsz">2h</span></li>
   <li><span class="ft pdf">03</span><span class="fn"><b>Governance</b><span>RLS, certified datasets, deployment pipelines</span></span><span class="fsz">1.5h</span></li>
   <li><span class="ft xls">04</span><span class="fn"><b>First Fabric look</b><span>Lakehouse, OneLake, when it's worth turning on</span></span><span class="fsz">1h</span></li>
  </ul></div>
 </div>
</div></section>"""

    body = f"""
<section><div class="wrap" data-r>
 <div class="center-head"><div class="kicker">The three pillars</div>
 <h2 class="h2">The three skills that separate a trusted report from a pretty one</h2>
 <p class="lead">Most Power BI training teaches buttons. This teaches the three decisions that actually
 decide whether people believe the number on the screen.</p></div>
 <div class="grid g3">
  <div class="pillar" style="--ac:#1D967C"><div class="pn">Pillar one</div>
   <h3>Modeling &amp; star schema</h3>
   <p>Shape the data so everything downstream gets easier. Power Query, a proper star schema, and a real
   date table.</p>
   <ul><li>Clean, foldable Power Query</li><li>Fact and dimension design</li><li>Date tables and relationships</li></ul></div>
  <div class="pillar" style="--ac:#11493F"><div class="pn">Pillar two</div>
   <h3>Performant DAX</h3>
   <p>Write measures that are correct and fast. Understand context, stop guessing, and tune the slow ones.</p>
   <ul><li>Row and filter context, made clear</li><li>Time intelligence that holds up</li><li>Finding and fixing slow measures</li></ul></div>
  <div class="pillar" style="--ac:#7AC4B5"><div class="pn">Pillar three</div>
   <h3>Governance + Fabric</h3>
   <p>Make the report trustworthy and ready for what's next. Security, certified datasets, and a first
   real look at Fabric.</p>
   <ul><li>Row-level security and RLS testing</li><li>Certified datasets and pipelines</li><li>Lakehouse and OneLake basics</li></ul></div>
 </div>
</div></section>

<section class="band"><div class="wrap" data-r>
 <div class="center-head"><div class="kicker">Curriculum</div>
 <h2 class="h2">Four modules, about seven hours, at your own pace</h2>
 <p class="lead">Every module ends with a real exercise on a sample dataset, so you leave having done it,
 not just watched it.</p></div>
 <div class="modules">
  <div class="mod"><span class="mnum">1</span><div><h4>Modeling and the star schema</h4>
   <p>Power Query cleanup, fact and dimension tables, a proper date table, and relationships that don't
   fight you. The foundation everything else sits on.</p></div><span class="mlen">~2h</span></div>
  <div class="mod"><span class="mnum">2</span><div><h4>DAX that performs</h4>
   <p>Row and filter context explained so it finally clicks, then time intelligence, ratios, and how to
   find and fix the measures that drag your report.</p></div><span class="mlen">~2h</span></div>
  <div class="mod"><span class="mnum">3</span><div><h4>Governance that holds</h4>
   <p>Row-level security and how to test it, certified datasets, workspace roles, and deployment
   pipelines, so changes ship safely and numbers stay trusted.</p></div><span class="mlen">~1.5h</span></div>
  <div class="mod"><span class="mnum">4</span><div><h4>A first look at Fabric</h4>
   <p>What a lakehouse and OneLake actually are, how Direct Lake changes things, and an honest read on
   when Fabric is worth turning on for a team your size.</p></div><span class="mlen">~1h</span></div>
 </div>
</div></section>

<section id="enroll"><div class="wrap" data-r>
 <div class="center-head"><div class="kicker">Enroll</div>
 <h2 class="h2">Lifetime access, intro price for now</h2></div>
 <div class="buybox">
  <div class="bprice"><span class="n">&euro;199</span><span class="w">&euro;299</span><span class="per">intro price &middot; lifetime access</span></div>
  <ul class="buylist">
   <li>All four modules, ~6 to 8 hours of video</li>
   <li>Sample datasets and exercise files</li>
   <li>The 25-measure DAX library</li>
   <li>Free updates as Fabric changes</li>
  </ul>
  <div class="bump"><div class="bx"></div><div>
   <b>Add <span class="bp">Governance Starter Templates</span> for +&euro;79</b>
   <p>RLS templates, a workspace-role matrix, a certified-dataset SOP, and a deployment-pipeline checklist.
   The paperwork done for you.</p></div></div>
  <div class="bump"><div class="bx"></div><div>
   <b>Add the <span class="bp">Fabric Readiness Track</span> for +&euro;149</b>
   <p>Lakehouse and Direct Lake migration patterns, for when you're ready to actually move.</p></div></div>
  <button class="go" type="button" onclick="alert('Mockup only — the live page enrolls you and unlocks the modules.')">Enroll now · &euro;199</button>
  <div class="guff">Seven-day money-back guarantee. Watch the first module; if it's not for you, we refund you.</div>
 </div>
</div></section>

{proof_block(head="Taught by engineers who fix this for a living",
  q1=("\"I'd used Power BI for two years and never really understood filter context. Module two fixed "
      "that in an afternoon. My month-end refresh went from nine minutes to under two.\"",
      "BI Analyst, logistics company"),
  q2=("\"We put three of our team through it before a Fabric decision. It paid for itself in the first "
      "meeting, because we finally asked the right questions.\"","Data lead, DACH retailer"))}

{bridge_block("Next rung", "Ready to do it on your own data, with your team in the room?",
   "The course teaches the method. Dashboard-in-a-Day brings us to your team for a live day on your own reports, so it lands for real.",
   "dashboard-in-a-day.html", "See Dashboard-in-a-Day")}

{faq_block([
 ("Is this live or self-paced?","Self-paced. You get lifetime access and watch on your own schedule. If you want a live day with your team on your own data, that's Dashboard-in-a-Day, the next rung up."),
 ("What level is it for?","Anyone who can build a basic Power BI report and wants to do it properly. It starts at modeling fundamentals and goes deep on DAX and governance, so beginners and self-taught analysts both get a lot from it."),
 ("Do I need a Fabric licence?","No. The Fabric module is a guided look at concepts and a readiness view; you don't need a capacity to follow along. The first three pillars work entirely in Power BI Desktop."),
 ("Can my company pay for the team?","Yes. Team seats and invoicing are available. For a whole team a custom workshop is often better value, and Microsoft co-funds Copilot enablement, so ask us before you buy in bulk."),
])}

{final_cta("Learn the method once, use it on every report",
   "Modeling, DAX, and governance are the three skills that make Power BI trustworthy. Get all three at the intro price while it lasts.",
   "#enroll", "Enroll now · €199", "Lifetime access · Seven-day guarantee · Free Fabric updates")}
"""
    funnel_page("course.html", "Foundations-to-Fabric Course", "\U0001F393", hero, body)

# ============================================================================
# RUNG 3  ·  Dashboard-in-a-Day  (~1,500 euro custom team training)
# ============================================================================
def dashboard_page():
    hero = """<section class="hero split"><div class="hwrap">
 <div data-r>
  <div class="eyebrow">Custom team training &middot; Dashboard-in-a-Day</div>
  <h1>One day, your team, your data, a dashboard you actually keep.</h1>
  <p class="sub">We come to your team for a live, hands-on day and build a real dashboard on your own
  data, not a demo dataset. Everyone leaves having done it, with a report you can put to work on Monday
  and the habits to keep it clean.</p>
  <div class="pricetag"><span class="now">&euro;1,500</span><span class="per">per day &middot; up to 10 seats</span></div>
  <div class="btnrow"><a class="cta" href="#book">Book a workshop</a>
  <a class="cta ghost" href="#agenda">See the agenda</a></div>
  <div class="heronote"><b>On your own data.</b> Microsoft co-funds Copilot enablement, so ask us about
  bringing the cost down.</div>
 </div>
 <div class="mock" data-r>
  <div class="mbar"><span class="dot"></span><span class="dot"></span><span class="dot"></span>
   <span class="mtitle">The day, at a glance</span></div>
  <div class="mbody"><ul class="filelist">
   <li><span class="ft dax">AM</span><span class="fn"><b>Model your data</b><span>Connect a real source, shape it into a star schema together</span></span><span class="fsz">9–12</span></li>
   <li><span class="ft pbix">PM</span><span class="fn"><b>Build the dashboard</b><span>Measures, visuals, and a report on your own numbers</span></span><span class="fsz">1–4</span></li>
   <li><span class="ft pdf">END</span><span class="fn"><b>Ship &amp; govern</b><span>Publish, secure, and set the rules to keep it trusted</span></span><span class="fsz">4–5</span></li>
   <li><span class="ft xls">+30d</span><span class="fn"><b>Follow-up</b><span>A recap pack and a checkpoint call after the day</span></span><span class="fsz">async</span></li>
  </ul></div>
 </div>
</div></section>"""

    body = f"""
<section id="outcome"><div class="wrap" data-r>
 <div class="center-head"><div class="kicker">The outcome</div>
 <h2 class="h2">Your team leaves with a working dashboard and the skill to build the next one</h2>
 <p class="lead">This isn't a slideshow. By the end of the day there's a real report on your real data,
 and the people who'll own it built it with their own hands.</p></div>
 <div class="grid g3">
  <div class="feat"><div class="ic">&#9632;</div><h3>A real dashboard</h3>
   <p>Built live on a source you use every day, not a sample. It's yours to keep and extend the moment
   the day ends.</p></div>
  <div class="feat"><div class="ic">&#9679;</div><h3>Skills that stick</h3>
   <p>Your team does the modeling and the measures themselves, guided step by step, so the ability stays
   in the building after we leave.</p></div>
  <div class="feat"><div class="ic">&#9650;</div><h3>Trusted from day one</h3>
   <p>We set up security, ownership, and refresh before we go, so the report is one people can rely on,
   not another orphaned file.</p></div>
 </div>
</div></section>

<section class="band"><div class="wrap" data-r>
 <div class="center-head"><div class="kicker">The agenda</div>
 <h2 class="h2">How the day runs</h2>
 <p class="lead">One facilitator, up to ten of your people, one shared screen and everyone building along.
 We adapt the pace to the room.</p></div>
 <div class="agenda" style="max-width:760px;margin-left:auto;margin-right:auto">
  <div class="ag"><div class="agt">9–12</div><div class="agc"><h4>Model your data</h4>
   <p>We connect one of your real sources, clean it in Power Query, and shape it into a star schema as a
   group. Everyone sees why the shape matters on their own numbers.</p></div></div>
  <div class="ag"><div class="agt">12–1</div><div class="agc"><h4>Lunch and questions</h4>
   <p>An informal hour to ask the awkward questions about your specific setup, licensing, or Fabric plans.</p></div></div>
  <div class="ag"><div class="agt">1–4</div><div class="agc"><h4>Build the dashboard</h4>
   <p>Measures, visuals, and layout, built live. By mid-afternoon each person has a working report on the
   data they actually care about.</p></div></div>
  <div class="ag"><div class="agt">4–5</div><div class="agc"><h4>Ship and govern</h4>
   <p>We publish, set row-level security, assign ownership, and agree the rules that keep the report
   trusted. You leave with something live, not a draft.</p></div></div>
 </div>
</div></section>

<section><div class="wrap narrow" data-r>
 <div class="center-head"><div class="kicker">Good to know</div>
 <h2 class="h2">The practical details</h2></div>
 <div class="checks">
  <div class="chk"><div class="cm">&#10003;</div><div><b>Up to 10 seats</b><span>Small enough that everyone builds, not just watches. Ideal for one team or a mixed group of report owners.</span></div></div>
  <div class="chk"><div class="cm">&#10003;</div><div><b>On your own data</b><span>We work on a real source you bring, so the output is useful the next morning, not a throwaway.</span></div></div>
  <div class="chk"><div class="cm">&#10003;</div><div><b>On-site or remote</b><span>We run it in your office or over a call, whichever suits the team. Same hands-on format either way.</span></div></div>
  <div class="chk"><div class="cm">&#10003;</div><div><b>Microsoft co-funding</b><span>For Copilot enablement, Microsoft co-funds training up to a set amount per customer. We'll help you check if you qualify.</span></div></div>
 </div>
</div></section>

{proof_block(head="Teams that did the day, not the demo",
  q1=("\"Our finance team had sat through two vendor demos and built nothing. In one day with CaseWhen "
      "they shipped a live margin dashboard on our own ERP data. It's still in use.\"",
      "CFO, manufacturing group"),
  q2=("\"The best part was watching our own analysts do it. A week later they'd built two more reports "
      "the same way, with no help from us.\"","Head of Data, DACH services firm"))}

<section id="book"><div class="wrap" data-r>
 <div class="center-head"><div class="kicker">Book it</div>
 <h2 class="h2">Bring Dashboard-in-a-Day to your team</h2>
 <p class="lead">Tell us your data source and roughly how many people, and we'll propose a date and check
 whether Microsoft co-funding can bring the cost down.</p></div>
 <div style="max-width:560px;margin:34px auto 0">
  <div class="buybox" style="margin-top:0">
   <div class="bprice"><span class="n">&euro;1,500</span><span class="per">per day &middot; up to 10 seats</span></div>
   <ul class="buylist">
    <li>A full facilitated day on your own data</li>
    <li>A working dashboard your team builds and keeps</li>
    <li>Security, ownership, and refresh set up before we leave</li>
    <li>A 30-day recap pack and a checkpoint call</li>
   </ul>
   <button class="go" type="button" onclick="alert('Mockup only — the live page opens a booking form.')">Book a workshop</button>
   <div class="guff">We'll reply within a day with dates and a co-funding check. No obligation to proceed.</div>
  </div>
 </div>
</div></section>

{bridge_block("Next rung", "One day isn't enough? Enable the whole team.",
   "If a single day whets the appetite, the Team Enablement package runs three sessions with a model and governance review and a month of async support.",
   "team-enablement.html", "See Team Enablement")}

{faq_block([
 ("What do we need to prepare?","Access to one real data source and a room, physical or virtual, with your people and their laptops. We handle the rest and send a short prep note a week ahead."),
 ("Is 1,500 euro the final price?","It's the standard day rate for up to ten seats. For Copilot enablement Microsoft co-funds training up to a set amount per customer, which can offset a large part of it. We'll help you check eligibility before you commit."),
 ("Can it be remote?","Yes. We run the same hands-on format over a call. Most teams find on-site slightly better for the energy, but remote works well and widens who can join."),
 ("What if our data is messy?","That's the point. We shape a real, imperfect source into a star schema live, so your team learns on the mess they actually have rather than a tidy sample."),
])}

{final_cta("Stop watching demos. Build the real thing.",
   "One day, your data, your team, a dashboard that's still in use next quarter. Tell us the source and we'll find a date.",
   "#book", "Book a workshop", "Up to 10 seats · On your own data · Microsoft co-funding available")}
"""
    funnel_page("dashboard-in-a-day.html", "Dashboard-in-a-Day", "\U0001F5A5", hero, body)

# ============================================================================
# RUNG 4  ·  Team Enablement & Packages  (4,500 euro + project + retainer)
# ============================================================================
def team_page():
    hero = """<section class="hero center"><div class="hwrap" data-r>
  <div class="eyebrow">Packages &middot; Team Enablement</div>
  <h1>Three ways to make Power BI stick across your whole team.</h1>
  <p class="sub">When one workshop isn't enough, these are the packages that build lasting capability:
  a multi-session enablement program, a fixed-scope first project, or an ongoing hand on the tiller.
  Pick the one that matches where your team is.</p>
  <div class="btnrow"><a class="cta" href="#tiers">See the packages</a>
  <a class="cta ghost" href="#book">Book a scoping call</a></div>
</div></section>"""

    body = f"""
<section id="tiers"><div class="wrap" data-r>
 <div class="center-head"><div class="kicker">The three packages</div>
 <h2 class="h2">From a focused program to an ongoing partnership</h2>
 <p class="lead">Every one starts with a scoping call, so what you buy is shaped around your team, your
 data, and the outcome you're after.</p></div>
 <div class="tiers">
  <div class="tier feature"><span class="flag">Most popular</span>
   <div class="tn">Enablement program</div><h3>Team Enablement</h3>
   <div class="tp">&euro;4,500</div>
   <div class="td">A structured program to level up a whole team over a few weeks.</div>
   <ul><li>Three live sessions, built around your reports</li><li>A full model and governance review</li>
   <li>30 days of async support after</li><li>A recorded library your team keeps</li></ul>
   <div class="tcta">Book a scoping call</div></div>
  <div class="tier"><div class="tn">Fixed-scope project</div><h3>Bounded-Entry Project</h3>
   <div class="tp">Fixed quote</div>
   <div class="td">A defined first project with a clear scope, price, and end date. The low-risk way to
   start working together.</div>
   <ul><li>One agreed outcome, quoted up front</li><li>Fixed price, fixed timeline</li>
   <li>Built with your team, not around them</li><li>A natural on-ramp to a retainer</li></ul>
   <div class="tcta">Scope a project</div></div>
  <div class="tier"><div class="tn">Ongoing</div><h3>Managed Retainer</h3>
   <div class="tp">&euro;2,500&#8211;4,500<small> / mo</small></div>
   <div class="td">A steady hand on your BI and governance, month to month, with a six-month minimum.</div>
   <ul><li>Ongoing model and report work</li><li>Governance and capacity oversight</li>
   <li>Priority access to our engineers</li><li>Six-month minimum, then rolling</li></ul>
   <div class="tcta">Talk about a retainer</div></div>
 </div>
</div></section>

<section class="band"><div class="wrap" data-r>
 <div class="center-head"><div class="kicker">What each includes</div>
 <h2 class="h2">Enough detail to know which one fits</h2></div>
 <div class="grid g3">
  <div class="feat"><div class="ic">1</div><h3>Team Enablement, in detail</h3>
   <p>Three live sessions spaced over a few weeks, each on your own reports. Between them we run a full
   review of your model and governance and write up what to fix. For 30 days after, your team can send
   questions and get real answers. The sessions are recorded and yours to keep.</p></div>
  <div class="feat"><div class="ic">2</div><h3>Bounded-Entry Project, in detail</h3>
   <p>We agree one specific outcome, a rebuilt model, a migrated report, a governance framework, and
   quote it up front with a fixed price and date. You get the result without signing up to an open-ended
   engagement, and both sides learn how the other works.</p></div>
  <div class="feat"><div class="ic">3</div><h3>Managed Retainer, in detail</h3>
   <p>An ongoing block of our time each month for BI development, governance, and capacity oversight, so
   your reporting keeps improving without you hiring for it. Six-month minimum so the work compounds,
   then it rolls month to month.</p></div>
 </div>
</div></section>

{proof_block(head="Teams we've enabled and kept",
  q1=("\"The bounded-entry project was the smart way in. Fixed price, clear outcome, no big commitment. "
      "Six weeks later we moved onto a retainer without a second thought.\"",
      "COO, Ipsen"),
  q2=("\"Having CaseWhen on a retainer is like having a senior BI engineer we don't have to recruit. The "
      "governance review alone caught two things that would have bitten us at year end.\"",
      "Finance Director, Schindler"))}

<section id="book" class="deep"><div class="wrap narrow center-head" data-r>
 <div class="kicker">Start here</div>
 <h2 class="h2">Book a scoping call</h2>
 <p class="lead" style="margin-left:auto;margin-right:auto">Every package starts the same way: a short
 call where we understand your team and your data, then recommend the one that fits and quote it clearly.
 No pressure, no generic proposal.</p>
 <div class="btnrow" style="justify-content:center;margin-top:28px">
  <a class="cta" href="javascript:void(0)" onclick="alert('Mockup only — the live page opens a scheduling link.')">Book a scoping call</a></div>
 <div class="heronote" style="color:#9fc2b8">30 minutes · We recommend the right package, or tell you if
 none of them fit yet.</div>
</div></section>

{faq_block([
 ("Which package should we start with?","Most teams start with either the Team Enablement program, if the goal is skill, or a Bounded-Entry Project, if there's a specific thing to fix. The retainer usually follows once we've worked together once. The scoping call is there to make this call with you."),
 ("How is the bounded-entry project priced?","It's quoted up front once we've scoped one clear outcome, so there are no surprises. The point of it is a fixed price and a fixed end date, which is why it's the low-risk way to start."),
 ("What does the retainer minimum mean?","Six months, because governance and BI improvements compound rather than land overnight. After the minimum it rolls month to month and you can stop with notice."),
 ("Can Microsoft co-funding apply here?","For the training and Copilot-enablement parts, often yes. Microsoft co-funds Copilot enablement up to a set amount per customer. We'll flag where it applies during scoping."),
])}

{final_cta("Make it stick across the team",
   "Whether you need a program, a first project, or a steady hand, it starts with one short scoping call. We'll point you to the right package or tell you honestly if it's not time yet.",
   "#book", "Book a scoping call", "30 minutes · A clear recommendation · A price you can plan around")}
"""
    funnel_page("team-enablement.html", "Team Enablement & Packages", "\U0001F91D", hero, body)

# ============================================================================
# RUNG 6  ·  Power BI Cost & Licensing Calculator  (free lead magnet -> call)
# ============================================================================
def calculator_page():
    hero = """<section class="hero split"><div class="hwrap">
 <div data-r>
  <div class="eyebrow">Free tool &middot; Cost &amp; Licensing Calculator</div>
  <h1>What your Power BI setup actually costs, on real Microsoft pricing.</h1>
  <p class="sub">Move two sliders and see the yearly number, the point where a Fabric capacity gets
  cheaper than per-user licences, and which side of that line you're on. Then, if the math looks off,
  book a call and we'll run it on your real setup.</p>
  <div class="btnrow"><a class="cta" href="#tool">Run the numbers</a>
  <a class="cta ghost" href="#call">Book a licensing call</a></div>
  <div class="heronote">Uses current <b>Power BI Pro</b> and <b>Fabric F-SKU</b> list pricing. No email to try it.</div>
 </div>
 <div id="tool" class="calc" data-r>
  <div class="row"><label>Report viewers <b id="vv">120</b></label>
   <input id="viewers" type="range" min="10" max="1200" value="120"></div>
  <div class="row"><label>Report builders <b id="bb">6</b></label>
   <input id="builders" type="range" min="1" max="60" value="6"></div>
  <div class="readout">
   <div class="big" id="cost">$0</div><div class="rl">estimated per year</div>
   <div class="rsplit">
    <div class="s"><b id="model">Per-user</b><span>cheaper model</span></div>
    <div class="s"><b id="cross">~350</b><span>viewer crossover</span></div>
   </div>
   <div class="rrec" id="rec">Move the sliders to see your recommendation.</div>
  </div>
 </div>
</div></section>"""

    body = f"""
<section><div class="wrap" data-r>
 <div class="center-head"><div class="kicker">What it tells you</div>
 <h2 class="h2">Three answers most teams are guessing at</h2>
 <p class="lead">Power BI licensing has one big fork in it, and getting it wrong costs real money every
 year. This calculator settles it in seconds.</p></div>
 <div class="grid g3">
  <div class="feat"><div class="ic">&euro;</div><h3>Your yearly number</h3>
   <p>The all-in annual cost for your mix of viewers and builders, on current list pricing. No more
   back-of-envelope guessing in a budget meeting.</p></div>
  <div class="feat"><div class="ic">&#8644;</div><h3>The crossover point</h3>
   <p>The viewer count where a Fabric capacity gets cheaper than paying per user. For most teams it sits
   around 350 viewers. See exactly where yours is.</p></div>
  <div class="feat"><div class="ic">&#8730;</div><h3>Which side you're on</h3>
   <p>A plain recommendation: stay per-user, or move to a capacity. With the two numbers side by side so
   you can defend the call.</p></div>
 </div>
</div></section>

<section class="band"><div class="wrap narrow" data-r>
 <div class="center-head"><div class="kicker">A word of honesty</div>
 <h2 class="h2">The list price is the easy part</h2>
 <p class="lead">This tool uses clean list pricing, which is enough to know which side of the line you're
 on. Your real bill depends on things a slider can't see: how many builders truly need Pro, whether
 you're overpaying for idle capacity, Premium-Per-User edge cases, and the 2026 and 2028 P-SKU to Fabric
 deadlines. That's the conversation worth having.</p></div>
 <div class="checks">
  <div class="chk"><div class="cm">&#10003;</div><div><b>Capacity right-sizing</b><span>An F64 you barely use is money burning. We check the size against your actual load.</span></div></div>
  <div class="chk"><div class="cm">&#10003;</div><div><b>Who really needs Pro</b><span>Often fewer builders need a paid seat than you think. That alone can shift the math.</span></div></div>
  <div class="chk"><div class="cm">&#10003;</div><div><b>The P-SKU deadlines</b><span>Premium P-SKUs are being retired. We map your migration before it's forced.</span></div></div>
  <div class="chk"><div class="cm">&#10003;</div><div><b>Copilot co-funding</b><span>If Copilot enablement is on the table, Microsoft co-funds the training. We factor that in.</span></div></div>
 </div>
</div></section>

{proof_block(head="We've done this math for teams like yours",
  q1=("\"The calculator said we were 40k a year past the crossover. The call confirmed it and mapped the "
      "move to a capacity. That's a real line item we got back.\"","Finance Director, DACH retailer"),
  q2=("\"We thought we needed Premium. Turned out we needed six fewer Pro seats and a right-sized "
      "capacity. CaseWhen found it in half an hour.\"","IT Manager, services company"))}

<section id="call" class="deep"><div class="wrap narrow center-head" data-r>
 <div class="kicker">Book it</div>
 <h2 class="h2">Get the licensing math done on your real setup</h2>
 <p class="lead" style="margin-left:auto;margin-right:auto">Bring your viewer and builder counts and your
 current bill. In 30 minutes we'll tell you whether you're on the right licence model, what a move would
 save, and how the P-SKU deadlines affect you.</p>
 <div class="btnrow" style="justify-content:center;margin-top:28px">
  <a class="cta" href="javascript:void(0)" onclick="alert('Mockup only — the live page opens a scheduling link.')">Book a licensing call</a></div>
 <div class="heronote" style="color:#9fc2b8">30 minutes · Real pricing on your real setup · No obligation</div>
</div></section>

{bridge_block("Not sure where to start?", "Score your whole setup, not just the cost.",
   "Cost is one of four things that decide whether your Power BI can be trusted. The free Governance and Cost Scorecard grades all four and sends your top three risks.",
   "scorecard.html", "Take the scorecard")}

{faq_block([
 ("Where does the pricing come from?","Current Microsoft list prices for Power BI Pro (per user) and Fabric F-SKU capacity. It's enough to see which side of the crossover you're on; the call refines it with your real usage."),
 ("Why is the crossover around 350 viewers?","Because a capacity is a fixed yearly cost while per-user scales with headcount. Below roughly 350 viewers, paying per user is usually cheaper; above it, the fixed capacity wins. Your exact line depends on your builder count."),
 ("Do I have to give you my email to use it?","No. The calculator runs entirely in your browser. The call is there if you want the real math on your setup, but the tool is yours to play with, no strings."),
 ("What about Premium-Per-User?","It's a real option between the two, and it matters in edge cases. The slider keeps things to the main fork, and we cover PPU properly on the call if it's relevant to you."),
])}

{final_cta("Stop guessing at the licensing bill",
   "Run the sliders now for the quick answer, then book a call to get the real math on your own setup before the next budget cycle.",
   "#call", "Book a licensing call", "Free tool · Real Microsoft pricing · No email to try it")}
"""
    js = """<script>
const PRO=14*12, F64=5000*12;
const v=document.getElementById('viewers'),b=document.getElementById('builders');
function fmt(n){return '$'+Math.round(n).toLocaleString();}
function animate(el,to){const from=+(el.dataset.v||0);const t0=performance.now();
 function f(t){const k=Math.min(1,(t-t0)/500);const val=from+(to-from)*(1-Math.pow(1-k,3));el.textContent=fmt(val);if(k<1)requestAnimationFrame(f);else el.dataset.v=to;}requestAnimationFrame(f);}
function calc(){const viewers=+v.value,builders=+b.value;
 document.getElementById('vv').textContent=viewers;document.getElementById('bb').textContent=builders;
 const perUser=(viewers+builders)*PRO;const capacity=F64+builders*PRO;const best=Math.min(perUser,capacity);
 animate(document.getElementById('cost'),best);const cap=capacity<perUser;
 document.getElementById('model').textContent=cap?'Capacity':'Per-user';
 document.getElementById('rec').textContent=cap
  ? 'At '+viewers+' viewers, a Fabric F64 capacity ('+fmt(capacity)+'/yr) beats per-user Pro ('+fmt(perUser)+'/yr). Buy capacity.'
  : 'At '+viewers+' viewers, per-user Pro ('+fmt(perUser)+'/yr) beats a capacity ('+fmt(capacity)+'/yr). Stay per-user.';}
v.addEventListener('input',calc);b.addEventListener('input',calc);calc();
</script>"""
    funnel_page("calculator.html", "Cost & Licensing Calculator", "\U0001F9EE", hero, body, extra_js=js)

# ---------- funnels index ----------
def funnels_page():
    scorecard_page(); fixkit_page(); course_page(); dashboard_page(); team_page(); calculator_page()
    # remove superseded static funnel files so nothing generic lingers
    for old in ("healthcheck.html","buyin.html","casestudy.html","governance-scorecard.html"):
        p = OUT/old
        if p.exists():
            try: p.unlink()
            except Exception: pass
    rungs=[
     ("Rung 0 &middot; Free lead magnet","Governance &amp; Cost Scorecard",
      "A five-minute assessment returns a score out of 100, a peer benchmark, and your top three risks. Email-only capture. The primary lead magnet everything points to.",
      "Controller or BI lead, not ready to book","scorecard.html","Free","#11493F"),
     ("Rung 1 &middot; &euro;49 tripwire","Star Schema Fix Kit",
      "A 45-minute walkthrough, a .pbix template, 25 tested DAX measures, and a governance checklist, plus a &euro;19 DAX Performance Pack order bump. The buyer-filter.",
      "Analyst with a slow, tangled model","fix-kit.html","&euro;49","#1D967C"),
     ("Rung 2 &middot; &euro;299 course","Foundations-to-Fabric Course",
      "Self-paced across the three pillars: modeling, performant DAX, and governance plus a first Fabric look. Intro &euro;199, with &euro;79 and &euro;149 order bumps. The pipeline engine.",
      "Self-taught analyst going pro","course.html","&euro;199","#7AC4B5"),
     ("Rung 3 &middot; &euro;1,500 workshop","Dashboard-in-a-Day",
      "A live, done-with-your-team day on your own data, up to 10 seats. Microsoft co-funds Copilot enablement. The bridge from course to services.",
      "Team lead who wants it to land","dashboard-in-a-day.html","&euro;1,500","#6F93AC"),
     ("Rung 4 &middot; &euro;4,500 and up","Team Enablement &amp; Packages",
      "Three tiers: a &euro;4,500 enablement program, a fixed-scope bounded-entry project, and a &euro;2,500 to 4,500 a month managed retainer. Book a scoping call.",
      "Buyer ready to commit","team-enablement.html","&euro;4,500","#CE8168"),
     ("Free tool &middot; buyer-intent","Cost &amp; Licensing Calculator",
      "Interactive Pro-vs-capacity math on real Microsoft pricing, showing the ~350-viewer crossover. Routes budget holders to a licensing scoping call.",
      "Budget holder sizing the spend","calculator.html","Free","#132630"),
    ]
    cards=""
    for tag,name,desc,persona,href,price,color in rungs:
        cards+=f"""<a class="fcard" href="{href}" data-r style="--ac:{color}">
        <div class="tag">{tag}</div><div class="pr">{price}</div><h3>{name}</h3><p>{desc}</p>
        <div class="who">{esc(persona)}</div><div class="cta">open the landing page &rarr;</div></a>"""
    st="""
.fgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:22px}
.fcard{display:block;text-decoration:none;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px;position:relative;overflow:hidden;transition:transform .15s,box-shadow .15s}
.fcard::before{content:"";position:absolute;top:0;left:0;right:0;height:5px;background:var(--ac)}
.fcard:hover{transform:translateY(-3px);box-shadow:0 16px 40px rgba(17,73,63,.12)}
.fcard .tag{font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--ac);margin-top:4px}
.fcard .pr{position:absolute;top:20px;right:20px;font-size:13px;font-weight:700;color:var(--dark);background:var(--pale);border-radius:20px;padding:4px 12px}
.fcard h3{font-size:20px;margin:6px 0 8px;letter-spacing:-.01em;max-width:20ch}
.fcard p{font-size:14px;color:var(--mut);margin:0}
.fcard .who{font-size:12px;color:var(--faint);margin-top:12px}
.fcard .cta{font-size:13px;font-weight:700;color:var(--dark);margin-top:8px}
[data-r]{opacity:0;transform:translateY(16px);transition:opacity .6s,transform .6s}[data-r].in{opacity:1;transform:none}
@media(max-width:760px){.fgrid{grid-template-columns:1fr}}
"""
    body=f"""<style>{st}</style>
<section class="hero"><div class="wrap"><div class="eb">CaseWhen &middot; funnel ladder</div>
<h1>The value ladder, one landing page per rung.</h1>
<p>Six full landing pages, from a free scorecard to a managed retainer, each branded the same and each
built to move a buyer to the next rung. Open any of them. Every page shares the CaseWhen wordmark, the
Neue Montreal type, and the brand colours, and ends in the right call to action for its rung.</p>
<div class="fgrid">{cards}</div></div></section>{REVEAL_JS}"""
    (OUT/"funnels.html").write_text(shell("funnels.html","Funnels",body),encoding="utf-8")

def seo_page():
    st = """
.seo .blk{border:1px solid var(--line);border-radius:14px;background:var(--card);padding:18px;margin-top:16px}
.seo .kw{font-size:12px;font-weight:700;letter-spacing:.02em;color:var(--dark);background:#eef5f2;border:1px solid var(--mid);border-radius:20px;padding:4px 11px;display:inline-block}
.seo h3{font-size:17px;margin:10px 0 2px}
.seo .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-top:12px}
.seo .chk{display:flex;align-items:center;gap:8px;font-size:13px;padding:7px 10px;border-radius:8px;background:#f4f8f6}
.seo .chk .m{width:18px;height:18px;border-radius:50%;flex:none;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff}
.seo .ok .m{background:var(--brand)}.seo .no .m{background:#c96a4f}
.seo .no{background:#faeee9}
.seo .meta{font-size:12.5px;color:var(--faint);margin-top:10px}
.seo .sec{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.seo .sec .s{font-size:11.5px;border-radius:20px;padding:3px 10px;border:1px solid var(--line)}
.seo .sec .yes{background:var(--pale);color:var(--dark);border-color:var(--mid)}
.seo .sec .miss{background:#faeee9;color:#8a4a37}
.score{font-size:12px;font-weight:700;border-radius:20px;padding:3px 11px;float:right}
.score.full{background:var(--dark);color:#fff}.score.part{background:#f4d9cd;color:#8a4a37}
.stab{width:100%;border-collapse:collapse;margin:14px 0;font-size:13.5px}
.stab th{text-align:left;background:var(--dark);color:#fff;padding:9px 11px;font-size:12px;font-weight:600}
.stab td{border-top:1px solid var(--line);padding:9px 11px;vertical-align:top}
"""
    import re as _re
    def parse_blog(md):
        fm={}; body=md
        if "---" in md:
            head,_,rest=md.partition("---")
            for ln in head.splitlines():
                m=_re.match(r"^([A-Za-z][\w ()',.&/-]*?):\s*(.*)$",ln)
                if m: fm[_re.sub(r"\s*\(.*?\)","",m.group(1)).strip().upper()]=m.group(2).strip()
            body=rest
        return fm,body
    def cov(f):
        md=(CONTENT/f).read_text(encoding="utf-8"); fm,body=parse_blog(md)
        kw=(fm.get("KEYWORD","").split("|")[0]).strip().lower()
        title=fm.get("META_TITLE",fm.get("TITLE","")); h1=fm.get("H1","") or fm.get("TITLE","") or title; desc=fm.get("META_DESC",fm.get("META","")); slug=fm.get("SLUG","")
        bl=body.lower(); words=_re.findall(r"[a-z0-9']+",bl); first100=" ".join(words[:100])
        h2s=[l for l in body.splitlines() if l.strip().startswith("## ")]
        qh2=sum(1 for l in h2s if l.strip().rstrip().endswith("?"))
        dens=round(bl.count(kw)/max(1,len(words))*100,2) if kw else 0
        secs=[s.strip() for s in _re.split(r"·|\|",fm.get("SECONDARY","")) if s.strip()]
        checks=[
            ("Keyword in meta title", kw in title.lower()),
            ("Keyword in H1", kw in h1.lower()),
            ("Keyword in first 100 words", kw in first100),
            ("Keyword in an H2 heading", any(kw in l.lower() for l in h2s)),
            ("Keyword in meta description", kw in desc.lower()),
            ("Keyword in URL slug", kw.replace(" ","-") in slug.lower()),
            (f"Density in range ({dens}%)", 0.4<=dens<=3.0),
            (f"{qh2} question-format H2s", qh2>=4),
            ("Schema markup", bool(fm.get("SCHEMA"))),
            ("Named byline", bool(fm.get("BYLINE"))),
            (f"{len(words)} words", len(words)>=1000),
            ("FAQPage schema", "faqpage" in fm.get("SCHEMA","").lower()),
            ("FAQ block", any(h in bl for h in ["häufige fragen","frequently asked","## faq"]) or bl.count("?")>=4),
            ("Comparison table", "|---" in body or "|-" in body.replace(" ","")),
            ("Internal links", any(x in bl for x in ["read next","weiterlesen","pillar-seite","pillar page"])),
        ]
        return kw,title,h1,checks,secs,bl
    blogs=[("blog-governance-framework.md","Governance"),("blog-power-bi-certification.md","Training"),("blog-bedeutung-kpi.md","KPI · DE")]
    blocks=""
    for f,cluster in blogs:
        try: kw,title,h1,checks,secs,bl=cov(f)
        except Exception: continue
        passed=sum(1 for _,ok in checks if ok); total=len(checks)
        full="full" if passed==total else "part"
        grid="".join(f'<div class="chk {"ok" if ok else "no"}"><span class="m">{"✓" if ok else "!"}</span>{esc(lbl)}</div>' for lbl,ok in checks)
        secchips="".join(f'<span class="s {"yes" if s.lower() in bl else "miss"}">{esc(s)} {"✓" if s.lower() in bl else "add"}</span>' for s in secs)
        blocks+=f"""<div class="blk"><span class="score {full}">{passed}/{total} placed</span>
<span class="kw">{esc(kw)}</span> · <span style="color:var(--faint);font-size:12px">{esc(cluster)}</span>
<h3>{esc(h1 or title)}</h3>
<div class="grid">{grid}</div>
<div class="meta">Secondary keyword varieties (the related terms Google clusters):</div>
<div class="sec">{secchips or '<span class="s miss">none listed</span>'}</div></div>"""
    reopt = """
<section class="ph" style="margin-top:30px"><div class="wrap"><div class="eb">Existing blog · re-optimization</div>
<h2>What we'd attack on the 44 live posts</h2>
<p style="color:var(--mut);font-size:15px;margin:10px 0 0;max-width:66ch">A read-only audit of every live post on casewhen.co. Nothing in production was changed. The good news: titles, URLs, schema, length, and bylines are already solid, so we don't touch those. The wins are a few high-leverage gaps repeated across the whole blog.</p>
<table class="stab" style="margin-top:16px"><tr><th>Gap</th><th>Where</th><th>Why it matters</th></tr>
<tr><td><b>No FAQPage schema</b></td><td>0 of 44 — even the ~9 with a visible FAQ</td><td>Free rich-result + AI-citation win; content already there, only the markup is missing</td></tr>
<tr><td><b>No FAQ block</b></td><td>~35 posts</td><td>Misses People-Also-Ask real estate and long-tail questions</td></tr>
<tr><td><b>Almost no internal linking</b></td><td>1-2 in-body links per post; no pillar/cluster structure</td><td>The biggest structural gap — link equity isn't flowing, topical authority isn't signalled</td></tr>
<tr><td><b>Missing comparison tables</b></td><td>Pricing, certification, performance posts</td><td>Tables win the featured snippet for "vs / cost / pricing" searches</td></tr>
<tr><td><b>Duplicate pages</b></td><td>two Premium-capacity URLs</td><td>Splits ranking signal — consolidate + 301 redirect</td></tr>
<tr><td><b>Stale 2024 cohort</b></td><td>14 strategy/reporting posts</td><td>2026 pricing/Fabric facts likely outdated — refresh and genuinely re-date</td></tr></table>
<div class="funnel" style="font-size:14px;color:#33372f;background:var(--pale);border-left:3px solid var(--brand);border-radius:0 8px 8px 0;padding:12px 14px;margin-top:16px"><b>The order of attack:</b> (1) two template fixes that touch every post — a reusable FAQPage schema block + flip og:type to article; (2) fix the duplicate with a 301; (3) add FAQ blocks tier by tier, starting with the BOFU money pages (vs / pricing / certification); (4) build three internal-link clusters (pricing-comparison, strategy-governance, DAX) each pointing to a pillar; (5) add the missing tables; (6) refresh the 2024 cohort last. Steps 1 and 3 alone touch all 44 posts for the least work.</div>
</div></section>"""
    body=f"""<style>{st}</style>
<section class="hero"><div class="wrap"><div class="eb">CaseWhen · SEO</div>
<h1>Proof every post hits its keywords.</h1>
<p>Two things here: proof that each post we write places its keyword everywhere Google and AI answers
look and clears the same audit we run on the existing blog, and the plan to re-optimize that existing
blog. Note that every post we make already carries FAQPage schema, an FAQ block, a comparison table,
and internal links, the exact gaps the live blog is missing. Green means it is there.</p></div></section>
<div class="wrap seo">{blocks}{reopt}
<div class="funnel" style="font-size:14px;color:#33372f;background:var(--pale);border-left:3px solid var(--brand);border-radius:0 8px 8px 0;padding:12px 14px;margin:18px 0 40px">
<b>How this is enforced:</b> every article runs through the ship gate before it appears here. The gate
hard-fails any post missing the keyword in the H1, the first 100 words, a question H2, the meta
description, the slug, or the schema, so a post cannot ship under-optimized. The grid above is that
gate's output, made visible.</div></div>"""
    (OUT/"seo.html").write_text(shell("seo.html","SEO coverage",body),encoding="utf-8")

def pricing_page():
    st = """
.pnote{background:#fff6ec;border:1px solid #f0d8b8;border-left:4px solid #d98a3d;border-radius:0 10px 10px 0;padding:14px 16px;margin:18px 0;font-size:14px;color:#6b4a22}
.ladder{display:flex;flex-direction:column;gap:10px;margin:16px 0}
.rung{display:grid;grid-template-columns:150px 1fr;gap:16px;border:1px solid var(--line);border-radius:12px;padding:14px 16px;background:var(--card)}
.rung .amt{font-weight:800;font-size:18px;color:var(--dark)}
.rung .amt small{display:block;font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--faint);margin-bottom:2px}
.rung h3{font-size:16px;margin:0 0 4px}
.rung p{font-size:13.5px;color:var(--mut);margin:0}
.rung .bump{font-size:12.5px;color:var(--faint);margin-top:5px}
.otab{width:100%;border-collapse:collapse;margin:12px 0;font-size:13.5px}
.otab th{text-align:left;background:var(--dark);color:#fff;padding:9px 11px;font-size:12px}
.otab td{border-top:1px solid var(--line);padding:9px 11px;vertical-align:top}
.why{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:12px}
.why .w{border:1px solid var(--line);border-radius:12px;padding:14px 16px;background:var(--card)}
.why .w b{color:var(--dark)}
@media(max-width:760px){.rung{grid-template-columns:1fr}.why{grid-template-columns:1fr}}
"""
    rungs = [
      ("Free","Governance & Cost Scorecard","A 5-minute interactive self-assessment (12-15 questions on model health, DAX, RLS, refresh ownership, Fabric readiness). Output: a score out of 100, a peer benchmark, and the top 3 risks. Email-only to unlock.","Email capture. The whole funnel starts here."),
      ("&euro;49","Star Schema Fix Kit","A 45-minute walkthrough plus a .pbix template (star schema, date table, 25 DAX measures) and a governance checklist. Sold on the scorecard thank-you page.","Order bump +&euro;19: DAX Performance Pack (15 optimized patterns + query-folding cheat sheet)."),
      ("&euro;299","Foundations to Fabric course","~6-8h self-paced on the three highest-demand pillars: modeling and star schema, performant DAX, governance and a first Fabric look. Intro price &euro;199. The pipeline engine.","Bump +&euro;79 Governance Starter Templates; upsell +&euro;149 Fabric Readiness Track."),
      ("&euro;1,500","Dashboard-in-a-Day (your team)","Live, done-with-your-team, on your own data, ~10 seats. The deliberate bridge from course to services, a scoping session disguised as training.","Tier above: Team Enablement Package &euro;4,500 (3 sessions + model/governance review + 30 days async)."),
      ("Project","Bounded-entry first project","A fixed-scope, fixed-price first engagement so a new client can start without signing a big open-ended contract.","Designed to convert into the retainer once trust is proven."),
      ("&euro;2,500-4,500/mo","Managed BI & governance retainer","Ongoing model, governance, Fabric and Azure work. 6-month minimum. Then full project consulting above it.","The durable revenue line the whole ladder climbs toward."),
    ]
    ladder = "".join(
      f'<div class="rung"><div class="amt"><small>Rung {i}</small>{amt}</div><div><h3>{name}</h3><p>{desc}</p><div class="bump">{bump}</div></div></div>'
      for i,(amt,name,desc,bump) in enumerate(rungs))
    offers = [
      ("Power BI Development & Dashboards","Core","Done-for-you semantic models, DAX, RLS, refresh, trusted usable reports. Highest buyer-value cluster."),
      ("Data Modeling / the One Agreed Number","Lead offer","Fix the semantic model so people and Copilot return one correct number. The AI-readiness wedge."),
      ("Azure Data Platform & Warehousing","Core (US-weighted)","Azure Data Factory, Synapse and warehouse, pipelines, the plumbing BI stands on."),
      ("Microsoft Fabric Adoption & Capacity FinOps","Core (DACH-weighted)","Fabric setup, capacity right-sizing and cost control, Premium P-SKU to Fabric migration."),
      ("Governance & Trusted BI (+ AI-output governance)","Core, rising","RLS, governance frameworks, lineage, trusted numbers, and governing what Copilot returns."),
      ("Reporting Automation & Migrations","Supporting","Automate manual and Excel reporting; Tableau to Power BI, on-prem to Fabric, SSIS to Azure."),
      ("Training & Enablement (Copilot supervision)","Supporting, top-of-funnel","Productized Power BI, Fabric and Copilot-supervision courses. Microsoft co-funds Copilot training."),
    ]
    otab = "".join(f'<tr><td><b>{n}</b></td><td>{tag}</td><td>{d}</td></tr>' for n,tag,d in offers)
    body = f"""<style>{st}</style>
<section class="hero"><div class="wrap"><div class="eb">CaseWhen &middot; offers &amp; pricing</div>
<h1>What CaseWhen sells, and the pricing behind it.</h1>
<p>The seven offers, the value ladder from a free scorecard up to a managed retainer, and the reasoning
for each price. Every post and script on this site points at one of these.</p></div></section>
<div class="wrap">
<div class="pnote"><b>Proposed, not final.</b> These prices are researched starting points to react to.
CaseWhen has the final say on every number here. Nothing is set, and we expect you to move them.</div>
<div class="eb">The seven offers</div>
<table class="otab"><tr><th>Offer</th><th>Role</th><th>What it is</th></tr>{otab}</table>
<div class="eb" style="margin-top:26px">The value ladder</div>
<p style="color:var(--mut);font-size:14px;margin:6px 0 0">Each rung is a small yes that makes the next one easier. The bridges between rungs are where funnels usually die, so each has a deliberate next step.</p>
{ladder}
<div class="eb" style="margin-top:26px">Why these prices (the logic)</div>
<div class="why">
<div class="w"><b>Free scorecard, email-only.</b> An interactive assessment beats a static PDF, and a one-field form converts far better than a two-field one (about 4.4% vs 2.9%). We profile the lead after capture, not before.</div>
<div class="w"><b>&euro;49 tripwire as a buyer filter.</b> A small paid yes separates real buyers from browsers and pays for the traffic. It is tightly tied to the services so it scopes the next step, not a random product.</div>
<div class="w"><b>&euro;299 course as the pipeline.</b> It is both revenue and lead-gen. It teaches the three things buyers search for most, then the &quot;now do it on your data&quot; bridge invites the mid-ticket.</div>
<div class="w"><b>&euro;1,500 mid-ticket scopes the high-ticket.</b> Dashboard-in-a-Day on the client's own data is a live scoping session. It de-risks the retainer for both sides before anyone signs a big number.</div>
<div class="w"><b>US vs DACH framing differs.</b> US and UK buyers respond to build-first, direct-to-call. DACH buyers respond to education and workshop-first, in German, anchored on modeling and governance.</div>
<div class="w"><b>AI is the trigger, not a line item.</b> Copilot and Fabric AI only pay off on governed data, so the AI conversation feeds offers 2, 4 and 5. We never sell &quot;AI consulting&quot; as its own thing.</div>
</div>
</div>"""
    (OUT / "pricing.html").write_text(shell("pricing.html", "Pricing", body), encoding="utf-8")

def strategy_page():
    st = """
.goal{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:18px}
.goal .g{border:1px solid var(--line);border-radius:14px;padding:18px;background:var(--card)}
.goal .g .n{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--brand)}
.goal .g h3{font-size:18px;margin:6px 0 6px}
.goal .g p{font-size:13.5px;color:var(--mut);margin:0}
.stab{width:100%;border-collapse:collapse;margin:14px 0;font-size:13.5px}
.stab th{text-align:left;background:var(--dark);color:#fff;padding:9px 11px;font-size:12px;font-weight:600}
.stab td{border-top:1px solid var(--line);padding:9px 11px;vertical-align:top}
.stab td.pct{font-weight:700;color:var(--dark);white-space:nowrap}
.bar{height:8px;background:var(--pale);border-radius:6px;overflow:hidden;margin-top:5px;max-width:220px}
.bar span{display:block;height:100%;background:var(--brand)}
.funnel{font-size:14px;color:#33372f;background:var(--pale);border-left:3px solid var(--brand);border-radius:0 8px 8px 0;padding:12px 14px;margin-top:14px}
@media(max-width:760px){.goal{grid-template-columns:1fr}}
"""
    def barrow(label, pct, note=""):
        return f'<tr><td>{esc(label)}</td><td class="pct">{pct}%</td><td><div class="bar"><span style="width:{pct}%"></span></div>{("<div style=\"font-size:12px;color:var(--faint);margin-top:4px\">"+esc(note)+"</div>") if note else ""}</td></tr>'
    # Target split after the Aug-2026 rebalance (opener-and-proof doctrine §4) — buyer-pain first, AI + migration added
    blog_topics = [("Governance & trust",16),("AI & Copilot",12),("Close & finance",12),("Dashboards & adoption",12),("Pricing & licensing",12),("Migration",10),("Fabric & Azure",10),("KPI & modeling",9),("Hiring & consulting",7)]
    li_topics = blog_topics
    sf_topics = blog_topics
    body = f"""<style>{st}</style>
<section class="hero"><div class="wrap"><div class="eb">CaseWhen · content strategy</div>
<h1>The split, the volumes, and the goal.</h1>
<p>What we publish, how much of each, and why. Every number below comes from the keyword and cadence
plan; the format mix comes from what actually drives engagement, saves, and search rankings for a
Power BI audience.</p></div></section>

<section class="ph"><div class="wrap"><div class="eb">The goal</div><h2>Three jobs, one funnel</h2>
<div class="goal">
<div class="g"><div class="n">1 · Get found</div><h3>Rank on Google and get cited by AI</h3><p>Blog articles answer a real search term in the first lines, with a table and FAQ, so we win the snippet and get quoted by ChatGPT, Claude, and Perplexity. This is the discovery engine.</p></div>
<div class="g"><div class="n">2 · Build authority</div><h3>Founders BI leaders trust</h3><p>Austin and Saju post opinion and real-release reactions on LinkedIn, backed by YouTube and case studies. This is the layer a referred buyer checks before they call.</p></div>
<div class="g"><div class="n">3 · Reach & saves</div><h3>Be seen by everyone who reports a number</h3><p>Short-form video and carousels reach far beyond people already searching, and earn saves that compound. This is top of funnel.</p></div>
</div>
<div class="funnel"><b>The funnel:</b> short-form reach → LinkedIn and YouTube authority → blog gets found and converts buyer-intent searches → a booked, fixed-price Reporting Foundation Review.</div>
</div></section>

<section class="ph"><div class="wrap"><div class="eb">At a glance</div><h2>What we publish each month</h2>
<table class="stab"><tr><th>Channel</th><th>Volume / month</th><th>Lead formats</th><th>Primary goal</th></tr>
<tr><td><b>Blog</b> (casewhen.co)</td><td>~43 (30 EN daily + 13 DE, 3×/wk)</td><td>Direct-answer + table + FAQ · how-to · "X vs Y"</td><td>Get found (SEO + AI citation)</td></tr>
<tr><td><b>LinkedIn</b></td><td>~26 (Austin EN + Saju DE, ~3×/wk each)</td><td>Contrarian opinion · numbered carousel · case study</td><td>Authority + reach</td></tr>
<tr><td><b>Short-form video</b></td><td>~30 (script + captions; EN + DE) · <b>reposted to X + Threads</b></td><td>Numbered countdown · mistake-callout · before/after</td><td>Reach + saves</td></tr>
<tr><td><b>YouTube</b></td><td>~8 (2×/wk, EN + DE)</td><td>Outcome-led tutorial · contrarian thesis</td><td>Deep authority + evergreen search</td></tr>
<tr><td><b>X / Twitter + Threads</b></td><td>~4 native/wk + <b>every short-form and carousel reposted</b></td><td>Numbered roadmap · newsjack · reposted video + carousels</td><td>Timeliness + free extra reach</td></tr>
</table>
<div class="funnel" style="margin-top:14px"><b>Reposting (made once, shown four times):</b> every short-form video and every carousel graphic is reposted to X and Threads with a platform-native caption, on top of its home platform. LinkedIn carousels also cross-post to Instagram. One asset, several surfaces, almost no extra work.</div></div></section>

<section class="ph"><div class="wrap"><div class="eb">Blog</div><h2>~43 articles a month · what they're about</h2>
<p class="sd" style="color:var(--mut);font-size:15px;margin:8px 0 0">Format mix: ~70% practitioner how-to and direct-answer (the search-harvest base), ~20% buyer-intent money pages (cost, licensing, "vs"), ~10% flagship authority (the governance framework and pillars). English daily to build the search footprint; German three times a week, where a named-author byline is the one thing no local competitor does.</p>
<table class="stab"><tr><th>Topic</th><th>Share</th><th></th></tr>{''.join(barrow(t,p) for t,p in blog_topics)}</table>
<div class="funnel"><b>Why this split:</b> KPI and training are the highest-volume searches, so they harvest the most organic traffic. Pricing and Azure are lower volume but higher buyer-intent, so they convert. Governance is small in volume but is the flagship authority piece everything links back to.</div></div></section>

<section class="ph"><div class="wrap"><div class="eb">LinkedIn</div><h2>~26 founder posts a month</h2>
<p class="sd" style="color:var(--mut);font-size:15px;margin:8px 0 0">Format mix: ~40% plain-text contrarian / opinion (our highest-reach format), ~30% numbered carousel (the save-and-reference engine), ~20% story and real-release reaction, ~10% stat or quote card. Austin posts in English, Saju in German on a different rhythm, so the combined founder feed shows up 5-6× a week.</p>
<table class="stab"><tr><th>Topic</th><th>Share</th><th></th></tr>{''.join(barrow(t,p) for t,p in li_topics)}</table>
<div class="funnel"><b>Why this split:</b> a defensible contrarian take on a real Microsoft release is the single highest-engagement post we can make, so opinion leads. Carousels earn the saves. The mix spans every cluster so the founders read as broad Power BI authorities, not one-note.</div></div></section>

<section class="ph"><div class="wrap"><div class="eb">Short-form video</div><h2>~30 scripts a month</h2>
<p class="sd" style="color:var(--mut);font-size:15px;margin:8px 0 0">Format mix: ~40% numbered countdown carousels (built for saves), ~35% mistake-callouts ("are you still doing this?", built for saves and shares), ~25% before/after and relatable moments (built for reach). Each script is built for one job — saves, shares, or reach — because on short-form those come from different content.</p>
<table class="stab"><tr><th>Topic</th><th>Share</th><th></th></tr>{''.join(barrow(t,p) for t,p in sf_topics)}</table>
<div class="funnel"><b>Why this split:</b> KPI and training are the broadest, most-searched topics, so they carry reach at the top of the funnel; pricing and Azure bring in the buyers. Numbered countdowns keep viewers to the payoff, and the callouts get the saves that the algorithm rewards.</div></div></section>
"""
    (OUT / "strategy.html").write_text(shell("strategy.html", "Strategy", body), encoding="utf-8")

def visuals_page():
    D = "img/decks/"
    def deck_strip(prefix, n):
        imgs = "".join(f'<img src="{D}{prefix}-{i}.png" loading="lazy" alt="{prefix} slide {i}">' for i in range(1, n+1))
        return f'<div class="vstrip">{imgs}</div><div class="vhint">← swipe through all {n} slides →</div>'
    def qgal(slugs):
        imgs = "".join(f'<img src="{D}quote-{s}.png" loading="lazy" alt="quote">' for s in slugs)
        return f'<div class="vgal">{imgs}</div>'
    quotes = ["rls-viewas","incremental-refresh","deployment-pipelines","onelake-shortcut","power-query","training-starschema"]
    body = f"""<section class="ph"><div class="wrap"><div class="eb">Visuals</div>
<h2>Carousels and cards</h2>
<p>The carousels that carry the posts on LinkedIn and Instagram. Each is a full seven-slide deck:
a cover that states the payoff, five slides that each teach one idea with a headline and an
explanation, and a save slide. Swipe each one. Every line passed the same language checks as the
written posts, and each slide carries one real, concrete specific.</p></div></section>
<div class="wrap">
 <div class="vsec"><div class="vname">Governance checklist <span>· 5 signs your Power BI numbers won't survive a board review</span></div>{deck_strip("governance", 7)}</div>
 <div class="vsec"><div class="vname">Migration: myth vs reality <span>· what actually transfers from Tableau to Power BI</span></div>{deck_strip("migration", 7)}</div>
 <div class="vsec"><div class="vname">Power BI licensing <span>· the 350-viewer line where a Fabric capacity beats per-user pricing</span></div>{deck_strip("pricing", 7)}</div>
 <div class="vsec"><div class="vname">Quote cards <span>· four self-contained founder insights, one topic each</span></div>{qgal(quotes)}</div>
</div>"""
    (OUT / "visuals.html").write_text(shell("visuals.html", "Visuals", body), encoding="utf-8")

BLOGDIR = Path(r"J:\Claude Code\casewhen-research\content\w-batch03-blogs")
BUYERBLOG = Path(r"J:\Claude Code\casewhen-research\content\w-buyer-blogs")
CADENCEBLOG = Path(r"J:\Claude Code\casewhen-research\content\w-cadence-blogs")

def _fm_body(md):
    fm = {}; body = md
    if "---" in md:
        head, _, rest = md.partition("---")
        for ln in head.splitlines():
            m = re.match(r"^([A-Za-z][\w ()',.&/-]*?):\s*(.*)$", ln)
            if m: fm[re.sub(r"\s*\(.*?\)", "", m.group(1)).strip().upper()] = m.group(2).strip()
        body = rest
    return fm, body

def article_chart(kw):
    k = (kw or "").lower()
    if any(w in k for w in ["train","cert","course","class","tutorial","learn","schulung"]):
        title, src = "Business spreadsheets used in decision-making", "Poon et al. (peer-reviewed), 2024"
        data = [("Error-free", 6, "6%"), ("Contain errors", 94, "94%")]
    elif any(w in k for w in ["pric","licens","cost"," pro","premium","capacity"]):
        title, src = "Power BI Pro list price, per user per month", "Microsoft, 2025 price update"
        data = [("2024", 10, "$10"), ("2025", 14, "$14")]
    elif any(w in k for w in ["azure","fabric","migration","datenmodell","modellierung","onelake"]):
        title, src = "Organizations with data good enough to use for AI", "Precisely & Drexel LeBow, 2025"
        data = [("Ready", 12, "12%"), ("Not ready", 88, "88%")]
    elif any(w in k for w in ["kpi","governance","trust","definition","dashboard","reporting","daten"]):
        title, src = "Organizations that fully trust their data", "Precisely & Drexel LeBow, 2025"
        data = [("Trust it", 33, "33%"), ("Do not", 67, "67%")]
    else:
        title, src = "Regular business decisions made on gut feel, not data", "BARC"
        data = [("On data", 42, "42%"), ("On gut feel", 58, "58%")]
    maxv = max(v for _, v, _ in data)
    bars = "".join(f'<div class="cbar"><span class="cl">{esc(l)}</span><div class="ctrack">'
                   f'<div class="cfill" style="width:{int(v/maxv*100)}%"></div></div>'
                   f'<span class="cv">{esc(d)}</span></div>' for l, v, d in data)
    return f'<figure class="achart"><figcaption>{esc(title)}</figcaption>{bars}<div class="csrc">Source: {esc(src)}</div></figure>'

ARTCSS = """
.article-wrap{max-width:760px;margin:0 auto}
.achart{margin:20px 0;padding:18px 20px;background:var(--pale);border-radius:14px}
.achart figcaption{font-weight:700;font-size:15px;color:var(--dark);margin-bottom:12px}
.cbar{display:grid;grid-template-columns:120px 1fr 54px;align-items:center;gap:10px;margin:8px 0;font-size:13px}
.cbar .cl{color:#33372f}.cbar .cv{font-weight:700;color:var(--dark);text-align:right}
.ctrack{background:#fff;border-radius:8px;height:22px;overflow:hidden}
.cfill{height:100%;background:var(--brand);border-radius:8px}
.csrc{font-size:11.5px;color:var(--faint);margin-top:10px}
.geo{margin:26px 0 10px;border-top:1px solid var(--line);padding-top:18px}
.geo h3{font-size:16px;margin:0 0 8px}
.geo .chips{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.geo .chips .c{font-size:12px;border-radius:20px;padding:3px 10px;background:var(--pale);color:var(--dark);border:1px solid var(--mid)}
.geo .plc{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.geo .plc .p{font-size:12px;color:var(--dark)}
.geo .plc .p::before{content:"\\2713 ";color:var(--brand);font-weight:700}
.geo p{font-size:13.5px;color:var(--mut);margin:8px 0 0}
/* blog grid — real 01-blog-cover thumbnails, rotating colours */
.bgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;padding:24px 0 60px}
.bcard{display:block;border-radius:12px;overflow:hidden;box-shadow:0 6px 20px rgba(17,73,63,.10);transition:transform .14s,box-shadow .14s;background:var(--card)}
.bcard:hover{transform:translateY(-3px);box-shadow:0 16px 42px rgba(17,73,63,.20)}
.bcard img{width:100%;height:auto;display:block}
.btile{aspect-ratio:4/5;display:flex;flex-direction:column;justify-content:space-between;padding:18px;background:linear-gradient(135deg,var(--dark),var(--brand))}
.btile .btcat{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,.72)}
.btile .bth{font-size:18px;font-weight:700;line-height:1.25;color:#fff}
@media(max-width:640px){.bgrid{grid-template-columns:1fr}}
"""

GAPBLOG = Path(r"J:\Claude Code\casewhen-research\content\w-gapfill-blogs")
def blog_articles_and_grid():
    gapfill = sorted(GAPBLOG.glob("**/*.md")) if GAPBLOG.exists() else []
    buyer = gapfill + (sorted(BUYERBLOG.glob("**/*.md")) if BUYERBLOG.exists() else [])
    cadence = sorted(CADENCEBLOG.glob("**/*.md")) if CADENCEBLOG.exists() else []
    rest = cadence + sorted(BLOGDIR.glob("*.md"))
    def is_training(f):
        k = f.stem.lower()
        return any(w in k for w in ["cert","train","course","class","tutorial","learn","exam","analyst","schulung","coursera"])
    training = [f for f in rest if is_training(f)]
    other = [f for f in rest if not is_training(f)]
    # BUYER-WEIGHTED grid: buyer/business-side articles first, then practitioner, training capped
    # generate a page for EVERY blog (so none keeps a stale footer), dedup by stem
    allblogs = buyer + other + training
    seen_stem = set(); files = []
    for f in allblogs:
        if f.stem in seen_stem: continue
        seen_stem.add(f.stem); files.append(f)
    grid_stems = seen_stem  # everything visible: every blog gets a card, buyer-first order
    cards = []; cats_present = set()
    for f in files:
        md = f.read_text(encoding="utf-8"); fm, body = _fm_body(md)
        kw = (fm.get("KEYWORD", "").split("|")[0]).strip()
        h1 = fm.get("H1", "") or fm.get("META_TITLE", "")
        cluster = fm.get("CLUSTER", "") or ("KPI" if "kpi" in kw.lower() else "Power BI")
        art = md_to_html(md).replace('class="body article annotatable"',
                                     f'class="body article annotatable" data-src="{esc(reposrc(f))}"', 1)
        # insert the chart right after the Quick Answer box (or after H1)
        chart = article_chart(kw)
        if 'class="qa"' in art:
            art = re.sub(r'(</div>)', r'\1' + chart, art, count=1)
        else:
            art = re.sub(r'(</h1>)', r'\1' + chart, art, count=1)
        # keyword / GEO section
        bl = body.lower(); words = re.findall(r"[a-z0-9']+", bl)
        secs = [s.strip() for s in re.split(r"·|\|", fm.get("SECONDARY", "")) if s.strip()]
        placements = [n for n, ok in [
            ("meta title", kw.lower() in fm.get("META_TITLE", "").lower()),
            ("H1", kw.lower() in h1.lower()),
            ("first 100 words", kw.lower() in " ".join(words[:100])),
            ("an H2", any(kw.lower() in l.lower() for l in body.splitlines() if l.strip().startswith("## "))),
            ("meta description", kw.lower() in fm.get("META_DESC", fm.get("META", "")).lower()),
            ("URL slug", kw.lower().replace(" ", "-") in fm.get("SLUG", "").lower()),
        ] if ok]
        geo = (f'<div class="geo"><h3>Keywords this article targets</h3>'
               f'<div class="chips"><span class="c" style="background:var(--dark);color:#fff">{esc(kw)}</span>'
               + "".join(f'<span class="c">{esc(s)}</span>' for s in secs) + '</div>'
               f'<div class="plc">' + "".join(f'<span class="p">{p}</span>' for p in placements) + '</div>'
               f'<p><b>Why it does well for GEO:</b> the first lines answer the question directly (the Quick Answer box AI engines lift), '
               f'it carries FAQPage schema, and the keyword sits in the title, first 100 words, an H2, the meta, and the URL, so both Google and AI answers can place it.</p></div>')
        inner = f'<section class="ph"><div class="wrap"><a href="blog.html" style="font-size:13px;color:var(--faint);text-decoration:none">\u2190 all articles</a></div></section><div class="wrap article-wrap">{art}{chart if False else ""}{geo}</div>'
        (OUT / f"{f.stem}.html").write_text(shell(f"{f.stem}.html", h1[:60], f"<style>{ARTCSS}</style>{inner}"), encoding="utf-8")
        if f.stem in grid_stems:  # only the buyer-weighted display set becomes a grid card
            blang = "DE" if re.search(r'[äöüß]', md) else "EN"
            bcat = categorize({"keyword": kw, "cluster": cluster}, kw)
            cats_present.add(bcat)
            has_cover = (OUT / "img" / "blogcovers" / f"{f.stem}.png").exists()
            if has_cover:
                inner_c = f'<img src="img/blogcovers/{f.stem}.png" loading="lazy" alt="{esc(h1)}">'
            else:  # cover not rendered yet (e.g. fresh gap-fill blog) — text tile so it still shows + clicks
                inner_c = f'<div class="btile"><span class="btcat">{esc(bcat)} · {blang}</span><span class="bth">{esc(h1)}</span></div>'
            cards.append(f'<a class="bcard" data-lang="{blang}" data-cat="{esc(bcat)}" href="{f.stem}.html">{inner_c}</a>')
    grid = (f'<section class="ph"><div class="wrap"><div class="eb">Blog</div><h2>{len(files)} full articles, written and gated</h2>'
            f'<p style="color:var(--mut);font-size:15px;margin:10px 0 0">One English article a day plus three German a week, across six months. Filter by language or category, then click any cover to read the finished, SEO-optimized article.</p></div></section>'
            f'{filter_bar(cats_present)}<div class="wrap"><div class="bgrid">{"".join(cards)}</div></div>')
    (OUT / "blog.html").write_text(shell("blog.html", "Blog", f"<style>{ARTCSS}{FILTCSS}</style>{grid}"), encoding="utf-8")
    return len(files)

LFDIR = Path(r"J:\Claude Code\casewhen-research\content\w-longform-scripts")
LFCSS = ".lfgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}.lfcard{display:block;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 18px 20px;text-decoration:none;color:var(--ink);transition:border-color .15s,transform .15s}.lfcard:hover{border-color:var(--dark);transform:translateY(-2px)}.lfl{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.05em;color:#fff;background:var(--dark);border-radius:6px;padding:2px 8px}.lft{display:block;margin-top:10px;font-weight:650;line-height:1.3;font-size:16px}"
LFEXTRA = [Path(r"J:\Claude Code\casewhen-research\content\w-gapfill-longform")]
def longform_page():
    files = sorted(LFDIR.glob("**/*.md")) if LFDIR.exists() else []
    for d in LFEXTRA:
        if d.exists(): files += sorted(d.glob("**/*.md"))
    cards = []; cats_present = set()
    for f in files:
        md = f.read_text(encoding="utf-8")
        m = re.search(r'^#\s+(.+)$', md, re.M)
        title = (m.group(1).strip() if m else f.stem)
        lang = "DE" if "\\DE\\" in str(f) or "/DE/" in str(f) else "EN"
        lcat = categorize({"keyword": title, "note": f.stem}, title)
        cats_present.add(lcat)
        # lang-prefixed slug so an EN/DE pair sharing a filename gets two distinct pages
        slug = f"script-{lang.lower()}-{f.stem}.html"
        art = md_to_html(md).replace('class="body article annotatable"',
                                     f'class="body article annotatable" data-src="{esc(reposrc(f))}"', 1)
        inner = (f'<section class="ph"><div class="wrap"><a href="youtube.html" style="font-size:13px;color:var(--faint);text-decoration:none">\u2190 all scripts</a></div></section>'
                 f'<div class="wrap article-wrap">{art}</div>')
        (OUT / slug).write_text(shell(slug, title[:60], f"<style>{ARTCSS}</style>{inner}"), encoding="utf-8")
        cards.append(f'<a class="lfcard" data-lang="{lang}" data-cat="{esc(lcat)}" href="{slug}"><span class="lfl">{lang}</span><span class="lft">{esc(title)}</span></a>')
    grid = (f'<section class="ph"><div class="wrap"><div class="eb">YouTube \u00b7 long-form</div>'
            f'<h2>{len(files)} full video scripts, gated</h2>'
            f'<p style="color:var(--mut);font-size:15px;margin:10px 0 0">8 to 15 minute talking-head scripts, Austin in English and Saju in German, buyer-first. '
            f'Click any to read the full script with chapters, beats, b-roll notes and the CTA. Highlight any line to leave a note.</p></div></section>'
            f'{filter_bar(cats_present)}<div class="wrap"><div class="lfgrid">{"".join(cards)}</div></div>')
    (OUT / "youtube.html").write_text(shell("youtube.html", "YouTube", f"<style>{ARTCSS}{LFCSS}{FILTCSS}</style>{grid}"), encoding="utf-8")
    return len(files)

def home(counts=None):
    counts = counts or {}
    cards = ""
    for k, cfg in PLATFORMS.items():
        n = counts.get(k, len(cfg["slots"]))
        cards += (f'<a href="{k}.html"><div class="n">{n}</div>'
                  f'<div class="l">{esc(cfg["title"])}</div><div class="s">{esc(cfg["tag"])}</div></a>')
    if counts.get("youtube"):
        cards += (f'<a href="youtube.html"><div class="n">{counts["youtube"]}</div>'
                  f'<div class="l">Long-form YouTube</div><div class="s">8 to 15 min scripts, EN + DE</div></a>')
    inner = f"""<section class="hero"><div class="wrap">
<div class="eb">CaseWhen · 6-month content plan</div>
<h1>Six months of CaseWhen content.</h1>
<p>Six months of posts for every platform, in English and German, built from the real keyword plan.
Pick a platform below to see the posts: blog articles, LinkedIn posts, short-form video scripts, and
X. Every finished one is written plainly and passes the language and SEO checks before it appears.</p>
<div class="cad">{cards}</div></div></section>"""
    (OUT / "index.html").write_text(shell("index.html", "6-month content plan", inner), encoding="utf-8")

strategy_page()
pricing_page()
seo_page()
funnels_page()
visuals_page()
SOCIALDIR = Path(r"J:\Claude Code\casewhen-research\content\w-batch03-social-v2")
BUYER_LI = Path(r"J:\Claude Code\casewhen-research\content\w-buyer-linkedin")
BUYER_REEL = Path(r"J:\Claude Code\casewhen-research\content\w-buyer-reels")
CADENCE_REEL = Path(r"J:\Claude Code\casewhen-research\content\w-cadence-reels")
CADENCE_X = Path(r"J:\Claude Code\casewhen-research\content\w-cadence-x")
def _load_json(f):
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except Exception:
        return None
def build_social():
    """Show ALL posts per platform, BUYER-FIRST: the buyer-weighted posts fill the
    early slots, the existing practitioner posts follow. Every post carries its own
    lang/who/keyword so the card renders it directly."""
    import collections as _c
    briefs = {}
    bf = Path(__file__).parent / "social-briefs-v2.json"
    if bf.exists():
        for b in json.loads(bf.read_text(encoding="utf-8")):
            briefs[b.get("id")] = b
    _REPOROOT = Path(r"J:\Claude Code\casewhen-research")
    def _relsrc(f):
        try: return str(Path(f).resolve().relative_to(_REPOROOT)).replace("\\", "/")
        except Exception: return ""
    existing = _c.defaultdict(list)
    if SOCIALDIR.exists():
        for f in sorted(SOCIALDIR.glob("*.json")):
            d = _load_json(f)
            if not d: continue
            b = briefs.get(f.stem, {})
            for k in ("keyword", "lang", "who", "cluster"):
                if b.get(k) and not d.get(k): d[k] = b[k]
            d["_src"] = _relsrc(f)
            existing[f.stem.split("-", 1)[0]].append(d)
    def _buyer(dirp, kw_from_note=False):
        out = []
        if dirp.exists():
            for f in sorted(dirp.glob("**/*.json")):
                d = _load_json(f)
                if d: d["_src"] = _relsrc(f)
                if not d: continue
                if not d.get("keyword") and kw_from_note:
                    d["keyword"] = (d.get("note", "").split(",")[-1].strip() or "Buyer post")
                d["buyer"] = True
                out.append(d)
        return out
    _CR = Path(r"J:\Claude Code\casewhen-research\content")
    GAP_LI, GAP_X, GAP_REEL = _CR/"w-gapfill-linkedin", _CR/"w-gapfill-x", _CR/"w-gapfill-reels"
    merged = {
        "linkedin": _buyer(GAP_LI, kw_from_note=True) + _buyer(BUYER_LI, kw_from_note=True) + existing.get("linkedin", []),
        "shortform": _buyer(GAP_REEL) + _buyer(BUYER_REEL) + _buyer(CADENCE_REEL) + existing.get("shortform", []),
        "x": _buyer(GAP_X) + _buyer(CADENCE_X) + existing.get("x", []),
    }
    # DEDUP: never render the same post twice (normalized hook/body), keep first occurrence
    def _sig(p):
        import re as _re
        # key on the opening 50 chars: the doctrine mandates unique openers, so a shared opener == a duplicate
        return _re.sub(r'[^a-z0-9]+', ' ', ((p.get("hook") or p.get("body") or "")).lower()).strip()[:50]
    for plat in merged:
        seen = set(); uniq = []
        for p in merged[plat]:
            s = _sig(p)
            if s and s in seen:
                continue
            seen.add(s); uniq.append(p)
        merged[plat] = uniq
    total = 0
    for plat, posts in merged.items():
        slots = []
        for i, p in enumerate(posts):
            lang = (p.get("lang") or "EN").upper()
            slots.append((lang, i % 30 + 1, {"primary_keyword": p.get("keyword") or ""}))
            COPY[f"{plat}:{i}"] = p
        PLATFORMS[plat]["slots"] = slots
        total += len(posts)
    return total

nsoc = build_social()
print(f"social merged: {nsoc}")
tot = don = 0
for k, cfg in PLATFORMS.items():
    n, d = platform_page(k, cfg); tot += n; don += d
nblogs = blog_articles_and_grid()   # overwrite blog.html with the full-article grid
nlf = longform_page()
home({"blog": nblogs, "linkedin": len(PLATFORMS["linkedin"]["slots"]),
      "shortform": len(PLATFORMS["shortform"]["slots"]), "x": len(PLATFORMS["x"]["slots"]),
      "youtube": nlf})   # real counts, after everything is built
print(f"long-form scripts: {nlf}")
print(f"blog articles assembled: {nblogs}")
print(f"built index + {len(PLATFORMS)} platform pages · {tot} slots scheduled · {don} finished/gated")
for k, cfg in PLATFORMS.items():
    print(f"  {k:10} {len(cfg['slots'])} posts")
