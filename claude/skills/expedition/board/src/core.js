// The words of format 2.2 in the four plan views (Epics, Tasks, Sprints, Milestones).
const STATUSES = ["to-do", "in progress", "blocked", "done", "archived"];
// Queue statuses (v2.1.x D8; no queue item is in progress) share these maps with the task statuses.
const QSTATUSES = ["to-do", "blocked", "done", "backlog", "archived"];
const SK = { "not started": "ns", "in progress": "prog", "blocked": "block", "done": "done", "skipped": "skip",
  "to-do": "qo", backlog: "ql", archived: "qx" };
const SICON = { "not started": "circle", "in progress": "clock", "blocked": "stop", "done": "check-circle", "skipped": "ban",
  "to-do": "circle-dot", backlog: "clock", archived: "ban" };
const VIEWS = ["dash", "epics", "tasks", "sprints", "milestones", "queue"];
const VIEW_INFO = { dash: ["Dashboard", "gauge"], epics: ["Epics", "lanes"], tasks: ["Tasks", "kanban"], sprints: ["Sprints", "columns"], milestones: ["Milestones", "list"], queue: ["Queue", "inbox"] };
// Dashboard groups and row kinds, from dashboard.data.js.
// Dashboard: one card per item; columns are the six statuses, the same words for every kind.
const GROUPS = ["to-do", "in progress", "blocked", "done", "backlog", "archived"];
const GROUP_INFO = { "to-do": ["To-do", "circle", "c-ns"], "in progress": ["In progress", "clock", "c-prog"], blocked: ["Blocked", "stop", "c-block"],
  done: ["Done", "check-circle", "c-done"], backlog: ["Backlog", "inbox", "c-ns"], archived: ["Archived", "ban", "c-skip"] };
const DSTATUS = { "to-do": ["ns", "circle"], "in progress": ["prog", "clock"], blocked: ["block", "stop"], done: ["done", "check-circle"], backlog: ["ql", "inbox"], archived: ["skip", "ban"] };
// A board layout, a view setting apart from the filters: custom column order (empty: the default order), widths in px, hidden columns, card second line.
const defSpLayout = () => ({ order: [], widths: {}, hidden: [], sub: true });
function cleanSpLayout(l) {
  if (!l || typeof l !== "object") return defSpLayout();
  const str = (a) => Array.isArray(a) ? a.filter((x) => typeof x === "string") : [];
  const widths = {};
  if (l.widths && typeof l.widths === "object") for (const [k, v] of Object.entries(l.widths)) if (Number.isFinite(v) && v > 0) widths[k] = Math.round(v);
  return { order: str(l.order), widths, hidden: str(l.hidden), sub: l.sub !== false };
}
// Whose turn: you (strong marker), the lead or an agent (muted).
const TURNS = ["you", "lead", "agent"];
const TURN_INFO = { you: ["You", "user", "Your turn"], lead: ["Lead", "compass", "The lead's turn"], agent: ["Agent", "bot", "An agent's turn"] };
const KINDS = ["queue", "decision", "epic", "milestone", "task"];
const DV = () => state.view === "dash";
// A plan view shows "to-do" and "archived" with the look of "not started" and "skipped"; the Queue and
// Dashboard views keep the look of SK and SICON for the two words.
const PLAN_SK = { "to-do": "ns", archived: "skip" }, PLAN_SICON = { "to-do": "circle", archived: "ban" };
const planView = () => state.view !== "queue" && !DV();
const skOf = (st) => (planView() && PLAN_SK[st]) || SK[st];
const siconOf = (st) => (planView() && PLAN_SICON[st]) || SICON[st];
const KIND_LABEL = { epic: "Epic", spec: "Spec", ms: "Milestone", task: "Task", sprint: "Sprint", q: "Queue item" };
// Folder of status.data.js and dashboard.data.js, relative to this page.
const DATA_DIR = "data/";
const CHILD = { epic: "spec", spec: "ms", ms: "task", sprint: "ms" };
// Done and archived columns in the Tasks view show this many compact rows until "Show all".
const COMPACT_LIMIT = 60;

// Sort options per view; the first is the default and gives the order the view had before sorting existed.
// "Plan order" is the data order: follow-up specs such as 20.1.1 come after 20.3 there, so it differs from ref order.
// Sprints: the option orders the milestone rows, the direction button orders the sprints (-1 newest first).
const SORTS = {
  epics: { opts: [["id", "Epic id"], ["progress", "Progress"], ["status", "Status"], ["changed", "Last change"]], def: { key: "id", dir: 1 } },
  tasks: { opts: [["newest", "Newest"], ["ref", "Milestone ref"], ["epic", "Epic"], ["changed", "Last change"], ["type", "Type"]], def: { key: "newest", dir: 1 } },
  sprints: { opts: [["plan", "Plan order"], ["ref", "Milestone ref"], ["status", "Status"], ["progress", "Progress"]], def: { key: "plan", dir: -1 } },
  milestones: { opts: [["plan", "Plan order"], ["ref", "Milestone ref"], ["status", "Status"], ["progress", "Progress"], ["changed", "Last change"]], def: { key: "plan", dir: 1 } },
  queue: { opts: [["status", "Status"], ["number", "Number"]], def: { key: "status", dir: 1 } },
  dash: { opts: [["group", "Group"], ["kind", "Kind"], ["order", "Data order"]], def: { key: "group", dir: 1 } },
};
const defSorts = () => Object.fromEntries(Object.entries(SORTS).map(([v, o]) => [v, { ...o.def }]));
const DEFAULTS = { view: "dash", status: [], qstatus: [], gfilter: [], kfilter: [], tfilter: [], lfold: {}, dlayout: null, smode: "list", splayout: null, qlayout: null, tlayout: null, qmode: "list", dmode: "board", q: "", more: [], sorts: defSorts(), arrows: true, crit: false, compact: true, zoom: 100, fill: true };
const state = { ...DEFAULTS, dlayout: defSpLayout(), splayout: defSpLayout(), qlayout: defSpLayout(), tlayout: defSpLayout(), sel: null, open: { c: new Set(), sp: new Set(), le: new Set(), lm: new Set() } };
try {
  const ui = JSON.parse(localStorage.getItem("dashboard-ui") || "{}");
  for (const k of Object.keys(DEFAULTS)) if (k in ui) state[k] = ui[k];
  if (!VIEWS.includes(state.view)) state.view = DEFAULTS.view;
  state.status = Array.isArray(state.status) ? state.status.filter((s) => STATUSES.includes(s)) : [];
  state.qstatus = Array.isArray(state.qstatus) ? state.qstatus.filter((s) => QSTATUSES.includes(s)) : [];
  if (state.qmode !== "board") state.qmode = "list";
  if (state.dmode !== "list") state.dmode = "board";
  if (!Array.isArray(state.gfilter)) state.gfilter = [];
  if (!Array.isArray(state.kfilter)) state.kfilter = [];
  if (!Array.isArray(state.tfilter)) state.tfilter = [];
  if (!state.lfold || typeof state.lfold !== "object" || Array.isArray(state.lfold)) state.lfold = {};
  for (const [k, v] of Object.entries(state.lfold)) if (!Array.isArray(v)) delete state.lfold[k];
  if (Array.isArray(ui.dfold) && !state.lfold.dash) state.lfold.dash = ui.dfold;
  for (const k of ["dlayout", "splayout", "qlayout", "tlayout"]) state[k] = cleanSpLayout(state[k]);
  if (state.smode !== "board") state.smode = "list";
  state.gfilter = state.gfilter.filter((g) => GROUPS.includes(g));
  const saved = state.sorts && typeof state.sorts === "object" ? state.sorts : {};
  state.sorts = defSorts();
  for (const v of Object.keys(SORTS)) {
    const x = saved[v];
    if (x && SORTS[v].opts.some(([k]) => k === x.key) && (x.dir === 1 || x.dir === -1)) state.sorts[v] = { key: x.key, dir: x.dir };
  }
  const op = JSON.parse(localStorage.getItem("taskboard-open") || "{}");
  for (const k of Object.keys(state.open)) state.open[k] = new Set(op[k] || []);
} catch (e) {}
const save = () => { try {
  const ui = {}; for (const k of Object.keys(DEFAULTS)) ui[k] = state[k];
  localStorage.setItem("dashboard-ui", JSON.stringify(ui));
  const op = {}; for (const k of Object.keys(state.open)) op[k] = [...state.open[k]];
  localStorage.setItem("taskboard-open", JSON.stringify(op));
} catch (e) {} };

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const board = $("#board"), panel = $("#panel");

