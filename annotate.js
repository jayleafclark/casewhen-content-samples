/* CaseWhen preview review layer.
   Highlight any section of a blog / script / LinkedIn / X post (EN or DE), attach a note,
   and get a surgical AI edit back that you can accept inline. The AI runs through a
   CaseWhen-hosted proxy (the key lives server-side); reviewers never enter a key. Notes
   anywhere except directly to the model provider you choose. */
(function () {
  "use strict";
  var LS = window.localStorage;
  var PATH = location.pathname.replace(/[^a-z0-9]/gi, "_");
  var NOTES_KEY = "cw_notes_" + PATH;
  var CFG_KEY = "cw_cfg";
  var uid = function () { return "a" + Math.random().toString(36).slice(2, 9); };

  function cfg() { try { return JSON.parse(LS.getItem(CFG_KEY)) || {}; } catch (e) { return {}; } }
  function setCfg(c) { LS.setItem(CFG_KEY, JSON.stringify(c)); }
  function notes() { try { return JSON.parse(LS.getItem(NOTES_KEY)) || []; } catch (e) { return []; } }
  function saveNotes(n) { LS.setItem(NOTES_KEY, JSON.stringify(n)); }
  function esc(s) { return (s || "").replace(/[&<>"]/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]; }); }

  var containers = [];
  function collectContainers() {
    containers = Array.prototype.slice.call(document.querySelectorAll(".annotatable"));
    containers.forEach(function (c, i) { c.setAttribute("data-cwid", i); });
  }

  // ---- highlight wrapping ----
  function wrapSelection(note) {
    var sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) return null;
    var range = sel.getRangeAt(0);
    var host = range.commonAncestorContainer;
    var el = host.nodeType === 1 ? host : host.parentNode;
    var container = el.closest ? el.closest(".annotatable") : null;
    if (!container) return null;
    var quote = sel.toString().trim();
    if (quote.length < 2) return null;
    var mark = document.createElement("mark");
    mark.className = "cw-anno";
    mark.setAttribute("data-aid", note.aid);
    try { range.surroundContents(mark); }
    catch (e) { // selection spans element boundaries: fall back to extract+insert
      var frag = range.extractContents(); mark.appendChild(frag); range.insertNode(mark);
    }
    sel.removeAllRanges();
    note.cwid = container.getAttribute("data-cwid");
    note.src = container.getAttribute("data-src") || "";
    note.quote = quote;
    return note;
  }

  // best-effort re-highlight saved notes on load (match quote text inside its container)
  function rehighlight() {
    notes().forEach(function (n) {
      if (n.status === "deleted") return;
      var c = document.querySelector('.annotatable[data-cwid="' + n.cwid + '"]');
      if (!c || c.querySelector('mark[data-aid="' + n.aid + '"]')) return;
      var walker = document.createTreeWalker(c, NodeFilter.SHOW_TEXT, null);
      var node;
      while ((node = walker.nextNode())) {
        var idx = node.nodeValue.indexOf(n.quote);
        if (idx >= 0) {
          var r = document.createRange();
          r.setStart(node, idx); r.setEnd(node, idx + n.quote.length);
          var mark = document.createElement("mark");
          mark.className = "cw-anno" + (n.status === "resolved" ? " done" : "");
          mark.setAttribute("data-aid", n.aid);
          try { r.surroundContents(mark); } catch (e) {}
          break;
        }
      }
    });
  }

  // ---- floating add-note popover on selection ----
  var pop;
  function ensurePop() {
    if (pop) return pop;
    pop = document.createElement("div");
    pop.className = "cw-pop"; pop.style.display = "none";
    pop.innerHTML = '<button class="cw-pop-btn">+ Add note</button>';
    document.body.appendChild(pop);
    pop.querySelector(".cw-pop-btn").addEventListener("mousedown", function (e) {
      e.preventDefault();
      var q = window.getSelection().toString().trim();
      if (!q) return;
      openNoteEditor(q);
    });
    return pop;
  }
  function onSelect() {
    var sel = window.getSelection();
    var q = sel ? sel.toString().trim() : "";
    var anchor = sel && sel.anchorNode ? (sel.anchorNode.nodeType === 1 ? sel.anchorNode : sel.anchorNode.parentNode) : null;
    if (!q || q.length < 2 || !anchor || !anchor.closest || !anchor.closest(".annotatable")) {
      if (pop) pop.style.display = "none"; return;
    }
    var rect = sel.getRangeAt(0).getBoundingClientRect();
    ensurePop();
    pop.style.display = "block";
    pop.style.top = (window.scrollY + rect.top - 42) + "px";
    pop.style.left = (window.scrollX + rect.left) + "px";
  }

  // ---- note editor (small inline prompt) ----
  function openNoteEditor(quote) {
    var n = { aid: uid(), quote: quote, note: "", status: "open", revision: "" };
    wrapSelection(n);
    if (pop) pop.style.display = "none";
    openPanel();
    var arr = notes(); arr.push(n); saveNotes(arr);
    renderPanel();
    var ta = document.querySelector('.cw-note[data-aid="' + n.aid + '"] textarea');
    if (ta) { ta.focus(); }
  }

  // whole-item note for image cards (carousels, quote cards): no text to highlight, so the note
  // is tied to the whole deck via its data-src, and the repo AI editor actions it on the source JSON.
  function openDeckNote(card) {
    if (!card) return;
    var n = { aid: uid(), quote: card.getAttribute("data-note-label") || "(whole item)", note: "",
              status: "open", revision: "", src: card.getAttribute("data-src") || "",
              cwid: card.getAttribute("data-cwid") || "", deck: true };
    openPanel();
    var arr = notes(); arr.push(n); saveNotes(arr);
    renderPanel();
    var ta = document.querySelector('.cw-note[data-aid="' + n.aid + '"] textarea');
    if (ta) ta.focus();
  }

  // ---- Austin / Saju approval checkmarks (per piece, keyed by its source file) ----
  function apKey(src) { return "cw_approve_" + src; }
  function getAp(src) { try { return JSON.parse(LS.getItem(apKey(src))) || {}; } catch (e) { return {}; } }
  function setAp(src, who, val) { var a = getAp(src); a[who] = val; a.t = Date.now(); LS.setItem(apKey(src), JSON.stringify(a)); }
  function apBtn(who, on) { return '<button class="cw-ap' + (on ? " on" : "") + '" data-who="' + who + '" type="button">' + (on ? "✓ " : "") + (who === "austin" ? "Austin" : "Saju") + " check</button>"; }
  function injectApprovals() {
    document.querySelectorAll(".annotatable[data-src]").forEach(function (el) {
      var src = el.getAttribute("data-src");
      if (!src || el.querySelector(".cw-approve")) return;
      var a = getAp(src);
      var bar = document.createElement("div");
      bar.className = "cw-approve";
      bar.innerHTML = '<span class="cw-aplab">Aligned and ready to film?</span>' + apBtn("austin", a.austin) + apBtn("saju", a.saju);
      bar.querySelectorAll(".cw-ap").forEach(function (b) {
        b.addEventListener("click", function (e) {
          e.preventDefault(); e.stopPropagation();
          var who = b.getAttribute("data-who"); var nv = !getAp(src)[who];
          setAp(src, who, nv); b.classList.toggle("on", nv);
          b.textContent = (nv ? "✓ " : "") + (who === "austin" ? "Austin" : "Saju") + " check";
        });
      });
      el.appendChild(bar);
    });
  }
  function exportApprovals() {
    var rows = [];
    for (var i = 0; i < LS.length; i++) {
      var k = LS.key(i); if (k.indexOf("cw_approve_") !== 0) continue;
      var v = getAp(k.slice("cw_approve_".length));
      rows.push({ file: k.slice("cw_approve_".length), austin: !!v.austin, saju: !!v.saju });
    }
    var blob = new Blob([JSON.stringify({ approvals: rows }, null, 1)], { type: "application/json" });
    var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "approvals.json"; a.click();
    alert(rows.length + " piece(s) with a check recorded. " + rows.filter(function (r) { return r.austin && r.saju; }).length + " have BOTH Austin and Saju.");
  }

  // ---- panel ----
  var panel, fab;
  function openPanel() { ensurePanel(); panel.classList.add("open"); }
  function ensurePanel() {
    if (panel) return;
    fab = document.createElement("button");
    fab.className = "cw-fab"; fab.title = "Highlight any line to leave a note or get an AI edit";
    fab.innerHTML = "✎ Review";
    fab.addEventListener("click", function () { ensurePanel(); panel.classList.toggle("open"); renderPanel(); });
    document.body.appendChild(fab);
    // one-time coach bubble so first-time reviewers know the gesture
    if (!LS.getItem("cw_coached")) {
      var coach = document.createElement("div");
      coach.className = "cw-coach";
      coach.innerHTML = "Highlight any line to leave a note or get an AI edit &times;";
      document.body.appendChild(coach);
      var hide = function () { coach.remove(); LS.setItem("cw_coached", "1"); };
      coach.addEventListener("click", hide);
      setTimeout(hide, 9000);
    }
    panel = document.createElement("aside");
    panel.className = "cw-panel";
    document.body.appendChild(panel);
    renderPanel();
  }
  function renderPanel() {
    if (!panel) return;
    var c = cfg();
    var list = notes().filter(function (n) { return n.status !== "deleted"; });
    var html = '<header><b>Review notes</b><span class="cw-x" data-act="close">×</span></header>';
    if (!list.length) html += '<p class="cw-empty">Select any text in the post and click <b>Add note</b>. Say what feels off, or what to add or cut, then hit <b>Suggest edit</b> and the AI rewrites just that part for you. No setup, no keys.</p>';
    list.forEach(function (n) {
      html += '<div class="cw-note' + (n.status === "resolved" ? " done" : "") + '" data-aid="' + n.aid + '">';
      html += '<blockquote>' + esc(n.quote.slice(0, 220)) + '</blockquote>';
      html += '<textarea placeholder="What should change here? e.g. this doesn\'t sound natural / cut this / add a number">' + esc(n.note) + '</textarea>';
      html += '<div class="cw-row"><button data-act="ai" data-aid="' + n.aid + '">✨ Suggest edit</button>' +
              '<button data-act="del" data-aid="' + n.aid + '" class="ghost">Delete</button></div>';
      if (n.revision) {
        html += '<div class="cw-rev"><div class="cw-rev-t">Suggested:</div><p>' + esc(n.revision) + '</p>' +
                '<div class="cw-row"><button data-act="accept" data-aid="' + n.aid + '">Accept</button>' +
                '<button data-act="reject" data-aid="' + n.aid + '" class="ghost">Reject</button></div></div>';
      }
      html += '</div>';
    });
    html += '<footer><button data-act="export" class="ghost">Export notes (md)</button><button data-act="exportjson" class="ghost">Export for AI editor</button><button data-act="exportap" class="ghost">Export approvals</button></footer>';
    panel.innerHTML = html;
    wire();
  }
  function wire() {
    panel.querySelectorAll("[data-k]").forEach(function (el) {
      el.addEventListener("change", function () { var c = cfg(); c[el.getAttribute("data-k")] = el.value; setCfg(c); });
    });
    panel.querySelectorAll(".cw-note textarea").forEach(function (ta) {
      ta.addEventListener("input", function () {
        var aid = ta.closest(".cw-note").getAttribute("data-aid");
        var arr = notes(); var n = arr.find(function (x) { return x.aid === aid; }); if (n) { n.note = ta.value; saveNotes(arr); }
      });
    });
    panel.querySelectorAll("[data-act]").forEach(function (b) {
      b.addEventListener("click", function () { act(b.getAttribute("data-act"), b.getAttribute("data-aid")); });
    });
  }

  function act(a, aid) {
    var arr = notes(); var n = aid && arr.find(function (x) { return x.aid === aid; });
    if (a === "close") { panel.classList.remove("open"); return; }
    if (a === "del" && n) { n.status = "deleted"; saveNotes(arr); var m = document.querySelector('mark[data-aid="' + aid + '"]'); if (m) m.replaceWith(document.createTextNode(m.textContent)); renderPanel(); return; }
    if (a === "reject" && n) { n.revision = ""; saveNotes(arr); renderPanel(); return; }
    if (a === "accept" && n) {
      var m = document.querySelector('mark[data-aid="' + aid + '"]');
      if (m) { m.textContent = n.revision; m.classList.add("done"); }
      n.status = "resolved"; n.applied = n.revision; saveNotes(arr); renderPanel(); return;
    }
    if (a === "export") { exportNotes(); return; }
    if (a === "exportjson") { exportNotesJSON(); return; }
    if (a === "exportap") { exportApprovals(); return; }
    if (a === "ai" && n) { suggest(n, arr); return; }
  }

  // ---- AI surgical edit ----
  function suggest(n, arr) {
    var c = cfg();
    var noteEl = panel.querySelector('.cw-note[data-aid="' + n.aid + '"]');
    var btn = noteEl && noteEl.querySelector('[data-act="ai"]');
    if (btn) { btn.disabled = true; btn.textContent = "Thinking…"; }
    var de = /[äöüß]/i.test(n.quote) || document.documentElement.lang === "de";
    // full surrounding post + keyword, so the edit has context (not just the isolated passage)
    var container = document.querySelector('.annotatable[data-cwid="' + n.cwid + '"]');
    var fullPost = container ? container.innerText.trim().slice(0, 1800) : "";
    var card = container && container.closest('.card, article') || container;
    var gt = function (sel) { return card && card.querySelector(sel) ? card.querySelector(sel).textContent.trim() : ""; };
    var kw = gt(".kw");
    var cat = (card && card.getAttribute("data-cat")) || "";
    var who = gt(".who");
    var goal = gt(".meta span:last-child") || (card && card.getAttribute("data-note-label")) || "";
    var channel = ({ "linkedin": "a LinkedIn post", "x": "an X post", "shortform": "a short-form video script",
      "youtube": "a long-form YouTube script", "visuals": "a carousel or quote card" }[
      (location.pathname.split("/").pop() || "").replace(/(-post-\d+)?\.html$/, "").replace(/^(script|blog)-.*/, "$1")
    ] || (/script-/.test(location.pathname) ? "a long-form YouTube script" : /\.html$/.test(location.pathname) ? "a blog article" : "a post"));
    var sys = "You are a surgical copy editor for CaseWhen, a Berlin Power BI / Microsoft Fabric / Azure consultancy that helps business buyers (controllers, CFOs, heads of data) get one trusted number. Rewrite ONLY the passage the reviewer selected, addressing their note, and make it fit naturally inside the full post you are given. "
      + "CaseWhen rules (obey all): (1) PROBLEM-FIRST — if the passage is the opening line, it must state the reader's real problem in plain everyday words with NO statistic, NO percentage, NO research-source name in that first line; earn the stat later. (2) NAME THE NOUN — never a vague placeholder ('the right things', 'something', 'what matters'); name the concrete thing. (3) At most one stat, and never default to Talend 40% / solvexia / revealbi 70% / ZoomInfo 82%; keep any stat's real source. (4) Keep the exact SEO keyword if present. (5) Plain, human, founder voice with contractions; be specific enough to be wrong. "
      + "Hard bans: no em dashes, no metaphors or analogies, no 'not X but Y' cadence, no hype or AI-slop words, no corny throat-clearing ('here's the thing', 'the good news', 'at its core', 'nobody tells you'), no jargon (DACH, TAM, ICP). "
      + "Brand rules (always): write \"Power BI\" with exactly that capitalization, never \"power bi\" or \"powerbi\" (leave URLs/slugs like power-bi-consultant and app.powerbi.com as they are); and never use the word \"board\" at all (no \"board report\", \"board pack\", \"board meeting\", \"boardroom\") — use \"management report\" for the document, \"leadership\" for the audience, \"leadership review\" for the meeting (German: Managementbericht / Management / Management-Meeting). "
      + "Return ONLY the revised passage as plain text, nothing else." + (de ? " The post is German; reply in natural German with correct ä/ö/ü and formal Sie." : "");
    var ctx = "THIS SPECIFIC POST — its identity and goal (keep the edit true to it): This is " + channel + " for CaseWhen aimed at a business buyer (a controller, CFO, or head of data), not an engineer."
      + (kw ? " Its target keyword is \"" + kw + "\" (preserve it)." : "")
      + (cat ? " Topic category: " + cat + "." : "")
      + (who ? " Author voice: " + who + "." : "")
      + (goal ? " Its intent/angle: " + goal + "." : "")
      + " The post's job is to make the buyer feel one real problem and trust CaseWhen to fix it. Your edit must serve that goal and stay plain and relatable to a non-technical decision maker.";
    var usr = ctx
      + "\n\nFULL POST (for context — do NOT rewrite this whole thing):\n" + fullPost
      + "\n\nTHE SELECTED PASSAGE TO REWRITE:\n" + n.quote
      + "\n\nREVIEWER NOTE:\n" + (n.note || "make it sound more natural and specific")
      + "\n\nReturn only the revised passage, fitting this post's voice and goal, and not repeating any other line in it.";
    callModel(c, sys, usr).then(function (out) {
      n.revision = (out || "").trim(); saveNotes(arr); renderPanel();
    }).catch(function (err) {
      if (btn) { btn.disabled = false; btn.textContent = "✨ Suggest edit"; }
      alert("AI request failed: " + (err && err.message ? err.message : err));
    });
  }

  // The CaseWhen key lives ONLY on this server-side proxy (origin-locked to this site).
  // Reviewers never see or enter a key — the AI edit just works.
  var CW_PROXY = "https://casewhen-ai-proxy-production.up.railway.app/edit";
  var CW_APP = "cw-preview-a7f3k9q2m5";
  function callModel(c, sys, usr) {
    return fetch(CW_PROXY, {
      method: "POST",
      headers: { "content-type": "application/json", "x-cw-app": CW_APP },
      body: JSON.stringify({ model: c.model || "claude-sonnet-4-5", max_tokens: 700, system: sys, messages: [{ role: "user", content: usr }] })
    }).then(chk).then(function (j) { return (j.content && j.content[0] && j.content[0].text) || ""; });
  }
  function chk(r) { if (!r.ok) { return r.text().then(function (t) { throw new Error(r.status + " " + t.slice(0, 160)); }); } return r.json(); }

  function exportNotes() {
    var list = notes().filter(function (n) { return n.status !== "deleted"; });
    var md = "# Review notes for " + location.pathname + "\n\n";
    list.forEach(function (n, i) {
      md += (i + 1) + ". **Selected:** " + n.quote + "\n   - **Note:** " + (n.note || "(none)") + "\n";
      if (n.revision) md += "   - **AI suggestion" + (n.status === "resolved" ? ", ACCEPTED" : "") + ":** " + n.revision + "\n";
      md += "\n";
    });
    var blob = new Blob([md], { type: "text/markdown" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "review-notes" + PATH + ".md"; a.click();
  }

  // Export in the format the GitHub Action (apply_notes.py) consumes: [{file, selection, note}].
  // Commit the downloaded file to the research repo as review-notes/pending.json to trigger the editor.
  function exportNotesJSON() {
    var list = notes().filter(function (n) { return n.status !== "deleted" && (n.note || "").trim(); });
    var items = list.filter(function (n) { return n.src; }).map(function (n) {
      return { file: n.src, selection: n.quote || "", note: n.note || "" };
    });
    var missing = list.length - items.length;
    var payload = JSON.stringify({ notes: items }, null, 1);
    var blob = new Blob([payload], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "pending.json"; a.click();
    alert(items.length + " note(s) exported to pending.json.\nCommit it to the research repo as review-notes/pending.json to run the AI editor." +
      (missing ? "\n\n(" + missing + " note(s) skipped: no source file on that element.)" : ""));
  }

  function boot() {
    if (!document.querySelector(".annotatable")) return;
    collectContainers();
    ensurePanel();
    rehighlight();
    document.addEventListener("mouseup", function () { setTimeout(onSelect, 10); });
    document.addEventListener("selectionchange", function () { if (window.getSelection().isCollapsed && pop) pop.style.display = "none"; });
    // image cards (carousels, quote cards) get a "Note this" button instead of text-selection
    document.querySelectorAll(".cw-notebtn").forEach(function (b) {
      b.addEventListener("click", function (e) { e.preventDefault(); e.stopPropagation(); openDeckNote(b.closest(".annotatable")); });
    });
    injectApprovals();  // Austin/Saju check on every reviewable piece
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
