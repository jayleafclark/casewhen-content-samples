#!/usr/bin/env python3
"""Gate every finished post in copy-store.json before it is allowed to show as done.
Runs the same rules as ship_check: both language scanners, em dashes, specificity
(concrete anchor in the hook), external-facing (no internal SEO/pitch data), and the
per-platform hook/close format. Prints PASS/FAIL per entry with evidence. Exit 1 if any fail."""
import json, sys, subprocess, tempfile, os, importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = Path(os.path.expanduser(r"~/.claude/skills/casewhen-content/scripts"))
spec = importlib.util.spec_from_file_location("sc", SKILL / "ship_check.py")
sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)

store = json.loads((HERE / "copy-store.json").read_text(encoding="utf-8"))
env = dict(os.environ, PYTHONIOENCODING="utf-8")

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
    # per-platform format
    if platform == "linkedin":
        if len(c.get("hook", "")) > 140: problems.append(f"hook {len(c['hook'])}c > 140")
        if not c.get("close", "").rstrip().endswith("?"): problems.append("close not a question")
    mark = "PASS" if not problems else "FAIL"
    if problems: fails += 1
    print(f"[{mark}] {key:14} {'; '.join(problems) if problems else 'clean · specific · external · in format'}")

print(f"\n{len(store)-fails}/{len(store)} finished posts SHIP · {fails} HOLD")
sys.exit(1 if fails else 0)
