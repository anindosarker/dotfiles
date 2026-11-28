// Icons (Lucide, ISC licence), one sprite for the whole page.
document.body.insertAdjacentHTML("afterbegin", `<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <symbol id="ic-columns" viewBox="0 0 24 24"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/><path d="M15 3v18"/></symbol>
  <symbol id="ic-lanes" viewBox="0 0 24 24"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M21 9H3"/><path d="M21 15H3"/></symbol>
  <symbol id="ic-list" viewBox="0 0 24 24"><path d="M3 12h.01"/><path d="M3 18h.01"/><path d="M3 6h.01"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M8 6h13"/></symbol>
  <symbol id="ic-flag" viewBox="0 0 24 24"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/></symbol>
  <symbol id="ic-sort" viewBox="0 0 24 24"><path d="m21 16-4 4-4-4"/><path d="M17 20V4"/><path d="m3 8 4-4 4 4"/><path d="M7 4v16"/></symbol>
  <symbol id="ic-sort-asc" viewBox="0 0 24 24"><path d="m3 8 4-4 4 4"/><path d="M7 4v16"/><path d="M11 12h4"/><path d="M11 16h7"/><path d="M11 20h10"/></symbol>
  <symbol id="ic-sort-desc" viewBox="0 0 24 24"><path d="m3 16 4 4 4-4"/><path d="M7 20V4"/><path d="M11 4h10"/><path d="M11 8h7"/><path d="M11 12h4"/></symbol>
  <symbol id="ic-fold" viewBox="0 0 24 24"><path d="M12 22v-6"/><path d="M12 8V2"/><path d="M4 12H2"/><path d="M10 12H8"/><path d="M16 12h-2"/><path d="M22 12h-2"/><path d="m15 19-3-3-3 3"/><path d="m15 5-3 3-3-3"/></symbol>
  <symbol id="ic-info" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></symbol>
  <symbol id="ic-fold-h" viewBox="0 0 24 24"><path d="M2 12h6"/><path d="M22 12h-6"/><path d="M12 2v2"/><path d="M12 8v2"/><path d="M12 14v2"/><path d="M12 20v2"/><path d="m19 9-3 3 3 3"/><path d="m5 15 3-3-3-3"/></symbol>
  <symbol id="ic-filter" viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M7 12h10"/><path d="M10 18h4"/></symbol>
  <symbol id="ic-check" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></symbol>
  <symbol id="ic-sliders" viewBox="0 0 24 24"><line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/></symbol>
  <symbol id="ic-kanban" viewBox="0 0 24 24"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M8 7v7"/><path d="M12 7v4"/><path d="M16 7v9"/></symbol>
  <symbol id="ic-check-circle" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></symbol>
  <symbol id="ic-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></symbol>
  <symbol id="ic-circle" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></symbol>
  <symbol id="ic-stop" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></symbol>
  <symbol id="ic-ban" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/></symbol>
  <symbol id="ic-eye" viewBox="0 0 24 24"><path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/></symbol>
  <symbol id="ic-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></symbol>
  <symbol id="ic-refresh" viewBox="0 0 24 24"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></symbol>
  <symbol id="ic-sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></symbol>
  <symbol id="ic-moon" viewBox="0 0 24 24"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></symbol>
  <symbol id="ic-x" viewBox="0 0 24 24"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></symbol>
  <symbol id="ic-chevron" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></symbol>
  <symbol id="ic-fold-all" viewBox="0 0 24 24"><path d="m7 20 5-5 5 5"/><path d="m7 4 5 5 5-5"/></symbol>
  <symbol id="ic-unfold-all" viewBox="0 0 24 24"><path d="m7 15 5 5 5-5"/><path d="m7 9 5-5 5 5"/></symbol>
  <symbol id="ic-user" viewBox="0 0 24 24"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></symbol>
  <symbol id="ic-compass" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="m16.24 7.76-1.8 5.4a2 2 0 0 1-1.28 1.28l-5.4 1.8 1.8-5.4a2 2 0 0 1 1.28-1.28z"/></symbol>
  <symbol id="ic-bot" viewBox="0 0 24 24"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></symbol>
  <symbol id="ic-gauge" viewBox="0 0 24 24"><path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/></symbol>
  <symbol id="ic-inbox" viewBox="0 0 24 24"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></symbol>
  <symbol id="ic-circle-dot" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="1"/></symbol>
  <symbol id="ic-wrench" viewBox="0 0 24 24"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></symbol>
</svg>`);
const icon = (id, cls = "") => `<svg class="i ${cls}"><use href="#ic-${id}"/></svg>`;
// Item id chip in its kind's color (legend: Kinds); sprints and specs get a neutral chip.
const KC = { epic: "epic", ms: "milestone", milestone: "milestone", task: "task", q: "queue", queue: "queue", decision: "decision" };
const kc = (kind, text) => `<span class="kchip k-${KC[kind] || "plain"}" title="${esc(KC[kind] || kind)}">${esc(text)}</span>`;
const sicon = (st) => icon(siconOf(st) || "circle", "c-" + (skOf(st) || "ns"));
const pill = (st) => `<span class="pill s-${skOf(st) || "ns"}">${icon(siconOf(st) || "circle")}${esc(st)}</span>`;
function progress(c, frac = true) {
  const pct = (n) => c.total ? (n / c.total * 100).toFixed(2) + "%" : "0";
  const bar = `<span class="pbar" title="${c.done} done, ${c.archived} archived, ${c["in progress"]} in progress, ${c.blocked} blocked, ${c["to-do"]} to-do">`
    + `<i class="b-done" style="width:${pct(c.done)}"></i><i class="b-skip" style="width:${pct(c.archived)}"></i>`
    + `<i class="b-prog" style="width:${pct(c["in progress"])}"></i><i class="b-block" style="width:${pct(c.blocked)}"></i></span>`;
  return `<span class="pgw">${bar}${frac ? `<span class="frac">${doneOf(c)}</span>` : ""}</span>`;
}
// ---- Folded sprint columns in the swimlanes, saved per release ----
// Finished sprints fold by default; a header click toggles one sprint away from that.
// mode: which sprints fold by rule ("none", "finished", "before" the current sprint, "all"); empty adds sprints with no card.
let foldSt = { mode: "finished", empty: false, toggled: new Set() }, foldRelease = null;
const FOLD_MODES = ["none", "finished", "before", "all"];
function loadFold() {
  foldRelease = D.release;
  foldSt = { mode: "finished", empty: false, toggled: new Set() };
  try {
    const f = JSON.parse(localStorage.getItem("taskboard-fold") || "{}")[D.release];
    if (f) foldSt = { mode: FOLD_MODES.includes(f.mode) ? f.mode : f.finished === false ? "none" : "finished", empty: !!f.empty, toggled: new Set(f.toggled || []) };
  } catch (e) {}
}
function saveFold() { try {
  const all = JSON.parse(localStorage.getItem("taskboard-fold") || "{}");
  all[D.release] = { mode: foldSt.mode, empty: foldSt.empty, toggled: [...foldSt.toggled] };
  localStorage.setItem("taskboard-fold", JSON.stringify(all));
} catch (e) {} }
const spFinished = (s) => s.status === "done" || s.status === "archived";
// Empty: no milestone in this sprint passes the current filter.
const spEmpty = (s) => !kids.get(s).some((m) => pass(m, "ms"));
function foldRule(s) {
  if (foldSt.mode === "all") return true;
  if (foldSt.mode === "finished") return spFinished(s);
  if (foldSt.mode === "before") { const now = nowSprint(); return now >= 0 && sprintPos.get(s.id) < now; }
  return false;
}
const foldBase = (s) => foldRule(s) || (foldSt.empty && spEmpty(s));
const isFolded = (s) => foldBase(s) !== foldSt.toggled.has(s.id);

