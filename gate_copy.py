#!/usr/bin/env python3
"""Gate every finished post in copy-store.json before it is allowed to show as done.
Runs the same rules as ship_check: both language scanners, em dashes, specificity
(concrete anchor in the hook), external-facing (no internal SEO/pitch data), and the
per-platform hook/close format. Prints PASS/FAIL per entry with evidence. Exit 1 if any fail."""
import json, sys, subprocess, tempfile, os, re, importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = Path(os.path.expanduser(r"~/.claude/skills/casewhen-content/scripts"))
spec = importlib.util.spec_from_file_location("sc", SKILL / "ship_check.py")
sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)

store = json.loads((HERE / "copy-store.json").read_text(encoding="utf-8"))
env = dict(os.environ, PYTHONIOENCODING="utf-8")

# pull each slot's scheduled keyword so we can verify SEO exact-match in the copy
import build_site as B
KW = {}
for pk, cfg in B.PLATFORMS.items():
    for idx, (lang, day, r) in enumerate(sorted(cfg["slots"], key=lambda s: (s[1], s[0]))):
        KW[f"{pk}:{idx}"] = (r.get("primary_keyword") or "").strip().lower()

def ngrams(text, n=5):
    w = re.findall(r"[a-z0-9']+", (text or "").lower())
    return {" ".join(w[i:i+n]) for i in range(len(w) - n + 1)}

def scan(text, script, drleaf):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("HOOK: %s\nBODY: %s\n" % ("", text)); p = f.name
    try:
        ok, ev = sc.run_scanner(script, p, drleaf=drleaf)
    finally:
        os.unlink(p)
    return ok, ev

fails = 0
for key, c in store.items():
    platform = key.split(":")[0]
    text = " ".join(x for x in (c.get("hook"), c.get("body"), c.get("close")) if x)
    problems = []
    # em dash
    if "—" in text or " - " in text and "—" in text: problems.append("em dash")
    if "—" in text: problems.append("em dash")
    # specificity on hook
    hard, soft = sc.specificity_issues(c.get("hook", ""))
    if hard: problems.append(f"vague hook: {hard}")
    # external-facing
    meta = sc.internal_meta_hits(text)
    if meta: problems.append(f"internal data: {meta}")
    # language scanners
    okm, evm = scan(text, sc.MY_GATE, False)
    if okm is False: problems.append(f"check_banned: {evm}")
    okd, evd = scan(text, sc.DRLEAF, True)
    if okd is False: problems.append(f"dr-leaf: {evd}")
    # slogan + full-sentence hook (social)
    slog = sc.slogan_issue(c.get("hook", ""))
    if slog: problems.append(slog)
    if platform in ("linkedin", "x", "shortform"):
        frag = sc.fragment_issue(c.get("hook", ""))
        if frag: problems.append(frag)
    # per-platform format
    if platform == "linkedin":
        if len(c.get("hook", "")) > 140: problems.append(f"hook {len(c['hook'])}c > 140")
        if not c.get("close", "").rstrip().endswith("?"): problems.append("close not a question")
    # SEO exact-match keyword placement (top-notch, 'exactly how it is typed')
    kw = KW.get(key, "")
    if kw:
        hooklow = (c.get("hook", "") or "").lower()
        alllow = text.lower()
        if platform == "blog":
            if kw not in hooklow: problems.append(f"SEO: keyword '{kw}' not in H1/hook")
            if kw not in alllow[:320]: problems.append(f"SEO: keyword '{kw}' not in first ~100 words")
        elif platform == "shortform":
            if kw not in alllow: problems.append(f"SEO: keyword '{kw}' not in script/caption")
            if "caption" not in alllow: problems.append("shortform missing a caption line")
        else:  # linkedin / x — every keyword word should anchor the post (not necessarily adjacent)
            toks = [t for t in re.findall(r"[a-z0-9]+", kw) if len(t) > 2]
            missing = [t for t in toks if t not in alllow]
            if missing: problems.append(f"keyword words missing: {missing}")
    mark = "PASS" if not problems else "FAIL"
    if problems: fails += 1
    print(f"[{mark}] {key:14} {'; '.join(problems) if problems else 'clean · specific · external · SEO placed · in format'}")

# cross-post recycling: the same message reused across formats/platforms
print("\n-- cross-post duplication (same post reused across formats) --")
keys = list(store.keys())
dups = 0
grams = {k: ngrams((store[k].get("hook","")+" "+store[k].get("body","")), 5) for k in keys}
for a in range(len(keys)):
    for b in range(a+1, len(keys)):
        ka, kb = keys[a], keys[b]
        if not grams[ka] or not grams[kb]: continue
        shared = grams[ka] & grams[kb]
        overlap = len(shared) / min(len(grams[ka]), len(grams[kb]))
        if overlap >= 0.30:
            dups += 1
            print(f"[DUP]  {ka} ~ {kb}  ({int(overlap*100)}% shared) e.g. \"{list(shared)[0]}\"")
if not dups: print("none — every post is a distinct message")
fails += dups

print(f"\n{len([k for k in store])-0} posts checked · {fails} problems (per-post + duplication)")
sys.exit(1 if fails else 0)