// "updated 2h ago" from the data's "YYYY-MM-DD HH:MM" (local time); the exact time is the tooltip.
function relTime(txt) {
  const m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(txt || "");
  if (!m) return txt || "?";
  const mins = Math.round((Date.now() - new Date(+m[1], m[2] - 1, +m[3], +m[4], +m[5]).getTime()) / 60000);
  // A time ahead of this clock: show it plainly, the time alone when it is today.
  if (mins < -1) return new Date().toDateString() === new Date(+m[1], m[2] - 1, +m[3]).toDateString() ? `at ${m[4]}:${m[5]}` : txt;
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  if (mins < 48 * 60) return `${Math.round(mins / 60)}h ago`;
  return `${Math.round(mins / 1440)}d ago`;
}
// The update time leaves the bar only when the bar would wrap; the reload tooltip still carries it.
function fitUpdated() {
  const u = $("#upd"), bar = $(".bar-in");
  u.hidden = false;
  if (bar.offsetHeight > 64) u.hidden = true;
}
addEventListener("resize", () => { if (D) fitUpdated(); });
function showUpdated() {
  const el = $("#upd");
  el.textContent = `updated ${relTime(D.updated)}`;
  el.title = `Updated ${D.updated ?? "?"}`;
  $("#reload").dataset.tip = `Reload data (also every 30 seconds) · ${el.textContent}`;
  fitUpdated();
}

// ---- Data and indexes (derived here; the data file holds only stored facts) ----
let D, idx, kids, cnt, hay, dependents, sprintPos, epicMs, lastChange, dataPos;
function load(data) {
  D = data;
  idx = { epic: new Map(), spec: new Map(), ms: new Map(), task: new Map(), sprint: new Map() };
  D.epics.forEach((o) => idx.epic.set(o.id, o));
  D.specs.forEach((o) => idx.spec.set(o.id, o));
  D.milestones.forEach((o) => idx.ms.set(o.id, o));
  D.tasks.forEach((o) => idx.task.set(o.id, o));
  D.sprints.forEach((o) => idx.sprint.set(o.id, o));
  sprintPos = new Map(D.sprints.map((s, i) => [s.id, i]));
  kids = new Map();
  epicMs = new Map(D.epics.map((e) => [e.id, []]));
  const push = (k, v) => { let a = kids.get(k); if (!a) kids.set(k, a = []); a.push(v); };
  D.epics.forEach((e) => kids.set(e, (e.specs || []).map((id) => idx.spec.get(id)).filter(Boolean)));
  D.specs.forEach((s) => { kids.set(s, []); const e = idx.epic.get(s.epic); if (e && !(e.specs || []).includes(s.id)) push(e, s); });
  D.sprints.forEach((s) => kids.set(s, []));
  D.milestones.forEach((m) => {
    kids.set(m, []);
    const s = idx.spec.get(m.spec); if (s) push(s, m);
    const sp = idx.sprint.get(m.sprint); if (sp) push(sp, m);
    epicMs.get(m.epic)?.push(m);
  });
  D.tasks.forEach((t) => { kids.set(t, []); const m = idx.ms.get(t.milestone); if (m) push(m, t); });
  dependents = new Map(D.milestones.map((m) => [m.id, []]));
  D.milestones.forEach((m) => (m.depends || []).forEach((d) => dependents.get(d)?.push(m.id)));
  // Task counts per status, rolled up: milestone, spec, epic, sprint.
  cnt = new Map();
  const zero = () => Object.fromEntries(STATUSES.map((s) => [s, 0]).concat([["total", 0]]));
  const add = (a, b) => { STATUSES.forEach((s) => (a[s] += b[s])); a.total += b.total; };
  D.milestones.forEach((m) => { const c = zero(); kids.get(m).forEach((t) => { if (t.status in c) c[t.status]++; c.total++; }); cnt.set(m, c); });
  for (const p of [...D.specs, ...D.sprints]) { const c = zero(); kids.get(p).forEach((m) => add(c, cnt.get(m))); cnt.set(p, c); }
  D.epics.forEach((e) => { const c = zero(); kids.get(e).forEach((s) => add(c, cnt.get(s))); cnt.set(e, c); });
  // Search text: own words plus every parent's, so "E35 release" finds the specs of E35.
  hay = new Map();
  const low = (...a) => a.filter((x) => x != null && x !== "").join(" ").toLowerCase();
  D.epics.forEach((e) => hay.set(e, low(e.id, e.name)));
  D.specs.forEach((s) => hay.set(s, low(s.id, "#" + s.id, s.title) + " " + (hay.get(idx.epic.get(s.epic)) || "")));
  D.milestones.forEach((m) => hay.set(m, low(m.id, m.name, m.sprint, m.commit) + " " + (hay.get(idx.spec.get(m.spec)) || hay.get(idx.epic.get(m.epic)) || "")));
  D.tasks.forEach((t) => hay.set(t, low(t.id, t.number, `${t.spec}-${t.number}`, t.title, t.type, t.decision) + " " + (hay.get(idx.ms.get(t.milestone)) || "")));
  D.sprints.forEach((s) => hay.set(s, low(s.id)));
  // Last change of an epic: the latest `changed` of its milestones and their tasks.
  lastChange = new Map(D.epics.map((e) => {
    let max = null;
    for (const m of epicMs.get(e.id)) for (const x of [m, ...kids.get(m)]) if (x.changed && (!max || x.changed > max)) max = x.changed;
    return [e, max];
  }));
  dataPos = new Map([...D.milestones, ...D.tasks, ...D.epics].map((x, i) => [x, i]));

  if (foldRelease !== D.release) loadFold();
  $("#rel").textContent = D.release;
  const all = { d: D.tasks.filter((x) => x.status === "done" || x.status === "archived").length, n: D.tasks.length };
  const td = $("#tdone");
  td.innerHTML = `${icon("check-circle")}${all.d}/${all.n}`;
  td.title = `${all.d} of ${all.n} tasks done`;
  showUpdated();
  if (state.sel && !get(state.sel)) state.sel = null;
}
const get = (pick) => { const i = pick.indexOf(":"), k = pick.slice(0, i); return (k === "q" ? qIdx : k === "r" ? dIdx : idx[k])?.get(pick.slice(i + 1)); };
// A milestone shows its ref, "<spec>.<number>"; older data without it falls back to the spec id.
const label = (kind, o) => kind === "task" ? `${o.spec}-${o.number}` : kind === "ms" ? (o.ref || o.spec) : o.id;
const title = (kind, o) => o.name || o.title || o.id;
const doneOf = (c) => `${c.done + c.archived}/${c.total}`;
// ---- Filter: status buttons and search, applied the same way in every view ----
let terms = [], stSet = null, passMemo = new Map();
const active = () => terms.length > 0 || stSet !== null;
function prepFilter() {
  terms = state.q.toLowerCase().split(/\s+/).filter(Boolean);
  stSet = state.status.length ? new Set(state.status) : null;
  passMemo = new Map();
}
const selfPass = (o) => (!stSet || stSet.has(o.status)) && terms.every((t) => hay.get(o).includes(t));
// An item shows when it passes itself or holds something that does (so the path to a match stays visible).
function pass(o, kind) {
  if (!active()) return true;
  let r = passMemo.get(o);
  if (r === undefined) {
    r = kind !== "sprint" && selfPass(o);
    if (!r && CHILD[kind]) r = kids.get(o).some((c) => pass(c, CHILD[kind]));
    passMemo.set(o, r);
  }
  return r;
}
const shownKids = (o, kind) => kids.get(o).filter((c) => pass(c, CHILD[kind]));