// ---- Shared board: every kanban board (Dashboard, Tasks, Sprints, Queue) moves, resizes and hides columns, one saved layout per view ----
const BOARD_LAYOUT = { dash: "dlayout", sprints: "splayout", queue: "qlayout", tasks: "tlayout" };
const capWord = (w) => w[0].toUpperCase() + w.slice(1);
const BOARD_BASE = { dash: () => GROUPS, queue: () => QSTATUSES, tasks: () => STATUSES, sprints: () => spBase().map((sp) => sp.id) };
const BOARD_NAME = { dash: (g) => GROUP_INFO[g][0], queue: capWord, tasks: capWord, sprints: (g) => g };
const boardOn = () => DV() || state.view === "tasks" || (state.view === "sprints" && state.smode === "board") || (state.view === "queue" && state.qmode === "board");
const LY = () => state[BOARD_LAYOUT[state.view]] || state.dlayout;
// All column ids of the current board in layout order, hidden ones included.
function layoutIds() {
  const base = BOARD_BASE[state.view] ? BOARD_BASE[state.view]() : [], o = LY().order;
  if (!o.length) return base;
  const at = (id) => { const i = o.indexOf(id); return i < 0 ? o.length + base.indexOf(id) : i; };
  return base.slice().sort((a, b) => at(a) - at(b));
}
const shownIds = () => layoutIds().filter((id) => !LY().hidden.includes(id));
// cols: [{ id, head, body, cls?, headCls? }] in display order.
function boardHtml(cols) {
  const L = LY();
  return `<div class="kb qkb dkb${L.sub ? "" : " nosub"}">${cols.map((c) => { const w = L.widths[c.id];
    return `<section class="kb-col${c.cls || ""}" data-dcol="${esc(c.id)}"${w ? ` style="flex:0 0 ${w}px"` : ""}><div class="kb-head${c.headCls ? " " + c.headCls : ""}" draggable="true" data-dhead="${esc(c.id)}" title="Drag to move the column">${c.head}</div>
    <span class="dcol-rs" data-drs="${esc(c.id)}" title="Drag to resize; double-click to reset" aria-hidden="true"></span>
    <div class="kb-list" data-sk="kb-${esc(state.view)}-${esc(c.id)}">${c.body || `<div class="empty" style="padding:16px">Nothing here</div>`}</div></section>`; }).join("")}</div>`;
}
// ---- Shared list sections: every grouped list folds per group, state saved per view ----
const foldedIn = (view = state.view) => state.lfold[view] || [];
// groups: [{ id, head, rows }] with rows already drawn; foot: html after the sections.
function listSections(groups, foot = "") {
  return `<div class="dsecs">${groups.map((g) => { const folded = foldedIn().includes(g.id);
    return `<section class="qsec dsec${folded ? " folded" : ""}"><div class="qgrp dhead" data-lfold="${esc(g.id)}" role="button" tabindex="0" aria-expanded="${!folded}" title="Click to ${folded ? "unfold" : "fold"}">
      <span class="tog${folded ? "" : " open"}">${icon("chevron")}</span>${g.head}</div>${folded ? "" : g.rows}</section>`; }).join("")}${foot}</div>`;
}
const listFoot = (extra = "") => `<div class="qfoot"><kbd>j</kbd> <kbd>k</kbd> move · <kbd>Enter</kbd> open · <kbd>Esc</kbd> close · <kbd>/</kbd> search${extra}</div>`;
// Keys on boards and lists, one cursor per view: j/k move in a column (a list is one column), h/l move between board columns.
const navCurs = {};
const menuOpen = () => ["#filter-pop", "#view-pop", "#vm", "#legend"].some((s) => !$(s).hidden);
function navCols() {
  if (board.querySelector(".dkb")) return [...board.querySelectorAll(".dkb .kb-col")].map((c) => [...c.querySelectorAll(".kb-list > [data-pick]")]).filter((l) => l.length);
  const rows = [...board.querySelectorAll(".dsecs .qr[data-pick], .spl .mr[data-pick]")];
  return rows.length ? [rows] : [];
}
const navEl = (pick = navCurs[state.view]) => navCols().flat().find((el) => el.dataset.pick === pick);
function navPaint() {
  board.querySelectorAll("[data-pick].cur").forEach((x) => x.classList.remove("cur"));
  navEl()?.classList.add("cur");
}
function navStep(n, col = 0) {
  const cols = navCols(), isBoard = !!board.querySelector(".dkb"), cur = navCurs[state.view];
  if (!cols.length || (col && !isBoard)) return;
  let ci = cols.findIndex((l) => l.some((el) => el.dataset.pick === cur)), ri = ci < 0 ? -1 : cols[ci].findIndex((el) => el.dataset.pick === cur);
  if (ci < 0) { ci = 0; ri = isBoard || n >= 0 ? 0 : cols[0].length - 1; }
  else if (col) { ci = Math.max(0, Math.min(cols.length - 1, ci + col)); ri = Math.min(ri, cols[ci].length - 1); }
  else ri = Math.max(0, Math.min(cols[ci].length - 1, ri + n));
  const el = cols[ci][ri];
  navCurs[state.view] = el.dataset.pick;
  navPaint();
  el.scrollIntoView({ block: "nearest", inline: "nearest" });
  if (state.sel && state.sel !== el.dataset.pick) select(el.dataset.pick);
}
function navClear() { navCurs[state.view] = null; navPaint(); }
function saveLayout() { for (const k of Object.values(BOARD_LAYOUT)) state[k] = cleanSpLayout(state[k]); save(); }
// Board columns: drag a header to move the column, drag the right edge to resize it, double-click the edge to reset.
let dragCol = null;
board.addEventListener("dragstart", (e) => {
  const h = e.target.closest?.("[data-dhead]"); if (!h) return;
  dragCol = h.dataset.dhead; e.dataTransfer.effectAllowed = "move";
  try { e.dataTransfer.setData("text/plain", dragCol); } catch (err) {}
  h.closest(".kb-col").classList.add("dragging");
});
board.addEventListener("dragend", () => { dragCol = null; board.querySelectorAll(".kb-col.dragging, .kb-col.drop-l, .kb-col.drop-r").forEach((c) => c.classList.remove("dragging", "drop-l", "drop-r")); });
const dropSide = (col, e) => { const r = col.getBoundingClientRect(); return e.clientX < r.left + r.width / 2 ? "l" : "r"; };
board.addEventListener("dragover", (e) => {
  if (!dragCol) return;
  const col = e.target.closest?.("[data-dcol]"); if (!col) return;
  e.preventDefault();
  board.querySelectorAll(".kb-col.drop-l, .kb-col.drop-r").forEach((c) => c.classList.remove("drop-l", "drop-r"));
  if (col.dataset.dcol !== dragCol) col.classList.add("drop-" + dropSide(col, e));
});
board.addEventListener("drop", (e) => {
  const col = e.target.closest?.("[data-dcol]"); if (!dragCol || !col) return;
  e.preventDefault();
  const to = col.dataset.dcol, from = dragCol;
  if (to !== from) {
    const order = layoutIds().filter((g) => g !== from);
    order.splice(order.indexOf(to) + (dropSide(col, e) === "r" ? 1 : 0), 0, from);
    LY().order = order; saveLayout();
  }
  dragCol = null; render();
});
board.addEventListener("pointerdown", (e) => {
  const rs = e.target.closest?.("[data-drs]"); if (!rs || e.button !== 0) return;
  e.preventDefault();
  const col = rs.closest(".kb-col"), g = rs.dataset.drs, x0 = e.clientX, w0 = col.getBoundingClientRect().width;
  rs.setPointerCapture(e.pointerId); document.body.classList.add("col-resizing");
  const move = (ev) => { col.style.flex = `0 0 ${Math.max(0, w0 + ev.clientX - x0)}px`; };
  const up = () => {
    rs.removeEventListener("pointermove", move); rs.removeEventListener("pointerup", up); rs.removeEventListener("pointercancel", up);
    document.body.classList.remove("col-resizing");
    LY().widths[g] = Math.round(col.getBoundingClientRect().width); saveLayout();
  };
  rs.addEventListener("pointermove", move); rs.addEventListener("pointerup", up); rs.addEventListener("pointercancel", up);
});
board.addEventListener("dblclick", (e) => {
  const rs = e.target.closest?.("[data-drs]"); if (!rs) return;
  delete LY().widths[rs.dataset.drs]; saveLayout(); render();
});
function toggleFold(g) {
  const f = foldedIn();
  state.lfold = { ...state.lfold, [state.view]: f.includes(g) ? f.filter((x) => x !== g) : [...f, g] };
  render();
  board.querySelector(`[data-lfold="${CSS.escape(g)}"]`)?.focus({ preventScroll: true });
}
board.addEventListener("click", (e) => { const h = e.target.closest("[data-lfold]"); if (h) toggleFold(h.dataset.lfold); });
board.addEventListener("keydown", (e) => {
  const h = e.target.closest("[data-lfold]");
  if (h && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); e.stopPropagation(); toggleFold(h.dataset.lfold); }
});
// n moves within the list or a board column; col moves between board columns.
// ---- Epics and Milestones views: swimlanes (epic lanes x sprint columns), ported from swimlanes.html ----
const LANE_VIEWS = new Set(["epics", "milestones"]);
const visible = (m) => pass(m, "ms");
const sprintOf = (m) => sprintPos.get(m.sprint) ?? -1;
// Under a filter, lanes and sprint columns with nothing that passes it are not drawn; no filter draws everything.
const shownLanes = () => D.epics.filter((e) => !active() || epicMs.get(e.id).some(visible));
function shownSprints(lanes) {
  const ids = new Set(lanes.map((e) => e.id));
  return D.sprints.map((_, i) => i).filter((i) => !active() || D.milestones.some((m) => sprintOf(m) === i && ids.has(m.epic) && visible(m)));
}
const finished = (m) => m.status === "done" || m.status === "archived";
function nowSprint() {
  const open = D.milestones.filter((m) => !finished(m)).map(sprintOf).filter((i) => i >= 0);
  return open.length ? Math.min(...open) : -1;
}
function laneInfo(e) {
  const ms = epicMs.get(e.id);
  const pos = ms.map(sprintOf).filter((i) => i >= 0);
  const span = pos.length ? [Math.min(...pos), Math.max(...pos)] : null;
  const spanTxt = span ? (span[0] === span[1] ? D.sprints[span[0]].id : `${D.sprints[span[0]].id}–${D.sprints[span[1]].id}`) : "";
  return { ms, spanTxt, done: ms.filter(finished).length };
}
// Epics view starts collapsed (stores opened lanes); Milestones view starts expanded (stores closed lanes).
const isCollapsed = (id) => state.view === "epics" ? !state.open.le.has(id) : state.open.lm.has(id);
function setAllCollapsed(c) {
  if (state.view === "epics") state.open.le = new Set(c ? [] : D.epics.map((e) => e.id));
  else state.open.lm = new Set(c ? D.epics.map((e) => e.id) : []);
}
function chain(id) {
  const out = new Set([id]);
  const walk = (k, next) => (next(k) || []).forEach((n) => { if (!out.has(n)) { out.add(n); walk(n, next); } });
  walk(id, (k) => idx.ms.get(k)?.depends);
  walk(id, (k) => dependents.get(k));
  return out;
}
const focusSet = () => state.sel && state.sel.startsWith("ms:") ? chain(state.sel.slice(3)) : null;
const tip = (m) => (idx.spec.get(m.spec)?.title || m.name) + (m.reason ? "\n" + m.reason : "");
function cardClass(m, focus, extra = "") {
  const cls = ["card", "st-" + skOf(m.status)];
  if (extra) cls.push(extra);
  if (state.sel === "ms:" + m.id) cls.push("sel");
  if (state.crit && m.critical) cls.push("crit-on");
  if ((focus && !focus.has(m.id)) || (state.crit && !focus && !m.critical)) cls.push("dim");
  return cls.join(" ");
}
function expandAllBtn() {
  const any = D.epics.some((e) => !isCollapsed(e.id));
  return `<button class="allbtn" data-all data-tip="${any ? "Collapse all" : "Expand all"}" aria-label="${any ? "Collapse all lanes" : "Expand all lanes"}">${icon(any ? "fold-all" : "unfold-all")}</button>`;
}
function headerRow(sprints, now, firstLabel) {
  // Sprint totals stay real: they count every lane, not only the lanes the filter leaves.
  let html = `<div class="hcell hlabel">${firstLabel}${expandAllBtn()}</div>`;
  sprints.forEach((i, k) => {
    const s = D.sprints[i];
    const ms = kids.get(s), done = ms.filter(finished).length;
    const pct = ms.length ? Math.round((done / ms.length) * 100) : 0;
    const last = k === sprints.length - 1 ? " lastcol" : "";
    if (isFolded(s)) {
      html += `<div class="hcell fold${last}" data-fold="${esc(s.id)}" title="${esc(s.id)} · ${esc(s.status)} · ${done}/${ms.length} done\nClick to unfold"><span class="sdot fbar st-${skOf(s.status)}"></span><span class="vid">${esc(s.id)}</span></div>`;
      return;
    }
    html += `<div class="hcell${i === now ? " now" : ""}${last}" data-fold="${esc(s.id)}" title="Click to fold">
      <div class="h1"><b>${esc(s.id)}</b>${i === now ? `<span class="nowtag">now</span>` : icon("fold-h", "fchev")}</div>
      <div class="hsub">${done}/${ms.length} done</div>
      <div class="hbar"><i class="${pct === 100 ? "full" : ""}" style="width:${pct}%"></i></div></div>`;
  });
  return html;
}
function laneLabel(e) {
  const { spanTxt, done, ms } = laneInfo(e);
  const collapsed = isCollapsed(e.id);
  return `<div class="lane${collapsed ? " collapsed" : ""}" data-lane="${esc(e.id)}" title="${esc(e.name)}\nClick to ${collapsed ? "expand" : "collapse"}">
    <span class="lbar"></span>
    <span class="ltxt"><b>${kc("epic", e.id)}</b><span>${esc(e.name)}</span><span>${spanTxt} · ${done}/${ms.length}</span></span>
    <span class="chev">${icon("chevron")}</span></div>`;
}
// Collapsed lane: one chip per sprint standing for its milestones; follows the filter like the cards.
const CHIP_ORDER = ["blocked", "in progress"];
const chipStatus = (shown) => CHIP_ORDER.find((s) => shown.some((m) => m.status === s))
  || (shown.every(finished) ? (shown.some((m) => m.status === "done") ? "done" : "archived") : "to-do");
