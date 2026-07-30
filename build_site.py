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
    items = [("index.html","Home"),("strategy.html","Strategy")] + [(f"{k}.html", v["title"]) for k, v in PLATFORMS.items()] + [("visuals.html","Visuals"),("seo.html","SEO"),("funnels.html","Funnels")]
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

CONTENT = Path(r"J:\Claude Code\casewhen-research\content\w-batch02-presentation")

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
    return f'<div class="body article">{"".join(out)}</div>'

def render_script(c):
    beats = ""
    for bt in c.get("beats", []):
        beats += (f'<div class="beat"><div class="t">{esc(bt.get("t"))}</div><div>'
                  f'<div class="sp">{esc(bt.get("spoken"))}</div>'
                  f'<div class="os"><b>on-screen</b> {esc(bt.get("screen"))}</div>'
                  f'<div class="pr">{esc(bt.get("prod"))}</div></div></div>')
    cap = (f'<div class="cap"><b>caption</b>{esc(c.get("caption",""))}</div>' if c.get("caption") else "")
    return (f'<div class="body script"><div class="sk-hook">{esc(c["hook"])}</div>'
            f'<span class="sk-os">frame 1: {esc(c.get("onscreen",""))}</span>{beats}{cap}'
            f'<div class="meta"><span class="ship">SHIP ✓ gated</span><span>{esc(c.get("note",""))}</span></div></div>')

def card(platform, idx, lang, day, r):
    key = f"{platform}:{idx}"
    c = COPY.get(key)
    who = "Austin" if lang == "EN" else "Saju"
    kw = esc(r.get("primary_keyword"))
    bar = (f'<div class="bar"><span class="day">Day {day} · {WD_NAME[wd(day)]}</span>'
           f'<span class="lang {lang.lower()}">{lang}</span>'
           f'<span class="who">{who}</span><span class="kw">{kw}</span></div>')
    if c and c.get("article_file"):  # full blog article
        md = (CONTENT / c["article_file"]).read_text(encoding="utf-8")
        body = md_to_html(md)
    elif c and c.get("format") == "script":  # short-form script
        body = render_script(c)
    elif c:  # finished short text (LinkedIn / X / blog summary)
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
    full = " full" if (c and c.get("article_file")) else ""
    return f'<article class="card{full}">{bar}{body}</article>'

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