const isSel = (pick) => state.sel === pick ? " sel" : "";
// ---- Sorting: numbers compare as numbers, refs and spec ids per dot segment ("90.10" after "90.9") ----
const sortOf = () => state.sorts[state.view] || SORTS[state.view].def;
const segs = (v) => String(v).split(".").map((x) => /^\d+$/.test(x) ? +x : x);
function cmp(a, b) {
  if (Array.isArray(a) && Array.isArray(b)) {
    for (let i = 0; i < Math.max(a.length, b.length); i++) {
      if (a[i] === undefined) return -1;
      if (b[i] === undefined) return 1;
      const c = cmp(a[i], b[i]);
      if (c) return c;
    }
    return 0;
  }
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true });
}
// A missing value (null) sorts last in both directions; ties keep the data order.
function sorted(list, key, dir) {
  if (!key) return list;
  return list.map((x) => [key(x), x]).sort((p, q) => {
    if (p[0] == null || q[0] == null) return p[0] == null && q[0] == null ? dataPos.get(p[1]) - dataPos.get(q[1]) : p[0] == null ? 1 : -1;
    return (cmp(p[0], q[0]) || dataPos.get(p[1]) - dataPos.get(q[1])) * dir;
  }).map((p) => p[1]);
}
const pct = (c) => c.total ? (c.done + c.archived) / c.total : null;
const stIdx = (o) => STATUSES.indexOf(o.status);
const MS_KEYS = {
  plan: (m) => dataPos.get(m), ref: (m) => segs(m.ref || m.spec), status: stIdx, progress: (m) => pct(cnt.get(m)), changed: (m) => m.changed || null,
};
const EPIC_KEYS = {
  id: (e) => dataPos.get(e), progress: (e) => pct(cnt.get(e)), status: stIdx, changed: (e) => lastChange.get(e),
};
const TASK_KEYS = {
  newest: (t) => -dataPos.get(t), ref: (t) => { const m = idx.ms.get(t.milestone); return m ? segs(m.ref || m.spec) : null; },
  epic: (t) => idx.ms.get(t.milestone)?.epic ?? null, changed: (t) => t.changed || null, type: (t) => t.type || null,
};