// A folded column's cell: a count pill tinted like the collapsed-lane chips; a click unfolds the sprint.
function foldPill(cards, sid) {
  const shown = cards.filter(visible);
  return shown.length ? `<span class="fpill st-${skOf(chipStatus(shown))}" data-fold="${esc(sid)}" title="${shown.length} milestone${shown.length > 1 ? "s" : ""} in ${esc(sid)}\nClick to unfold">${shown.length}</span>` : "";
}
function laneChip(e, cards) {
  const shown = cards.filter(visible);
  if (!shown.length) return "";
  const status = chipStatus(shown);
  return `<div data-lane="${esc(e.id)}" class="card chip st-${skOf(status)}">${shown.length} milestone${shown.length > 1 ? "s" : ""}</div>`;
}
const cnt1 = (m) => `<span class="cnt" title="tasks done or archived / all tasks">${doneOf(cnt.get(m))}</span>`;
function renderEpic(lanes, sprints, now, focus) {
  const nowCls = (i, k) => (i === now ? " now" : "") + (k === sprints.length - 1 ? " lastcol" : "") + (fx.sprint === D.sprints[i].id ? " reveal" : "");
  let html = headerRow(sprints, now, "Epic");
  lanes.forEach((e) => {
    const { ms } = laneInfo(e);
    const collapsed = isCollapsed(e.id);
    html += laneLabel(e);
    sprints.forEach((i, k) => {
      const cards = ms.filter((m) => sprintOf(m) === i);
      if (isFolded(D.sprints[i])) { html += `<div class="cell fcell${nowCls(i, k)}">${foldPill(cards, D.sprints[i].id)}</div>`; return; }
      html += `<div class="cell${nowCls(i, k)}${fx.lane === e.id ? " reveal" : ""}">`;
      if (collapsed) html += laneChip(e, cards);
      else cards.filter(visible).forEach((m) => {
        html += `<div class="${cardClass(m, focus)}" data-id="${esc(m.id)}" data-pick="ms:${esc(m.id)}" title="${esc(tip(m))}">${kc("ms", label("ms", m))}<span class="mn">${esc(m.name)}</span>${cnt1(m)}${m.reason ? `<span class="reason">${icon(siconOf(m.status))}<span>${esc(m.reason)}</span></span>` : ""}</div>`;
      });
      html += `</div>`;
    });
  });
  return html;
}
function renderMilestone(lanes, sprints, now, focus) {
  const nowCls = (i, k) => (i === now ? " now" : "") + (k === sprints.length - 1 ? " lastcol" : "") + (fx.sprint === D.sprints[i].id ? " reveal" : "");
  let html = headerRow(sprints, now, "Milestone");
  lanes.forEach((e) => {
    const { ms } = laneInfo(e);
    if (isCollapsed(e.id)) {
      html += laneLabel(e);
      sprints.forEach((i, k) => {
        const cards = ms.filter((m) => sprintOf(m) === i);
        html += isFolded(D.sprints[i]) ? `<div class="mcell fcell${nowCls(i, k)}">${foldPill(cards, D.sprints[i].id)}</div>` : `<div class="mcell${nowCls(i, k)}">${laneChip(e, cards)}</div>`;
      });
      return;
    }
    // Epic group header spans the whole row.
    html += `${laneLabel(e)}<div class="lanefill"></div>`;
    const so = sortOf();
    sorted(ms, MS_KEYS[so.key], so.dir).forEach((m) => {
      if (!visible(m)) return;
      const dim = (focus && !focus.has(m.id)) || (state.crit && !focus && !m.critical);
      html += `<div data-pick="ms:${esc(m.id)}" class="mrow${dim ? " dim" : ""}${state.sel === "ms:" + m.id ? " selrow" : ""}">
        ${icon("flag", "mi")}${kc("ms", label("ms", m))}<span class="mn" title="${esc(tip(m))}">${esc(m.name)}</span></div>`;
      sprints.forEach((i, k) => {
        if (isFolded(D.sprints[i])) { html += `<div class="mcell fcell${nowCls(i, k)}">${sprintOf(m) === i ? foldPill([m], D.sprints[i].id) : ""}</div>`; return; }
        html += `<div class="mcell${nowCls(i, k)}${fx.lane === e.id ? " reveal" : ""}">`;
        if (sprintOf(m) === i) html += `<div class="${cardClass(m, focus, "mcard")}" data-id="${esc(m.id)}" data-pick="ms:${esc(m.id)}" title="${esc(m.status)}: ${esc(tip(m))}">${icon(siconOf(m.status))}${kc("ms", label("ms", m))}<span class="mn">${esc(m.name)}</span>${cnt1(m)}</div>`;
        html += `</div>`;
      });
    });
  });
  return html;
}
function renderLanes() {
  let lanes = shownLanes();
  if (state.view === "epics") { const so = sortOf(); lanes = sorted(lanes, EPIC_KEYS[so.key], so.dir); }
  if (!lanes.length) return `<div class="empty">No milestone matches the filter.</div>`;
  const sprints = shownSprints(lanes), now = nowSprint(), focus = focusSet();
  const labelW = state.view === "milestones" ? 260 : 200;
  const cols = `${labelW}px ${sprints.map((i) => isFolded(D.sprints[i]) ? "30px" : state.fill ? "minmax(150px, 1fr)" : "150px").join(" ")}`;
  const inner = state.view === "milestones" ? renderMilestone(lanes, sprints, now, focus) : renderEpic(lanes, sprints, now, focus);
  return `<div class="slhost" style="zoom:${state.zoom / 100}"><div class="sl" style="grid-template-columns:${cols}">${inner}</div><svg class="arrows"></svg></div>`;
}
function drawArrows() {
  const svg = board.querySelector("svg.arrows"), host = board.querySelector(".slhost");
  if (!svg || !host) return;
  svg.innerHTML = "";
  if (!state.arrows) return;
  svg.setAttribute("width", host.scrollWidth);
  svg.setAttribute("height", host.scrollHeight);
  // Layout offsets, not screen rects: they ignore scrolling and the cards' hover transform.
  const pos = (id) => {
    const el = host.querySelector(`.card[data-id="${CSS.escape(id)}"]`);
    // Only cards on screen: no arrows to folded strips or collapsed-lane chips.
    if (!el) return null;
    let x = 0, y = 0;
    for (let n = el; n && n !== host; n = n.offsetParent) { x += n.offsetLeft; y += n.offsetTop; }
    const w = el.offsetWidth, h = el.offsetHeight;
    return { l: x, r: x + w, y: y + h / 2, t: y, b: y + h };
  };
  const focus = focusSet();
  let out = `<defs>${["overlay0", "red", "mauve"].map((k) => `<marker id="m-${k}" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L8 4L0 8z" style="fill:var(--ctp-${k})"/></marker>`).join("")}</defs>`;
  D.milestones.forEach((m) => (m.depends || []).forEach((d) => {
    const a = pos(d), b = pos(m.id);
    if (!a || !b) return;
    const from = idx.ms.get(d);
    const hl = focus && focus.has(m.id) && focus.has(d);
    const crit = state.crit && !!(from?.critical && m.critical);
    let path;
    if (b.l > a.r + 4) {
      const dx = Math.max(20, (b.l - a.r) / 2);
      path = `M${a.r} ${a.y} C${a.r + dx} ${a.y} ${b.l - dx} ${b.y} ${b.l - 2} ${b.y}`;
    } else {
      const x = (a.l + a.r) / 2, down = b.t > a.b;
      path = `M${x} ${down ? a.b : a.t} L${x} ${down ? b.t - 2 : b.b + 2}`;
    }
    const cls = ["edge", from && from.epic !== m.epic ? "cross" : "", crit ? "crit" : "", hl ? "hl" : "", focus && !hl ? "dim" : ""].join(" ");
    out += `<path class="${cls}" d="${path}" marker-end="url(#m-${hl ? "mauve" : crit ? "red" : "overlay0"})"/>`;
  }));
  svg.innerHTML = out;
}
// Redraw the arrows when the grid changes size (late fonts, wraps, window resizes); nothing runs on scroll.
let arrowFrame = 0;
const scheduleArrows = () => { cancelAnimationFrame(arrowFrame); arrowFrame = requestAnimationFrame(drawArrows); };
const layoutWatch = new ResizeObserver(scheduleArrows);
// Swimlanes: the current sprint column with one column before it in view (the right end when the rest fits),
// and the newest epics: the bottom, or the top when the lane sort puts newest first.
function laneTarget() {
  const maxL = board.scrollWidth - board.clientWidth, maxT = board.scrollHeight - board.clientHeight;
  const now = board.querySelector(".hcell.now"), label = board.querySelector(".hcell.hlabel");
  let left = maxL;
  if (now && label) {
    const bx = board.getBoundingClientRect().left - board.scrollLeft;
    const prev = now.previousElementSibling;
    const pw = prev && prev !== label ? prev.getBoundingClientRect().width : 0;
    left = Math.min(maxL, now.getBoundingClientRect().left - bx - label.getBoundingClientRect().width - pw);
  }
  const top = state.view === "epics" && sortOf().dir < 0 ? 0 : maxT;
  return [Math.max(0, left), top];
}
// animate: first open and a switch into a view; start top-left so the move shows, after fonts and layout settle.
function toLatest(animate) {
  if (!LANE_VIEWS.has(state.view)) return board.scrollTo(0, 0);
  const go = () => {
    const [left, top] = laneTarget();
    const smooth = animate && !matchMedia("(prefers-reduced-motion: reduce)").matches;
    board.scrollTo({ left, top, behavior: smooth ? "smooth" : "auto" });
  };
  if (!animate) return go();
  board.scrollTo(0, 0);
  (document.fonts ? document.fonts.ready : Promise.resolve()).then(() => requestAnimationFrame(() => requestAnimationFrame(go)));
}