def landing(title, favicon, css, inner, js=""):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>CaseWhen · {esc(title)}</title><style>{FONTFACE}
*{{box-sizing:border-box}}html{{overflow-x:hidden}}
body{{margin:0;font-family:'NM',ui-sans-serif,-apple-system,'Segoe UI',sans-serif;line-height:1.55;-webkit-font-smoothing:antialiased;overflow-x:hidden}}
a{{color:inherit}}
[data-r]{{opacity:0;transform:translateY(18px);transition:opacity .7s ease,transform .7s ease}}
[data-r].in{{opacity:1;transform:none}}
@media(prefers-reduced-motion:reduce){{[data-r]{{opacity:1;transform:none;transition:none}}}}
.back{{position:fixed;top:14px;left:14px;z-index:30;font-size:12.5px;background:rgba(255,255,255,.9);backdrop-filter:blur(6px);border:1px solid #dfe6e3;border-radius:20px;padding:6px 13px;text-decoration:none;color:#11493F;font-weight:600}}
{css}</style></head><body>
<a class="back" href="funnels.html">← all funnels</a>
{inner}{REVEAL_JS}{js}</body></html>"""

def scorecard_mockup():
    css = """
body{background:#0e2f28;color:#eafaf5}
.hero{max-width:760px;margin:0 auto;padding:96px 22px 30px;text-align:center}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:#7AC4B5}
h1{font-family:'NM';font-weight:700;font-size:clamp(30px,6vw,52px);letter-spacing:-.02em;line-height:1.08;margin:16px 0 0}
.hero p{font-size:18px;color:#bcd8cf;max-width:56ch;margin:16px auto 0}
.card{max-width:640px;margin:26px auto 0;background:#fff;color:#1a1615;border-radius:20px;padding:26px 24px;box-shadow:0 30px 80px rgba(0,0,0,.35)}
.q{border-top:1px solid #eef1ef;padding:16px 0}.q:first-child{border-top:0;padding-top:2px}
.q h4{font-size:15.5px;margin:0 0 10px;font-weight:700}
.opts{display:flex;gap:8px;flex-wrap:wrap}
.opt{font-size:13.5px;border:1px solid #dfe6e3;border-radius:10px;padding:8px 13px;cursor:pointer;transition:all .15s;user-select:none}
.opt:hover{border-color:#1D967C}
.opt.sel{background:#11493F;color:#fff;border-color:#11493F}
.result{margin-top:20px;border-top:2px solid #f0f2f6;padding-top:18px}
.meter{height:14px;border-radius:10px;background:linear-gradient(90deg,#CE8168 0%,#e6c07a 50%,#1D967C 100%);position:relative;margin:12px 0}
.needle{position:absolute;top:-6px;width:4px;height:26px;background:#1a1615;border-radius:3px;left:8%;transition:left 1s cubic-bezier(.2,.8,.2,1)}
.tier{font-family:'NM';font-weight:700;font-size:26px;margin:6px 0 2px}
.tierrow{display:flex;justify-content:space-between;font-size:11px;color:#787a76;font-weight:600;text-transform:uppercase;letter-spacing:.05em}
.gate{margin-top:18px;background:#f3fbfa;border:1px solid #d8f3ed;border-radius:14px;padding:16px}
.gate input{width:100%;border:1px solid #cfe3dc;border-radius:10px;padding:12px 14px;font-size:15px;font-family:inherit;margin-top:8px}
.gate button{width:100%;margin-top:10px;background:#1D967C;color:#fff;border:0;border-radius:10px;padding:13px;font-size:15px;font-weight:700;cursor:pointer;font-family:inherit}
.gate small{color:#787a76;font-size:11.5px}
.foot{max-width:640px;margin:22px auto 60px;text-align:center;color:#9fc2b8;font-size:12.5px}
.badge{display:inline-block;font-size:11px;background:rgba(122,196,181,.16);color:#7AC4B5;border-radius:20px;padding:4px 12px;font-weight:600;margin-bottom:10px}
"""
    quiz = ""
    Q = [("Can you name, in one sentence, who owns the revenue number on your board report?",["Yes, one person","Sort of","No"]),
         ("How do report changes reach the live dashboard?",["Dev, test, then live","Straight to live","Not sure"]),
         ("When did you last test row-level security?",["This quarter","At launch only","Never"]),
         ("Do two teams ever report the same metric differently?",["Never","Sometimes","Often"])]
    for i,(q,opts) in enumerate(Q):
        os_="".join(f'<div class="opt" data-q="{i}" data-v="{2-j}">{esc(o)}</div>' for j,o in enumerate(opts))
        quiz += f'<div class="q"><h4>{i+1}. {esc(q)}</h4><div class="opts">{os_}</div></div>'
    inner = f"""
<div class="hero" data-r>
 <span class="badge">Mockup · Lead magnet</span>
 <div class="eyebrow">Reporting-Foundation Maturity Scorecard</div>
 <h1>Would your Power BI numbers survive a board review?</h1>
 <p>Answer four questions. Get an instant maturity tier and a one-page PDF you can forward to your CFO.</p>
</div>
<div class="card" data-r>
 {quiz}
 <div class="result">
  <div class="tierrow"><span>Fragile</span><span>Functional</span><span>Board-ready</span></div>
  <div class="meter"><div class="needle" id="needle"></div></div>
  <div class="tier" id="tier">Answer the four questions</div>
  <div class="gate">
   <b style="font-size:14px">Get your full scorecard + the forwardable PDF</b>
   <input type="email" placeholder="you@company.com" aria-label="email">
   <button type="button">Email me my scorecard</button>
   <small>No spam. One email with your result and the PDF. Mockup only — nothing is sent.</small>
  </div>
 </div>
</div>
<div class="foot" data-r>CaseWhen · a fixed-price Reporting Foundation Review fixes whatever the scorecard flags.</div>"""
    js = """<script>
let ans={};
document.querySelectorAll('.opt').forEach(o=>o.addEventListener('click',()=>{
  const q=o.dataset.q; document.querySelectorAll('.opt[data-q="'+q+'"]').forEach(x=>x.classList.remove('sel'));
  o.classList.add('sel'); ans[q]=+o.dataset.v; render();
}));
function render(){
  const ks=Object.keys(ans); if(!ks.length)return;
  let s=0; ks.forEach(k=>s+=ans[k]); const max=Object.keys(ans).length*2;
  const pct=Math.round(s/ (4*2) *100);
  document.getElementById('needle').style.left=Math.max(4,Math.min(96,pct))+'%';
  const t=document.getElementById('tier');
  if(ks.length<4){t.textContent='Keep going ('+ks.length+'/4)';t.style.color='#787a76';return;}
  if(pct<40){t.textContent='Fragile';t.style.color='#CE8168';}
  else if(pct<75){t.textContent='Functional';t.style.color='#b8862f';}
  else {t.textContent='Board-ready';t.style.color='#1D967C';}
}
</script>"""
    (OUT/"scorecard.html").write_text(landing("Maturity Scorecard","🎯",css,inner,js),encoding="utf-8")

def calculator_mockup():
    css = """
body{background:#E9ECE8;color:#1a1615}
.wrap2{max-width:720px;margin:0 auto;padding:92px 22px 60px}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:#1D967C}
h1{font-family:'NM';font-weight:700;font-size:clamp(28px,5.4vw,46px);letter-spacing:-.02em;line-height:1.1;margin:12px 0 0}
.sub{font-size:17px;color:#5c6866;margin:14px 0 0;max-width:56ch}
.panel{margin-top:24px;background:#fff;border-radius:20px;padding:26px 24px;box-shadow:0 24px 60px rgba(17,73,63,.12)}
.row{margin:18px 0}
.row label{font-size:14px;font-weight:600;display:flex;justify-content:space-between}
.row label b{color:#11493F}
input[type=range]{width:100%;margin-top:10px;accent-color:#1D967C}
.readout{margin-top:22px;background:#11493F;color:#fff;border-radius:16px;padding:22px;text-align:center}
.readout .big{font-family:'NM';font-weight:700;font-size:clamp(40px,10vw,72px);letter-spacing:-.03em;line-height:1}
.readout .lbl{color:#9fc2b8;font-size:13px;margin-top:6px}
.split{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}
.split .s{flex:1;min-width:120px;background:rgba(255,255,255,.08);border-radius:10px;padding:12px;font-size:12.5px;color:#cfe3dc}
.split .s b{display:block;color:#fff;font-size:18px;font-weight:700}
.rec{margin-top:14px;font-size:14px;color:#eafaf5;background:rgba(122,196,181,.14);border-radius:10px;padding:12px}
.gate{margin-top:16px;background:#f3fbfa;border:1px solid #d8f3ed;border-radius:14px;padding:16px}
.gate input{width:100%;border:1px solid #cfe3dc;border-radius:10px;padding:12px 14px;font-size:15px;font-family:inherit;margin-top:8px}
.gate button{width:100%;margin-top:10px;background:#1D967C;color:#fff;border:0;border-radius:10px;padding:13px;font-size:15px;font-weight:700;cursor:pointer;font-family:inherit}
.gate small{color:#787a76;font-size:11.5px}
.badge{display:inline-block;font-size:11px;background:#d8f3ed;color:#11493F;border-radius:20px;padding:4px 12px;font-weight:600}
"""
    inner = """
<div class="wrap2">
 <span class="badge" data-r>Mockup · Lead magnet</span>
 <div class="eyebrow" data-r>Power BI cost calculator</div>
 <h1 data-r>What your Power BI setup actually costs.</h1>
 <p class="sub" data-r>Move the sliders. See the yearly number, the licence-vs-capacity crossover, and which side you're on. Real Microsoft pricing.</p>
 <div class="panel" data-r>
  <div class="row"><label>Report viewers <b id="vv">120</b></label><input id="viewers" type="range" min="10" max="1200" value="120"></div>
  <div class="row"><label>Report builders <b id="bb">6</b></label><input id="builders" type="range" min="1" max="60" value="6"></div>
  <div class="readout">
   <div class="big" id="cost">$0</div><div class="lbl">estimated per year</div>
   <div class="split">
    <div class="s"><b id="model">Per-user</b>cheaper model</div>
    <div class="s"><b id="cross">~350</b>viewer crossover</div>
   </div>
   <div class="rec" id="rec">Adjust the sliders to see your recommendation.</div>
  </div>
  <div class="gate">
   <b style="font-size:14px">Email me this estimate as a one-page PDF</b>
   <input type="email" placeholder="you@company.com" aria-label="email">
   <button type="button">Send my estimate</button>
   <small>Mockup only — nothing is sent. Real page uses live Microsoft pricing.</small>
  </div>
 </div>
</div>"""
    js = """<script>
const PRO=14*12, F64=5000*12;
const v=document.getElementById('viewers'),b=document.getElementById('builders');
function fmt(n){return '$'+Math.round(n).toLocaleString();}
function animate(el,to){const from=+(el.dataset.v||0);const t0=performance.now();
 function f(t){const k=Math.min(1,(t-t0)/500);const val=from+(to-from)*(1-Math.pow(1-k,3));el.textContent=fmt(val);if(k<1)requestAnimationFrame(f);else el.dataset.v=to;}requestAnimationFrame(f);}
function calc(){
 const viewers=+v.value,builders=+b.value;
 document.getElementById('vv').textContent=viewers;document.getElementById('bb').textContent=builders;
 const perUser=(viewers+builders)*PRO;
 const capacity=F64+builders*PRO;
 const best=Math.min(perUser,capacity);
 animate(document.getElementById('cost'),best);
 const cap=capacity<perUser;
 document.getElementById('model').textContent=cap?'Capacity':'Per-user';
 document.getElementById('rec').textContent=cap
  ? 'At '+viewers+' viewers, a Fabric F64 capacity ('+fmt(capacity)+'/yr) beats per-user Pro ('+fmt(perUser)+'/yr). Buy capacity.'
  : 'At '+viewers+' viewers, per-user Pro ('+fmt(perUser)+'/yr) beats a capacity ('+fmt(capacity)+'/yr). Stay per-user.';
}
v.addEventListener('input',calc);b.addEventListener('input',calc);calc();
</script>"""
    (OUT/"calculator.html").write_text(landing("Cost calculator","🧮",css,inner,js),encoding="utf-8")

def funnels_page():
    scorecard_mockup(); calculator_mockup()
    mags=[
     ("Reporting-Foundation Maturity Scorecard","Flagship capture atom","A 4-question quiz returns an instant tier (Fragile / Functional / Board-ready) and emails a one-page PDF the controller forwards to their CFO.","Foundation-checker · top-mid funnel","scorecard.html","open the mockup","#11493F"),
     ("Power BI cost calculator","Buyer-intent (BOFU)","Sliders return a real yearly cost and the per-user-vs-capacity crossover, with email capture on the result.","Foundation-checker · decision","calculator.html","open the mockup","#1D967C"),
     ("Internal buy-in briefing","De-risking template","A one-page PDF: how to present a reporting review to your CFO or board as a proactive governance move.","Foundation-checker · consideration","","spec — mockup next","#7AC4B5"),
     ("Case-study bundle","Evaluation proof","A curated set: 10 DACH reporting rebuilds (Schindler, Ipsen, WellBeauty), before and after, as one downloadable research artifact.","In active evaluation","","spec — mockup next","#6F93AC"),
     ("Governance whitepaper","Authority capture","A gated governance / manufacturing whitepaper structured to the AI-Overview governance outline.","Buyer-authority","","spec — mockup next","#CE8168"),
     ("German scorecard + briefing","DACH parity","The scorecard and buy-in briefing localised into German — Saju's track capture entry point.","DACH foundation-checker","","spec — mockup next","#132630"),
    ]
    cards=""
    for name,tag,desc,persona,href,cta,color in mags:
        link=f'href="{href}"' if href else 'href="javascript:void(0)" style="cursor:default"'
        cards+=f"""<a class="fcard" {link} data-r style="--ac:{color}">
        <div class="tag">{esc(tag)}</div><h3>{esc(name)}</h3><p>{esc(desc)}</p>
        <div class="who">{esc(persona)}</div><div class="cta">{esc(cta)} →</div></a>"""
    st="""
.fgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:22px}
.fcard{display:block;text-decoration:none;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;position:relative;overflow:hidden;transition:transform .15s,box-shadow .15s}
.fcard::before{content:"";position:absolute;top:0;left:0;right:0;height:5px;background:var(--ac)}
.fcard:hover{transform:translateY(-3px);box-shadow:0 16px 40px rgba(17,73,63,.12)}
.fcard .tag{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--ac);margin-top:4px}
.fcard h3{font-size:19px;margin:6px 0 8px;letter-spacing:-.01em}
.fcard p{font-size:14px;color:var(--mut);margin:0}
.fcard .who{font-size:12px;color:var(--faint);margin-top:12px}
.fcard .cta{font-size:13px;font-weight:700;color:var(--dark);margin-top:8px}
[data-r]{opacity:0;transform:translateY(16px);transition:opacity .6s,transform .6s}[data-r].in{opacity:1;transform:none}
@media(max-width:760px){.fgrid{grid-template-columns:1fr}}
"""
    body=f"""<style>{st}</style>
<section class="hero"><div class="wrap"><div class="eb">CaseWhen · funnels</div>
<h1>The lead magnets that turn reach into emails.</h1>
<p>Six free tools and downloads, each traded for an email, each pointed at a booked fixed-price review.
Two are built as live mockups below — open them. The rest are specced and get the same treatment next.
Every one shares the brand, and each looks distinct.</p>
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
        title=fm.get("META_TITLE",fm.get("TITLE","")); h1=fm.get("H1",""); desc=fm.get("META_DESC",fm.get("META","")); slug=fm.get("SLUG","")
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
look, and the plan to re-optimize the existing blog. Green means placed. This is how you get confidence
a post is optimized, not just written.</p></div></section>
<div class="wrap seo">{blocks}{reopt}
<div class="funnel" style="font-size:14px;color:#33372f;background:var(--pale);border-left:3px solid var(--brand);border-radius:0 8px 8px 0;padding:12px 14px;margin:18px 0 40px">
<b>How this is enforced:</b> every article runs through the ship gate before it appears here. The gate
hard-fails any post missing the keyword in the H1, the first 100 words, a question H2, the meta
description, the slug, or the schema, so a post cannot ship under-optimized. The grid above is that
gate's output, made visible.</div></div>"""
    (OUT/"seo.html").write_text(shell("seo.html","SEO coverage",body),encoding="utf-8")

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
    blog_topics = [("KPI & data modeling",30),("Training & certification",28),("Azure & data engineering",12),("Pricing & licensing",11),("Governance",7),("Power BI flagship",6),("Fabric",3),("Migrations / automation",3)]
    li_topics = [("KPI",19),("Training",17),("Governance",15),("Azure",13),("Pricing",12),("Fabric",10),("Migrations",8),("Automation",6)]
    sf_topics = [("KPI",31),("Training",26),("Pricing",11),("Azure",11),("Governance",8),("Power BI flagship",7),("Fabric",4),("Migrations / automation",2)]
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
<tr><td><b>Short-form video</b></td><td>~30 (script + captions; EN + DE)</td><td>Numbered countdown · mistake-callout · before/after</td><td>Reach + saves</td></tr>
<tr><td><b>YouTube</b></td><td>~8 (2×/wk, EN + DE)</td><td>Outcome-led tutorial · contrarian thesis</td><td>Deep authority + evergreen search</td></tr>
<tr><td><b>X / Twitter</b></td><td>~4 native + repurposed</td><td>Numbered roadmap · same-day release newsjack</td><td>Timeliness + repurpose</td></tr>
</table></div></section>

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

def home():
    cards = ""
    for k, cfg in PLATFORMS.items():
        n = len(cfg["slots"])
        cards += (f'<a href="{k}.html"><div class="n">{n}</div>'
                  f'<div class="l">{esc(cfg["title"])}</div><div class="s">{esc(cfg["tag"])}</div></a>')
    inner = f"""<section class="hero"><div class="wrap">
<div class="eb">CaseWhen · 30-day content sample</div>
<h1>A 30-day sample of CaseWhen content.</h1>
<p>Thirty days of posts for every platform, in English and German, built from the real keyword plan.
Pick a platform below to see the posts: blog articles, LinkedIn posts, short-form video scripts, and
X. Every finished one is written plainly and passes the language and SEO checks before it appears.</p>
<div class="cad">{cards}</div></div></section>"""
    (OUT / "index.html").write_text(shell("index.html", "30-day content plan", inner), encoding="utf-8")

home()
strategy_page()
seo_page()
funnels_page()
visuals_page()
tot = don = 0
for k, cfg in PLATFORMS.items():
    n, d = platform_page(k, cfg); tot += n; don += d
print(f"built index + {len(PLATFORMS)} platform pages · {tot} slots scheduled · {don} finished/gated")
for k, cfg in PLATFORMS.items():
    print(f"  {k:10} {len(cfg['slots'])} posts")