// Markdown, a safe subset: paragraphs, nested lists, headings, fenced code, `code`, **bold**, *italic*, http(s) links.
function mdInline(s) {
  return String(s).split(/(`[^`]*`)/).map((p, i) => i % 2 ? `<code>${esc(p.slice(1, -1))}</code>` : esc(p)
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[\s(])\*([^*\s][^*]*?)\*(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>")).join("");
}
function md(src) {
  const lines = String(src || "").replace(/\r/g, "").split("\n"), stack = [];
  let out = "", para = [], fence = null;
  const flush = () => { if (para.length) { out += `<p>${mdInline(para.join(" "))}</p>`; para = []; } };
  const closeTo = (ind) => { while (stack.length && stack[stack.length - 1].ind > ind) out += `</li></${stack.pop().type}>`; };
  for (const line of lines) {
    if (fence) { if (/^\s*```/.test(line)) { out += `<pre><code>${esc(fence.join("\n"))}</code></pre>`; fence = null; } else fence.push(line); continue; }
    if (/^\s*```/.test(line)) { flush(); closeTo(-1); fence = []; continue; }
    if (!line.trim()) { flush(); continue; }
    const li = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/.exec(line);
    if (li) {
      flush();
      const ind = li[1].replace(/\t/g, "    ").length, type = /\d/.test(li[2]) ? "ol" : "ul";
      closeTo(ind);
      const top = stack[stack.length - 1];
      if (top && top.ind === ind && top.type === type) out += "</li><li>";
      else {
        if (top && top.ind === ind) out += `</li></${stack.pop().type}>`;
        out += `<${type}${type === "ol" ? ` start="${parseInt(li[2], 10)}"` : ""}><li>`;
        stack.push({ type, ind });
      }
      out += mdInline(li[3]);
      continue;
    }
    const h = /^#{1,6}\s+(.*)$/.exec(line);
    if (h) { flush(); closeTo(-1); out += `<h4>${mdInline(h[1])}</h4>`; continue; }
    if (stack.length && /^\s/.test(line)) { out += " " + mdInline(line.trim()); continue; }
    closeTo(-1);
    para.push(line.trim());
  }
  if (fence) out += `<pre><code>${esc(fence.join("\n"))}</code></pre>`;
  flush(); closeTo(-1);
  return out;
}
// ---- Side panel ----
const encPath = (p) => p.split("/").map(encodeURIComponent).join("/");
const absPath = (rel) => D.root ? D.root.replace(/\/+$/, "") + "/" + rel : "";
const vscodeUrl = (p) => "vscode://file" + encPath(p);
const fileUrl = (p) => "file://" + encPath(p);
const fileBtns = (rel) => {
  const abs = rel && absPath(rel);
  return abs ? `<a class="fbtn" href="${esc(vscodeUrl(abs))}" title="${esc(abs)}">VS Code</a><a class="fbtn" href="${esc(fileUrl(abs))}" target="_blank" title="${esc(abs)}">Browser</a>` : "";
};
const fileLink = (rel) => rel ? `<div class="lnk"><code class="path">${esc(rel)}</code>${fileBtns(rel)}</div>` : "";
// Spec files of a list of specs, each with its title and open buttons.
const specLinks = (specs) => specs.length ? `<ul class="lnk-list">${specs.map((s) => `<li><div class="lt"><button class="link" data-pick="spec:${esc(s.id)}">Spec ${esc(s.id)}</button> ${esc(s.title)}</div>${fileLink(s.path)}</li>`).join("")}</ul>` : "";
function crumbs(kind, o) {
  const path = [];
  const t = kind === "task" ? o : null;
  const m = kind === "ms" ? o : t ? idx.ms.get(t.milestone) : null;
  const s = kind === "spec" ? o : m ? idx.spec.get(m.spec) : null;
  const e = kind === "epic" ? o : s ? idx.epic.get(s.epic) : m ? idx.epic.get(m.epic) : null;
  if (kind === "sprint") path.push(["sprint", o]);
  if (e) path.push(["epic", e]);
  if (s) path.push(["spec", s]);
  if (m) path.push(["ms", m]);
  if (t) path.push(["task", t]);
  return path.map(([k, x], i) => {
    const txt = k === "spec" ? kc("spec", `Spec ${x.id}`) : k === "ms" ? `${kc("ms", label("ms", x))} ${esc(x.name)}` : k === "task" ? kc("task", `${x.spec}-${x.number}`) : kc(k, x.id);
    const ic = k === "ms" ? icon("flag", "mi") : "";
    return i === path.length - 1 ? `<span class="cur">${ic}${txt}</span>` : `<button data-pick="${k}:${esc(x.id)}" title="${esc(title(k, x))}">${ic}${txt}</button><span class="sep">›</span>`;
  }).join("");
}
const checkItem = (kind, x) => {
  const c = kind !== "task" ? cnt.get(x) : null;
  const abs = kind === "task" && x.file ? absPath(x.file) : "";
  return `<li class="ck ${skOf(x.status) || "ns"}" data-pick="${kind}:${esc(x.id)}" title="${esc(x.status + (x.reason ? ": " + x.reason : ""))}">${sicon(x.status)}${kind === "ms" ? icon("flag", "mi") : ""}<span class="num ck-chip">${kc(kind, kind === "spec" ? "Spec " + x.id : label(kind, x))}</span><span class="ck-name">${esc(title(kind, x))}</span>${kind === "task" && x.ownerCheck ? `<span class="owner">${icon("eye")}owner</span>` : ""}${c ? `<span class="frac">${doneOf(c)}</span>` : ""}${abs ? `<a class="fbtn open-f" href="${esc(vscodeUrl(abs))}" title="Open the task file in VS Code: ${esc(x.file)}">open</a>` : ""}</li>`;
};
const sec = (h, body) => body ? `<div class="p-sec"><h3>${h}</h3>${body}</div>` : "";
const checklist = (kind, list) => list.length ? `<ul class="checklist">${list.map((x) => checkItem(kind, x)).join("")}</ul>` : "";
const uniqSpecs = (ms) => [...new Set(ms.map((m) => m.spec))].map((id) => idx.spec.get(id)).filter(Boolean);
let lastPanelSel = null;
function renderPanel(scrollTop) {
  const o = state.sel && get(state.sel);
  if (!o) { state.sel = null; lastPanelSel = null; panel.hidden = true; panel.innerHTML = ""; return; }
  const kind = state.sel.slice(0, state.sel.indexOf(":"));
  const wasHidden = panel.hidden, changed = state.sel !== lastPanelSel;
  lastPanelSel = state.sel;
  panel.classList.toggle("wide", kind === "q" || kind === "r");
  if (kind === "q" || kind === "r") {
    panel.hidden = false;
    panel.innerHTML = `<div class="p-body${changed && !wasHidden ? " fx" : ""}">${kind === "r" ? dashPanel(o) : queuePanel(o)}</div>`;
    if (wasHidden) fxClass(panel, "fx-in");
    panel.scrollTop = scrollTop || 0;
    return;
  }
  let h = `<div class="p-top"><nav class="crumbs" aria-label="Breadcrumb">${crumbs(kind, o)}</nav>
    <button class="ibtn sm" data-close aria-label="Close" data-tip="Close (Esc)" data-tip-end>${icon("x")}</button></div>
    <div class="p-kind">${kind === "ms" ? icon("flag", "mi") : ""}${KIND_LABEL[kind]} ${kc(kind, kind === "spec" ? o.id : label(kind, o))}</div><h2>${esc(title(kind, o))}</h2>
    <div class="p-row">${pill(o.status)}${kind === "task" ? `<span class="tag">${esc(o.type)}</span>` : ""}${o.ownerCheck ? `<span class="owner">${icon("eye")}owner check</span>` : ""}${o.critical ? `<span class="tag">critical path</span>` : ""}</div>`;
  if (o.reason) h += `<div class="p-reason s-${skOf(o.status)}" style="text-decoration:none">${esc(o.reason)}</div>`;
  if (kind !== "task") {
    const c = cnt.get(o);
    h += sec("Progress", `${progress(c)}<div class="breakdown">${STATUSES.filter((s) => c[s]).map((s) => `<span class="pill s-${skOf(s)}">${c[s]} ${esc(s)}</span>`).join("")}</div>`);
  }
  if (kind === "epic") h += sec(`Specs (${kids.get(o).length})`, specLinks(kids.get(o)));
  if (kind === "spec") {
    h += sec("Spec file", fileLink(o.path));
    h += sec(`Milestones (${kids.get(o).length})`, checklist("ms", kids.get(o)));
    const tasks = kids.get(o).flatMap((m) => kids.get(m));
    h += sec(`Tasks (${tasks.length})`, checklist("task", tasks));
  }
  if (kind === "sprint") {
    h += sec(`Milestones (${kids.get(o).length})`, checklist("ms", kids.get(o)));
    const specs = uniqSpecs(kids.get(o));
    h += sec(`Spec file${specs.length === 1 ? "" : "s"}`, specLinks(specs));
  }
  if (kind === "ms") {
    h += `<div class="p-sec"><dl class="kv"><dt>Sprint</dt><dd><button class="link" data-pick="sprint:${esc(o.sprint)}">${esc(o.sprint)}</button></dd>
      <dt>Epic</dt><dd><button class="link" data-pick="epic:${esc(o.epic)}">${esc(o.epic)}</button> ${esc(idx.epic.get(o.epic)?.name)}</dd>
      <dt>Spec</dt><dd><button class="link" data-pick="spec:${esc(o.spec)}">Spec ${esc(o.spec)}</button> ${esc(idx.spec.get(o.spec)?.title)}${o.section ? `<span class="frac"> · section ${esc(o.section)}</span>` : ""}</dd>
      ${o.changed ? `<dt>Changed</dt><dd>${esc(o.changed)}</dd>` : ""}${o.commit ? `<dt>Commit</dt><dd><code>${esc(o.commit)}</code></dd>` : ""}</dl></div>`;
    const s = idx.spec.get(o.spec);
    if (s) h += sec("Spec file", fileLink(s.path));
    h += sec("Outcome", o.outcome ? `<p>${esc(o.outcome)}</p>` : "");
    h += sec(`Tasks (${kids.get(o).length})`, checklist("task", kids.get(o)));
    h += sec(`Depends on (${(o.depends || []).length})`, checklist("ms", (o.depends || []).map((d) => idx.ms.get(d)).filter(Boolean)));
    h += sec(`Needed by (${dependents.get(o.id).length})`, checklist("ms", dependents.get(o.id).map((d) => idx.ms.get(d))));
    h += sec(`Files (${(o.files || []).length})`, (o.files || []).length ? `<ul class="files">${o.files.map((f) => `<li><code class="path">${esc(f)}</code></li>`).join("")}</ul>` : "");
  }
  if (kind === "task") {
    const m = idx.ms.get(o.milestone);
    h += `<div class="p-sec"><dl class="kv"><dt>Milestone</dt><dd>${m ? `${icon("flag", "mi")}<button class="link" data-pick="ms:${esc(m.id)}">${esc(msText(m))}</button> ${pill(m.status)}` : esc(o.milestone)}</dd>
      ${m ? `<dt>Sprint</dt><dd><button class="link" data-pick="sprint:${esc(m.sprint)}">${esc(m.sprint)}</button></dd>` : ""}
      <dt>Type</dt><dd>${esc(o.type)}</dd>${o.decision ? `<dt>Decision</dt><dd>${esc(o.decision)}</dd>` : ""}
      ${o.changed ? `<dt>Changed</dt><dd>${esc(o.changed)}</dd>` : ""}<dt>Owner check</dt><dd>${o.ownerCheck ? "yes, waits for the owner's look" : "no"}</dd></dl></div>`;
    h += sec("Task file", o.file ? fileLink(o.file) : `<p class="frac">This task has no file.</p>`);
    if (m) h += sec("Other tasks in this milestone", checklist("task", kids.get(m)));
  }
  h += `<p class="pnote">Paths are relative to the ${esc(D.release)} release folder${D.root ? `: <code>${esc(D.root)}</code>` : ""}.</p>`;
  panel.hidden = false;
  panel.innerHTML = `<div class="p-body${changed && !wasHidden ? " fx" : ""}">${h}</div>`;
  if (wasHidden) fxClass(panel, "fx-in");
  panel.scrollTop = scrollTop || 0;
}

function syncControls() {
  const [vName, vIc] = VIEW_INFO[state.view];
  $("#view-label").textContent = vName;
  $("#view-ic").setAttribute("href", "#ic-" + vIc);
  if (!$("#view-pop").hidden) renderViewPop();
  $("#title").textContent = DV() ? "Dashboard" : "Task Board";
  if (D) document.title = `${D.release} ${DV() ? "Dashboard" : "Task Board"}`;
  document.querySelectorAll("[data-status]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.status === "all" ? !state.status.length : state.status.includes(b.dataset.status)));
  const q = $("#q"); if (document.activeElement !== q) q.value = state.q;
  const so = sortOf(), sel = $("#sort");
  if (sel.dataset.view !== state.view) { sel.innerHTML = SORTS[state.view].opts.map(([k, l]) => `<option value="${k}">${l}</option>`).join(""); sel.dataset.view = state.view; }
  sel.value = so.key;
  const dt = state.view === "sprints" ? (so.dir < 0 ? "Newest sprint first" : "Oldest sprint first") : (so.dir < 0 ? "Descending" : "Ascending");
  const db = $("#sortdir"); db.dataset.tip = dt; db.setAttribute("aria-label", dt);
  db.querySelector("use").setAttribute("href", so.dir < 0 ? "#ic-sort-desc" : "#ic-sort-asc");
  $("#q-clear").hidden = !state.q;
  const isQ = state.view === "queue";
  const fsel = DV() ? [...state.gfilter, ...state.kfilter, ...state.tfilter.map((t) => "t:" + t)] : isQ ? state.qstatus : state.status, fb = $("#filter-btn");
  $("#tdone").hidden = isQ || DV();
  $("#qmode").hidden = !isQ && !DV() && state.view !== "sprints";
  document.querySelectorAll("#qmode [data-qmode]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.qmode === (DV() ? state.dmode : state.view === "sprints" ? state.smode : state.qmode)));
  if (D) $("#rel").textContent = DV() && DD?.release ? DD.release : D.release;
  const qo = $("#qopen"), nOpen = QD ? QD.items.filter((x) => x.status === "to-do").length : 0;
  qo.hidden = !(isQ && QD) && !(DV() && DD);
  if (DV()) {
    const nNow = DD ? DD.rows.filter((r) => r.turn === "you").length : 0;
    qo.textContent = `${nNow} need you`;
    qo.title = DD ? `${nNow} of ${DD.rows.length} items need you` : "";
  } else {
    qo.textContent = `${nOpen} to-do`;
    qo.title = QD ? `${nOpen} of ${QD.items.length} queue items to-do` : "";
  }
  const fName = (x) => DV() ? (x.startsWith("t:") ? TURN_INFO[x.slice(2)][2] : GROUP_INFO[x]?.[0] || x) : x[0].toUpperCase() + x.slice(1);
  $("#filter-label").textContent = !fsel.length ? (DV() ? "All items" : "All statuses") : fsel.length === 1 ? fName(fsel[0]) : `${fsel.length} ${DV() ? "filters" : "statuses"}`;
  $("#filter-ic").setAttribute("class", "i" + (DV() ? (fsel.length === 1 && GROUP_INFO[fsel[0]] ? " " + GROUP_INFO[fsel[0]][2] : "") : fsel.length === 1 ? " c-" + skOf(fsel[0]) : ""));
  $("#filter-ic use").setAttribute("href", DV() ? (fsel.length === 1 && GROUP_INFO[fsel[0]] ? "#ic-" + GROUP_INFO[fsel[0]][1] : "#ic-filter") : fsel.length === 1 ? "#ic-" + siconOf(fsel[0]) : "#ic-filter");
  fb.setAttribute("aria-pressed", fsel.length > 0);
  if (!$("#filter-pop").hidden) renderFilterPop();
  const lanesView = LANE_VIEWS.has(state.view);
  $("#vm-wrap").hidden = !lanesView && !DV() && !boardOn();
  if (!lanesView && !DV() && !boardOn() && !$("#vm").hidden) openVm(false);
  if (!$("#vm").hidden) renderVm();
  $("#legend-wrap").hidden = !lanesView && !DV();
  $("#lg-lanes").hidden = DV();
  $("#lg-kinds").hidden = !DV();
  if (!lanesView && !DV()) { $("#legend").hidden = true; $("#legend-btn").setAttribute("aria-pressed", "false"); }
  // Epics and Milestones have expand-all in the board's top-left cell; the Sprints view uses this one.
  const fold = $("#fold");
  fold.hidden = state.view !== "sprints";
  const any = D ? D.sprints.some((s) => !spCollapsed(s)) : false;
  const t = any ? "Collapse all sprints" : "Expand all sprints";
  fold.dataset.tip = t; fold.setAttribute("aria-label", t);
  fold.querySelector("use").setAttribute("href", any ? "#ic-fold-all" : "#ic-unfold-all");
  const root = document.documentElement;
  const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  $("#theme-ic use").setAttribute("href", dark ? "#ic-sun" : "#ic-moon");
  if (D) fitUpdated();
}
// One-shot motion hints for the next render: set by a click, read while drawing, then cleared.
let fx = {};
const motion = () => !matchMedia("(prefers-reduced-motion: reduce)").matches;
const fxClass = (el, cls, ms = 400) => { if (!el || !motion()) return; el.classList.remove(cls); void el.offsetWidth; el.classList.add(cls); setTimeout(() => el.classList.remove(cls), ms); };
// Every render keeps the scroll of the board and of each scrolling column, unless asked to start fresh.
function render(fresh, animate) {
  if (!D) return;
  prepFilter();
  syncControls();
  const keep = { board: [board.scrollLeft, board.scrollTop] };
  board.querySelectorAll("[data-sk]").forEach((el) => (keep[el.dataset.sk] = [el.scrollLeft, el.scrollTop]));
  const pTop = panel.scrollTop;
  board.dataset.view = state.view;
  board.classList.toggle("compact", state.compact);
  layoutWatch.disconnect();
  board.innerHTML = RENDER[state.view]();
  navPaint();
  renderPanel(pTop);
  if (LANE_VIEWS.has(state.view)) { drawArrows(); const g = board.querySelector(".sl"); if (g) layoutWatch.observe(g); }
  if (fx.view) fxClass(board, "fx-view");
  else if (fx.filter) fxClass(board, "fx-fade");
  fx = {};
  if (fresh) toLatest(animate);
  else {
    board.scrollTo(keep.board[0], keep.board[1]);
    board.querySelectorAll("[data-sk]").forEach((el) => { const k = keep[el.dataset.sk]; if (k) el.scrollTo(k[0], k[1]); });
  }
  save();
}
// Newest work: bottom right in the swimlanes, the top of the Sprints list and of the task columns.
function select(pick) {
  state.sel = state.sel === pick ? null : pick;
  if (pick && navEl(pick)) navCurs[state.view] = pick;
  // Swimlanes dim and highlight the dependency chain of the selected card, so they draw again.
  if (LANE_VIEWS.has(state.view)) { render(); panel.scrollTop = 0; return; }
  board.querySelectorAll(".sel").forEach((el) => el.classList.remove("sel"));
  if (state.sel) board.querySelectorAll(`[data-pick="${CSS.escape(state.sel)}"]`).forEach((el) => el.classList.add("sel"));
  renderPanel(0);
}

// ---- Events ----
document.addEventListener("click", (e) => {
  if (!e.target.closest("#legend-wrap")) { $("#legend").hidden = true; $("#legend-btn").setAttribute("aria-pressed", "false"); }
  // A row of the filter menu is drawn again on click, so its target may be gone from the page by now.
  if (e.target.isConnected && !e.target.closest("#filter-wrap") && !$("#filter-pop").hidden) openFilter(false);
  if (e.target.isConnected && !$("#view-pop").hidden && (!e.target.closest("#view-wrap") || e.target.closest("#view-pop [data-view]"))) setTimeout(() => openView(false));
  if (e.target.isConnected && !e.target.closest("#vm-wrap") && !$("#vm").hidden) openVm(false);
  document.body.classList.toggle("popover-open", !$("#legend").hidden || !$("#filter-pop").hidden || !$("#vm").hidden);
  if (e.target.closest("a[href]")) return;
  const t = e.target.closest("[data-tog],[data-pick],[data-more],[data-view],[data-status],[data-close],[data-lane],[data-all],[data-sp],[data-fold]");
  if (!t) return;
  if (t.dataset.view) { if (state.view !== t.dataset.view) { state.view = t.dataset.view; fx.view = true; render(true, true); } return; }
  if (t.dataset.status) {
    const s = t.dataset.status;
    if (s === "all") state.status = [];
    else state.status = state.status.includes(s) ? state.status.filter((x) => x !== s) : [...state.status, s];
    if (state.status.length === STATUSES.length) state.status = [];
    render(true); return;
  }
  if (t.dataset.tog) {
    fx.tog = t.dataset.tog.slice(t.dataset.tog.indexOf(":") + 1);
    const i = t.dataset.tog.indexOf(":"), set = state.open[t.dataset.tog.slice(0, i)], id = t.dataset.tog.slice(i + 1);
    if (t.classList.contains("open")) set.delete(id); else set.add(id);
    render(); return;
  }
  if (t.dataset.fold) { const id = t.dataset.fold; fx.sprint = id; foldSt.toggled.has(id) ? foldSt.toggled.delete(id) : foldSt.toggled.add(id); saveFold(); render(); return; }
  if (t.dataset.sp) { const s = state.open.sp, id = t.dataset.sp; s.has(id) ? s.delete(id) : s.add(id); render(); return; }
  if (t.dataset.lane) {
    fx.lane = t.dataset.lane;
    const set = state.view === "epics" ? state.open.le : state.open.lm, id = t.dataset.lane;
    set.has(id) ? set.delete(id) : set.add(id);
    render(); return;
  }
  if ("all" in t.dataset) { setAllCollapsed(D.epics.some((x) => !isCollapsed(x.id))); render(); return; }
  if (t.dataset.more) { state.more = [...new Set([...state.more, t.dataset.more])]; render(); return; }
  if ("close" in t.dataset) { select(state.sel); return; }
  if (t.dataset.pick) {
    // A pick from inside the side panel always opens its target; on the board a second click closes it.
    if (panel.contains(t) && state.sel === t.dataset.pick) return;
    const fromPanel = panel.contains(t);
    select(t.dataset.pick);
    // A jump from the side panel brings its target into view and rings it once.
    if (fromPanel && state.sel) {
      const id = state.sel.slice(state.sel.indexOf(":") + 1);
      const el = board.querySelector(state.sel.startsWith("ms:") ? `.card[data-id="${CSS.escape(id)}"]` : `[data-pick="${CSS.escape(state.sel)}"]`)
        || board.querySelector(`[data-pick="${CSS.escape(state.sel)}"]`);
      if (el) { el.scrollIntoView({ behavior: motion() ? "smooth" : "auto", block: "nearest", inline: "center" }); fxClass(el, "flash", 600); }
    }
  }
});
// Swimlane toggles, as in swimlanes.html.
// View menu (Epics and Milestones): the swimlanes.html toggles, sprint folding, lanes and size in one popover.
function openVm(open) {
  $("#vm").hidden = !open;
  $("#vm-btn").setAttribute("aria-expanded", open);
  document.body.classList.toggle("popover-open", open || !$("#legend").hidden || !$("#filter-pop").hidden);
  if (open) { renderVm(); $("#vm .frow").focus(); }
}
$("#vm-btn").addEventListener("click", () => openVm($("#vm").hidden));
$("#vm").addEventListener("click", (e) => {
  const r = e.target.closest("button[data-vm]");
  if (r && (DV() || boardOn())) {
    const k = r.dataset.vm, L = LY();
    if (k.startsWith("dcol:")) { const g = k.slice(5); L.hidden = L.hidden.includes(g) ? L.hidden.filter((x) => x !== g) : [...L.hidden, g]; }
    else if (k === "dsub") L.sub = !L.sub;
    else if (k === "dreset") state[BOARD_LAYOUT[state.view]] = defSpLayout();
    else return;
    r.focus(); saveLayout(); render(); return;
  }
  if (!r || !VM_ACTIONS[r.dataset.vm]) return;
  r.focus();
  VM_ACTIONS[r.dataset.vm]();
  render();
});
$("#vm").addEventListener("input", (e) => {
  if (e.target.id !== "vm-zoom") return;
  state.zoom = +e.target.value;
  e.target.nextElementSibling.textContent = state.zoom + "%";
  const host = board.querySelector(".slhost");
  if (host) host.style.zoom = state.zoom / 100;
  save();
});
$("#vm").addEventListener("keydown", (e) => {
  const rows = [...$("#vm").querySelectorAll(".frow, #vm-zoom")], i = rows.indexOf(document.activeElement);
  const range = document.activeElement?.id === "vm-zoom" && (e.key === "ArrowLeft" || e.key === "ArrowRight");
  if (!range && (e.key === "ArrowDown" || e.key === "ArrowUp")) { e.preventDefault(); rows[(i + (e.key === "ArrowDown" ? 1 : rows.length - 1)) % rows.length].focus(); }
  if (e.key === "Escape") { e.stopPropagation(); openVm(false); $("#vm-btn").focus(); }
});
// Status filter menu: "All statuses" plus the five statuses, multi-select, task counts from the whole release.
// In the Queue view the same menu lists the queue statuses and counts queue items.
const fKey = () => DV() ? "gfilter" : state.view === "queue" ? "qstatus" : "status";
const fList = () => DV() ? GROUPS : state.view === "queue" ? QSTATUSES : STATUSES;
function renderFilterPop() {
  const pop = $("#filter-pop"), focused = document.activeElement?.dataset?.fs;
  if (DV()) {
    const rows = DD ? DD.rows : [];
    const row = (st, ic, name, count, on) => `<button class="frow" role="menuitemcheckbox" aria-checked="${on}" data-fs="${esc(st)}" tabindex="-1"><span class="cbx">${on ? icon("check") : ""}</span>${ic}<span>${esc(name)}</span><span class="n">${count}</span></button>`;
    const head = (t) => `<div class="fsep"></div><div class="fhead">${t}</div>`;
    pop.innerHTML = row("all", icon("filter", "c-ns"), "All items", rows.length, !state.gfilter.length && !state.kfilter.length && !state.tfilter.length)
      + head("Status") + GROUPS.map((g) => row(g, icon(GROUP_INFO[g][1], GROUP_INFO[g][2]), GROUP_INFO[g][0], rows.filter((r) => r.status === g).length, state.gfilter.includes(g))).join("")
      + head("Kind") + KINDS.map((k) => row("k:" + k, `<span class="kchip k-${k}" style="width:10px;padding:0;margin:0;min-height:10px;line-height:10px"></span>`, k, rows.filter((r) => r.kind === k).length, state.kfilter.includes(k))).join("")
      + head("Turn") + TURNS.map((t) => row("t:" + t, `<span class="d-turn t-${t}">${icon(TURN_INFO[t][1])}</span>`, TURN_INFO[t][2], rows.filter((r) => r.turn === t).length, state.tfilter.includes(t))).join("");
    if (focused) pop.querySelector(`[data-fs="${CSS.escape(focused)}"]`)?.focus();
    return;
  }
  const items = state.view === "queue" ? (QD ? QD.items : []) : D ? D.tasks : [], sel = state[fKey()];
  const n = (st) => items.filter((t) => t.status === st).length;
  const row = (st, ic, name, count, on) => `<button class="frow" role="menuitemcheckbox" aria-checked="${on}" data-fs="${esc(st)}" tabindex="-1"><span class="cbx">${on ? icon("check") : ""}</span>${ic}<span>${esc(name)}</span><span class="n">${count}</span></button>`;
  pop.innerHTML = row("all", icon("filter", "c-ns"), "All statuses", items.length, !sel.length) + `<div class="fsep"></div>`
    + fList().map((st) => row(st, sicon(st), st[0].toUpperCase() + st.slice(1), n(st), sel.includes(st))).join("");
  if (focused) pop.querySelector(`[data-fs="${CSS.escape(focused)}"]`)?.focus();
}
function renderViewPop() {
  $("#view-pop").innerHTML = VIEWS.map((v, i) => `<button class="frow" role="menuitemradio" aria-checked="${v === state.view}" data-view="${v}" tabindex="-1">${icon(VIEW_INFO[v][1])}<span>${VIEW_INFO[v][0]}</span><span class="n"><kbd>${i + 1}</kbd></span></button>`).join("");
}
function openView(open) {
  $("#view-pop").hidden = !open;
  $("#view-btn").setAttribute("aria-expanded", open);
  if (open) { renderViewPop(); ($("#view-pop [aria-checked=true]") || $("#view-pop .frow")).focus(); }
}
$("#view-btn").addEventListener("click", () => openView($("#view-pop").hidden));
$("#view-pop").addEventListener("keydown", (e) => {
  const rows = [...$("#view-pop").querySelectorAll(".frow")], i = rows.indexOf(document.activeElement);
  if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); e.stopPropagation(); rows[(i + (e.key === "ArrowDown" ? 1 : rows.length - 1)) % rows.length].focus(); }
  if (e.key === "Escape") { e.stopPropagation(); openView(false); $("#view-btn").focus(); }
});
function openFilter(open) {
  $("#filter-pop").hidden = !open;
  $("#filter-btn").setAttribute("aria-expanded", open);
  document.body.classList.toggle("popover-open", open || !$("#legend").hidden);
  if (open) { renderFilterPop(); $("#filter-pop .frow").focus(); }
}
$("#filter-btn").addEventListener("click", () => openFilter($("#filter-pop").hidden));
$("#filter-pop").addEventListener("click", (e) => {
  const r = e.target.closest("[data-fs]");
  if (!r) return;
  const st = r.dataset.fs, k = fKey();
  r.focus();
  if (st.startsWith("t:")) { const td = st.slice(2); state.tfilter = state.tfilter.includes(td) ? state.tfilter.filter((x) => x !== td) : [...state.tfilter, td]; if (state.tfilter.length === TURNS.length) state.tfilter = []; }
  else if (st.startsWith("k:")) { const kd = st.slice(2); state.kfilter = state.kfilter.includes(kd) ? state.kfilter.filter((x) => x !== kd) : [...state.kfilter, kd]; if (state.kfilter.length === KINDS.length) state.kfilter = []; }
  else if (st === "all") { state[k] = []; if (DV()) { state.kfilter = []; state.tfilter = []; } }
  else state[k] = state[k].includes(st) ? state[k].filter((x) => x !== st) : [...state[k], st];
  if (state[k].length === fList().length) state[k] = [];
  fx.filter = true;
  render(true);
});
$("#filter-pop").addEventListener("keydown", (e) => {
  const rows = [...$("#filter-pop").querySelectorAll(".frow")], i = rows.indexOf(document.activeElement);
  if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); rows[(i + (e.key === "ArrowDown" ? 1 : rows.length - 1)) % rows.length].focus(); }
  if (e.key === "Home") { e.preventDefault(); rows[0].focus(); }
  if (e.key === "End") { e.preventDefault(); rows[rows.length - 1].focus(); }
  if (e.key === "Escape") { e.stopPropagation(); openFilter(false); $("#filter-btn").focus(); }
});
function closePopovers() {
  if (!$("#filter-pop").hidden) openFilter(false);
  if (!$("#vm").hidden) openVm(false);
  $("#legend").hidden = true;
  $("#legend-btn").setAttribute("aria-pressed", "false");
  document.body.classList.remove("popover-open");
}
$("#legend-btn").addEventListener("click", () => {
  const open = $("#legend").hidden;
  $("#legend").hidden = !open;
  $("#legend-btn").setAttribute("aria-pressed", open);
  document.body.classList.toggle("popover-open", open);
});
$("#sort").addEventListener("change", (e) => { state.sorts[state.view] = { ...sortOf(), key: e.target.value }; render(); });
$("#qmode").addEventListener("click", (e) => {
  const b = e.target.closest("[data-qmode]");
  const k = DV() ? "dmode" : state.view === "sprints" ? "smode" : "qmode";
  if (!b || b.dataset.qmode === state[k]) return;
  state[k] = b.dataset.qmode; fx.filter = true; render(true);
});
$("#sortdir").addEventListener("click", () => { const so = sortOf(); state.sorts[state.view] = { ...so, dir: -so.dir }; render(); });
$("#fold").addEventListener("click", () => {
  const any = D.sprints.some((s) => !spCollapsed(s));
  // Store only sprints toggled away from their default (finished ones start collapsed).
  state.open.sp = new Set(D.sprints.filter((s) => any ? s.status !== "done" : s.status === "done").map((s) => s.id));
  render();
});
let qTimer = 0;
$("#q").addEventListener("input", (e) => {
  clearTimeout(qTimer);
  qTimer = setTimeout(() => { state.q = e.target.value.trim(); fx.filter = true; render(true); }, 120);
});
$("#q-clear").addEventListener("click", (e) => { e.preventDefault(); $("#q").value = ""; state.q = ""; render(true); });
document.addEventListener("keydown", (e) => {
  if (e.target.matches("input")) {
    if (e.key === "Escape") { if (e.target.value) { e.target.value = ""; state.q = ""; render(true); } else e.target.blur(); }
    return;
  }
  // An open menu owns the keys: Escape closes only the menu, and the cursor behind it does not move.
  const menu = menuOpen();
  if (e.key === "Escape") { if (menu) { closePopovers(); openView(false); } else if (state.sel) select(state.sel); else navClear(); }
  if (e.key === "/" && !e.metaKey && !e.ctrlKey) { e.preventDefault(); $("#q").focus(); }
  const n = "123456".indexOf(e.key);
  if (n >= 0 && !e.metaKey && !e.ctrlKey && !e.altKey && state.view !== VIEWS[n]) { state.view = VIEWS[n]; fx.view = true; render(true, true); }
  if (!menu && navCols().length && !e.metaKey && !e.ctrlKey && !e.altKey && !e.target.closest("select, input")) {
    if (e.key === "j" || e.key === "ArrowDown") { e.preventDefault(); navStep(1); }
    else if (e.key === "k" || e.key === "ArrowUp") { e.preventDefault(); navStep(-1); }
    else if (e.key === "h" || e.key === "ArrowLeft") { e.preventDefault(); navStep(0, -1); }
    else if (e.key === "l" || e.key === "ArrowRight") { e.preventDefault(); navStep(0, 1); }
    else if (e.key === "Enter" && navEl() && !e.target.closest("button, a, [data-lfold]")) { e.preventDefault(); if (state.sel !== navCurs[state.view]) select(navCurs[state.view]); }
  }
});
$("#theme").addEventListener("click", () => {
  const root = document.documentElement;
  const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  root.dataset.theme = dark ? "light" : "dark";
  try { localStorage.setItem("taskboard-theme", root.dataset.theme); } catch (e) {}
  syncControls();
});
$("#reload").addEventListener("click", () => { loadScript(true); loadDashScript(true); });

// The reload button and the 30 second timer share this path. Unchanged data is not drawn again;
// changed data keeps the view, the filters, the open rows, the selection and the scroll position.
let dataText = null;
function loadScript(bust) {
  const s = document.createElement("script");
  s.src = DATA_DIR + "status.data.js" + (bust ? `?t=${Date.now()}` : "");
  s.onload = () => {
    s.remove();
    const text = JSON.stringify(window.STATUS_DATA);
    if (D) showUpdated();
    if (text === dataText) return;
    const first = dataText === null;
    dataText = text;
    const prev = D ? new Map([...D.milestones, ...D.tasks].map((x) => [x.id, x.status])) : null;
    load(window.STATUS_DATA);
    render(first, first);
    if (!first) fxClass($("#upd"), "fresh", 900);
    // Items whose status changed in this reload ring once.
    if (prev) [...D.milestones.map((x) => ["ms", x]), ...D.tasks.map((x) => ["task", x])].forEach(([k, x]) => {
      if (prev.has(x.id) && prev.get(x.id) !== x.status) board.querySelectorAll(`[data-pick="${k}:${CSS.escape(x.id)}"]`).forEach((el) => fxClass(el, "pulse", 700));
    });
  };
  s.onerror = () => { s.remove(); if (!D) board.innerHTML = `<div class="empty">status.data.js not found next to this page.</div>`; };
  document.head.appendChild(s);
}
// dashboard.data.js is optional: without it the Dashboard and the Queue view show an empty state.
let dashText = null;
function loadDashScript(bust) {
  const s = document.createElement("script");
  s.src = DATA_DIR + "dashboard.data.js" + (bust ? `?t=${Date.now()}` : "");
  s.onload = () => {
    s.remove();
    const text = JSON.stringify(window.DASHBOARD_DATA ?? null);
    if (text === dashText) return;
    const first = dashText === null;
    dashText = text;
    loadDash(window.DASHBOARD_DATA);
    if (!D) return;
    render();
    if (!first && (DV() || state.view === "queue")) fxClass($("#upd"), "fresh", 900);
  };
  s.onerror = () => { s.remove(); if (dashText === null && D) render(); };
  document.head.appendChild(s);
}
// Starts after parts.js and views.js have loaded (scripts at the end of <body> run before DOMContentLoaded).
addEventListener("DOMContentLoaded", () => {
  syncControls();
  loadDashScript(false);
  loadScript(false);
  setInterval(() => { if (!document.hidden) { loadScript(true); loadDashScript(true); } }, 30000);
});
