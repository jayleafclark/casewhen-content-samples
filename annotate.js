/* CaseWhen preview review layer.
   Highlight any section of a blog / script / LinkedIn / X post (EN or DE), attach a note,
   and (with your own API key) get a surgical AI edit back that you can accept inline.
   100% client-side. Your API key stays in this browser (localStorage), nothing is sent
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

  // ---- panel ----
  var panel, fab;
  function openPanel() { ensurePanel(); panel.classList.add("open"); }
  function ensurePanel() {
    if (panel) return;
    fab = document.createElement("button");
    fab.className = "cw-fab"; fab.title = "Review this page";
    fab.innerHTML = "✎ Review";
    fab.addEventListener("click", function () { ensurePanel(); panel.classList.toggle("open"); renderPanel(); });
    document.body.appendChild(fab);
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
    html += '<div class="cw-cfg"><details><summary>AI settings (your key)</summary>' +
      '<label>Provider<select data-k="provider"><option value="anthropic"' + (c.provider !== "openai" ? " selected" : "") + '>Anthropic (Claude)</option><option value="openai"' + (c.provider === "openai" ? " selected" : "") + '>OpenAI</option></select></label>' +
      '<label>Model<input data-k="model" value="' + esc(c.model || (c.provider === "openai" ? "gpt-4o-mini" : "claude-sonnet-4-5")) + '"></label>' +
      '<label>API key<input data-k="key" type="password" placeholder="sk-... (stays in this browser)" value="' + esc(c.key || "") + '"></label>' +
      '<small>Your key is stored only in this browser and sent directly to the provider.</small>' +
      '</details></div>';
    if (!list.length) html += '<p class="cw-empty">Select any text in the post and click <b>Add note</b>. Say what feels off or what to add or cut. With your API key set, the AI makes a surgical edit to just that part.</p>';
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
    html += '<footer><button data-act="export" class="ghost">Export notes</button></footer>';
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
    if (a === "ai" && n) { suggest(n, arr); return; }
  }

  // ---- AI surgical edit ----
  function suggest(n, arr) {
    var c = cfg();
    if (!c.key) { alert("Add your API key first (AI settings, top of the panel)."); return; }
    var noteEl = panel.querySelector('.cw-note[data-aid="' + n.aid + '"]');
    var btn = noteEl && noteEl.querySelector('[data-act="ai"]');
    if (btn) { btn.disabled = true; btn.textContent = "Thinking…"; }
    var de = /[äöüß]/i.test(n.quote) || document.documentElement.lang === "de";
    var sys = "You are a surgical copy editor for CaseWhen, a Berlin Power BI / Fabric / Azure consultancy. Rewrite ONLY the passage the reviewer selected, addressing their note. Keep the meaning, any statistics and their sources, and any SEO keywords. Keep the casual, human, founder voice with contractions. Hard rules: no em dashes, no metaphors or analogies, no 'not X but Y' cadence, no hype/AI-slop words, no corny phrasing. Return ONLY the revised passage as plain text, nothing else." + (de ? " The passage is German; reply in natural German." : "");
    var usr = "PASSAGE:\n" + n.quote + "\n\nREVIEWER NOTE:\n" + (n.note || "make it sound more natural") + "\n\nReturn only the revised passage.";
    callModel(c, sys, usr).then(function (out) {
      n.revision = (out || "").trim(); saveNotes(arr); renderPanel();
    }).catch(function (err) {
      if (btn) { btn.disabled = false; btn.textContent = "✨ Suggest edit"; }
      alert("AI request failed: " + (err && err.message ? err.message : err));
    });
  }

  function callModel(c, sys, usr) {
    if (c.provider === "openai") {
      return fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: { "content-type": "application/json", "authorization": "Bearer " + c.key },
        body: JSON.stringify({ model: c.model || "gpt-4o-mini", temperature: 0.4, messages: [{ role: "system", content: sys }, { role: "user", content: usr }] })
      }).then(chk).then(function (j) { return j.choices[0].message.content; });
    }
    return fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": c.key,
        "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true"
      },
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

  function boot() {
    if (!document.querySelector(".annotatable")) return;
    collectContainers();
    ensurePanel();
    rehighlight();
    document.addEventListener("mouseup", function () { setTimeout(onSelect, 10); });
    document.addEventListener("selectionchange", function () { if (window.getSelection().isCollapsed && pop) pop.style.display = "none"; });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
