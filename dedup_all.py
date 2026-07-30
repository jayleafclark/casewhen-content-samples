#!/usr/bin/env python3
"""Site-wide zero-repeat check. Compares EVERY finished item against every other —
posts (copy-store), carousel slides + quote cards (decks.json) — and flags any two
that share too much phrasing. A quote may not echo a carousel; a post may not echo
another post. Exit 1 if any repeat is found."""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent

def grams(text, n=5):
    w = re.findall(r"[a-z0-9']+", (text or "").lower())
    return {" ".join(w[i:i+n]) for i in range(len(w) - n + 1)}

items = {}  # id -> text

# posts
cs = json.loads((HERE / "copy-store.json").read_text(encoding="utf-8"))
for k, c in cs.items():
    if c.get("format") == "script":
        t = c.get("hook","") + " " + " ".join(b.get("spoken","") for b in c.get("beats", [])) + " " + c.get("caption","")
    else:
        t = " ".join(str(c.get(x,"")) for x in ("hook","body","close"))
    items[f"post:{k}"] = t

# carousels + quotes
dk = json.loads((HERE / "decks.json").read_text(encoding="utf-8"))
for name, deck in dk.items():
    if name == "quotes":
        for q in deck: items[f"quote:{q['slug']}"] = q["quote"]
        continue
    for i, s in enumerate(deck["slides"], 1):
        items[f"deck:{name}-{i}"] = " ".join(str(s.get(x,"")) for x in ("headline","promise","subtext","leftbody","rightbody","cta","link"))

ids = list(items)
G = {i: grams(items[i]) for i in ids}
reps = 0
for a in range(len(ids)):
    for b in range(a+1, len(ids)):
        ia, ib = ids[a], ids[b]
        if not G[ia] or not G[ib]: continue
        ov = len(G[ia] & G[ib]) / min(len(G[ia]), len(G[ib]))
        # ignore slides within the SAME deck (a deck is one coherent piece)
        same_deck = ia.startswith("deck:") and ib.startswith("deck:") and ia.split(":")[1].rsplit("-",1)[0] == ib.split(":")[1].rsplit("-",1)[0]
        if ov >= 0.25 and not same_deck:
            reps += 1
            print(f"[REPEAT] {ia}  ~  {ib}  ({int(ov*100)}% shared)  e.g. \"{sorted(G[ia] & G[ib])[0]}\"")
print(f"\n{len(ids)} items checked · {reps} repeats" + ("" if reps else " — zero repeats across posts, carousels, and quotes"))
sys.exit(1 if reps else 0)
