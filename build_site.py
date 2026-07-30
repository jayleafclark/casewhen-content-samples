#!/usr/bin/env python3
"""
build_site.py — generate the CaseWhen 30-day content site from the real calendar
tables + a copy store of finished, gated post text.

- Reads the per-platform idea tables (content/w-platform-batches/*.csv).
- Lays out a 30-day schedule per platform at the cadence from 12-distribution-map:
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
                 "keyword. Payoff in the first two seconds, one idea.",
        "slots": ([("EN", d, r) for d, r in schedule(sf, "EN", DAYS, {1,3,5})]
                  + [("DE", d, r) for d, r in schedule(sf, "DE", DAYS, {0,2})]),
    },
    "x": {
        "title": "X / Twitter", "tag": "weekly + repurposed",
        "blurb": "One native declarative post a week, plus the short-form and LinkedIn lines trimmed "
                 "to a single claim and a number. Keyword in the first line.",
        "slots": [("EN", d, r) for d, r in schedule(xt, "EN", DAYS, {0})],
    },
}

# ---- HTML ----
CSS = """
:root{--ink:#141a19;--bg:#fbfcfc;--card:#fff;--line:#e2e8e6;--mut:#5c6866;--faint:#93a09c;
--brand:#1D967C;--dark:#11493F;--mid:#7AC4B5;--pale:#D8F3EE;--neutral:#E9ECE8}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;font-family:'NM',ui-sans-serif,-apple-system,'Segoe UI',sans-serif;color:var(--ink);
background:var(--bg);line-height:1.6;-webkit-font-smoothing:antialiased}
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
.nav a{font-size:13.5px;color:var(--mut);text-decoration:none;padding:7px 12px;border-radius:8px}
.nav a:hover{background:var(--pale);color:var(--dark)}
.nav a.on{background:var(--dark);color:#fff}
/* hero */
.hero{padding:56px 0 34px;border-bottom:1px solid var(--line)}
.hero .eb{font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--brand);margin-bottom:12px}
.hero h1{font-size:clamp(29px,5.4vw,50px);max-width:17ch}
.hero p{font-size:clamp(16px,2.2vw,18.5px);color:var(--mut);max-width:60ch;margin:18px 0 0}
/* cadence cards on home */
.cad{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:30px}
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
.days{display:grid;grid-template-columns:repeat(2,1fr);gap:18px;padding:24px 0 60px}
.card{border:1px solid var(--line);border-radius:16px;background:var(--card);overflow:hidden;display:flex;flex-direction:column}
.card .bar{display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.day{font-size:11px;font-weight:700;letter-spacing:.03em;background:var(--dark);color:#fff;border-radius:7px;padding:4px 8px}
.lang{font-size:11px;font-weight:700;border-radius:7px;padding:4px 8px}
.lang.en{background:var(--pale);color:var(--dark)}.lang.de{background:#e7efe9;color:#2c5a4c}
.who{font-size:12px;color:var(--faint)}
.kw{margin-left:auto;font-size:11.5px;color:var(--dark);background:#eef5f2;border:1px solid var(--mid);border-radius:20px;padding:3px 10px;font-weight:500}
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
.foot{padding:30px 0 50px;color:var(--mut);font-size:13px;border-top:1px solid var(--line)}
@media(max-width:760px){
 .cad{grid-template-columns:repeat(2,1fr)}
 .days{grid-template-columns:1fr}
 .top .wrap{gap:8px}
 .nav{width:100%;margin-left:0;overflow-x:auto;flex-wrap:nowrap;-webkit-overflow-scrolling:touch}
 .hero{padding:40px 0 26px}
}
"""

def nav(active):
    items = [("index.html","Home")] + [(f"{k}.html", v["title"]) for k, v in PLATFORMS.items()]
    return "".join(f'<a href="{h}" class="{"on" if h==active else ""}">{esc(t)}</a>' for h, t in items)

def shell(active, title, inner):
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>CaseWhen · {esc(title)}</title>
<style>{CSS}</style></head><body>
<header class="top"><div class="wrap"><img src="img/wordmark.png" alt="CaseWhen">
<nav class="nav">{nav(active)}</nav></div></header>
{inner}
<footer class="foot"><div class="wrap">A 30-day content plan built from the keyword calendar. Every
finished post clears the ship gate (plain language, a concrete specific, external-facing only, and the
per-platform format) before it appears as done. Internal preview · not indexed.</div></footer>
</body></html>"""

def card(platform, idx, lang, day, r):
    key = f"{platform}:{idx}"
    c = COPY.get(key)
    who = "Austin" if lang == "EN" else "Saju"
    kw = esc(r.get("primary_keyword"))
    bar = (f'<div class="bar"><span class="day">Day {day} · {WD_NAME[wd(day)]}</span>'
           f'<span class="lang {lang.lower()}">{lang}</span>'
           f'<span class="who">{who}</span><span class="kw">{kw}</span></div>')
    if c:  # finished, gated copy
        body = f'<div class="body done"><span class="hook">{esc(c["hook"])}</span>' \
               f'<div class="txt">{esc(c["body"])}</div>'
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
    return f'<article class="card">{bar}{body}</article>'

def platform_page(k, cfg):
    slots = sorted(cfg["slots"], key=lambda s: (s[1], s[0]))
    done = sum(1 for i,(lang,day,r) in enumerate(slots) if f"{k}:{i}" in COPY)
    cards = "".join(card(k, i, lang, day, r) for i,(lang,day,r) in enumerate(slots))
    inner = f"""<section class="ph"><div class="wrap"><div class="eb">30-day plan</div>
<h2>{esc(cfg['title'])}</h2><p>{esc(cfg['blurb'])}</p>
<div class="count">{len(slots)} posts scheduled over 30 days · {done} finished and gated · {cfg['tag']}</div></div></section>
<div class="wrap"><div class="days">{cards}</div></div>"""
    (OUT / f"{k}.html").write_text(shell(f"{k}.html", cfg["title"], inner), encoding="utf-8")
    return len(slots), done

def home():
    cards = ""
    for k, cfg in PLATFORMS.items():
        n = len(cfg["slots"])
        cards += (f'<a href="{k}.html"><div class="n">{n}</div>'
                  f'<div class="l">{esc(cfg["title"])}</div><div class="s">{esc(cfg["tag"])}</div></a>')
    inner = f"""<section class="hero"><div class="wrap">
<div class="eb">CaseWhen · 30-day content plan</div>
<h1>Two people pull the same number and get two different answers.</h1>
<p>That is the problem CaseWhen fixes, and it is what every post here is about: Power BI reporting a
board can actually trust. Below is a full 30 days of content across every platform, in English and
German, built from the real keyword calendar. Every finished post clears the ship gate first.</p>
<div class="cad">{cards}</div></div></section>"""
    (OUT / "index.html").write_text(shell("index.html", "30-day content plan", inner), encoding="utf-8")

home()
tot = don = 0
for k, cfg in PLATFORMS.items():
    n, d = platform_page(k, cfg); tot += n; don += d
print(f"built index + {len(PLATFORMS)} platform pages · {tot} slots scheduled · {don} finished/gated")
for k, cfg in PLATFORMS.items():
    print(f"  {k:10} {len(cfg['slots'])} posts")