const SIZE_DEFAULTS = { zoom: 100, fill: true };
const epicOpen = (e) => epicMs.get(e.id).some((m) => !finished(m));
function setLaneCollapsed(id, c) {
  if (state.view === "epics") c ? state.open.le.delete(id) : state.open.le.add(id);
  else c ? state.open.lm.add(id) : state.open.lm.delete(id);
}
// Lane rules: each says which epics are collapsed; the menu checks the rule the current lanes match.
const LANE_RULES = [
  ["expandAll", "Expand all lanes", () => false],
  ["collapseAll", "Collapse all lanes", () => true],
  ["collapseFinished", "Collapse finished epics", (e) => !epicOpen(e)],
  ["expandOpen", "Expand only epics with open work", (e) => !epicOpen(e)],
];
const laneRuleOn = (rule) => D.epics.every((e) => isCollapsed(e.id) === rule(e));
const VM_ACTIONS = {
  arrows: () => { state.arrows = !state.arrows; },
  crit: () => { state.crit = !state.crit; },
  compact: () => { state.compact = !state.compact; },
  ...Object.fromEntries(FOLD_MODES.map((m) => ["fold-" + m, () => { foldSt.mode = m; foldSt.toggled.clear(); saveFold(); }])),
  foldEmpty: () => { foldSt.empty = !foldSt.empty; foldSt.toggled.clear(); saveFold(); },
  collapseAll: () => setAllCollapsed(true),
  expandAll: () => setAllCollapsed(false),
  collapseFinished: () => D.epics.forEach((e) => setLaneCollapsed(e.id, !epicOpen(e))),
  expandOpen: () => D.epics.forEach((e) => setLaneCollapsed(e.id, !epicOpen(e))),
  fill: () => { state.fill = !state.fill; },
  resetSize: () => Object.assign(state, SIZE_DEFAULTS),
};
function renderVm() {
  const pop = $("#vm"), focused = document.activeElement?.dataset?.vm;
  const chk = (k, name, on) => `<button class="frow" role="menuitemcheckbox" aria-checked="${on}" data-vm="${k}" tabindex="-1"><span class="cbx">${on ? icon("check") : ""}</span><span>${name}</span></button>`;
  if (DV() || boardOn()) {
    const L = LY(), name = BOARD_NAME[state.view];
    pop.innerHTML = `<div class="vm-h">Columns</div><div class="vm-cols">${layoutIds().map((g) => chk("dcol:" + g, name(g), !L.hidden.includes(g))).join("")}</div>
      <div class="fsep"></div><div class="vm-h">Cards</div>${chk("dsub", { dash: "Second line (reason, done count)", sprints: "Second line (blocked reason)", queue: "Second line (last change)", tasks: "Second line (milestone, reason)" }[state.view], L.sub)}
      <div class="fsep"></div><button class="frow btnrow" role="menuitem" data-vm="dreset" tabindex="-1">Reset layout</button>`;
    if (focused) pop.querySelector(`[data-vm="${CSS.escape(focused)}"]`)?.focus();
    return;
  }
  const radio = (k, name, on) => `<button class="frow" role="menuitemradio" aria-checked="${on}" data-vm="${k}" tabindex="-1"><span class="cbx round"></span><span>${name}</span></button>`;
  const custom = (on) => on ? `<button class="frow" role="menuitemradio" aria-checked="true" tabindex="-1" disabled><span class="cbx round"></span><span>Custom</span></button>` : "";
  const sprintCustom = foldSt.toggled.size > 0;
  const laneOn = LANE_RULES.map(([, , rule]) => laneRuleOn(rule));
  pop.innerHTML = `<div class="vm-h">Show</div>${chk("arrows", "Dependency arrows", state.arrows)}${chk("crit", "Critical path", state.crit)}${chk("compact", "Compact cards", state.compact)}
    <div class="fsep"></div><div class="vm-h">Sprints</div>
    ${[["none", "Unfold all sprints"], ["finished", "Fold finished sprints"], ["before", "Fold sprints before the current one"], ["all", "Fold all sprints"]].map(([m, n]) => radio("fold-" + m, n, !sprintCustom && foldSt.mode === m)).join("")}${custom(sprintCustom)}
    ${chk("foldEmpty", "Also fold empty sprints", foldSt.empty)}
    <div class="fsep"></div><div class="vm-h">Lanes</div>
    ${LANE_RULES.map(([k, n], i) => radio(k, n, laneOn[i])).join("")}${custom(!laneOn.some(Boolean))}
    <div class="fsep"></div><div class="vm-h">Size</div>
    <label class="vm-zoom"><span>Zoom</span><input type="range" id="vm-zoom" data-vm="zoom" min="60" max="150" step="5" value="${state.zoom}"><span class="n">${state.zoom}%</span></label>
    ${chk("fill", "Fill the screen width", state.fill)}<button class="frow btnrow" role="menuitem" data-vm="resetSize" tabindex="-1">Reset size</button>`;
  if (focused) pop.querySelector(`[data-vm="${CSS.escape(focused)}"]`)?.focus();
}
