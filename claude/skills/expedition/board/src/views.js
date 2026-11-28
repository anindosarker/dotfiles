// ---- Sprints view: a vertical list, newest sprint on top; finished sprints start collapsed ----
const spCollapsed = (sp) => !active() && ((sp.status === "done") !== state.open.sp.has(sp.id));

// Sprints that pass the filter, in the sort order; spOrdered adds the board's saved column order.
function spBase() {
  const list = D.sprints.filter((sp) => pass(sp, "sprint"));
  if (sortOf().dir < 0) list.reverse();
  return list;
}
function spOrdered() {
  if (state.view !== "sprints") return spBase();
  const by = new Map(spBase().map((sp) => [sp.id, sp]));
  return layoutIds().map((id) => by.get(id)).filter(Boolean);
}
const msTurn = (m) => dIdx.get(m.id)?.turn || "";
function spCard(m) {
  const c = cnt.get(m), r = { turn: msTurn(m) };
  return `<div class="tc qcard dcard${isSel("ms:" + m.id)}" data-pick="ms:${esc(m.id)}" title="${esc(label("ms", m) + ". " + m.name)}">
    <div class="tc-top">${kc("ms", label("ms", m))}${kc("epic", m.epic)}<span class="tags">${dYou(r)}<span class="frac">${doneOf(c)}</span></span></div>
    <div class="tc-title">${esc(m.name)}</div>
    ${m.status === "blocked" && m.reason ? `<span class="d-sub" style="margin-top:3px">${esc(m.reason)}</span>` : ""}</div>`;
}
function renderSprintBoard() {
  const now = nowSprint(), nowId = now >= 0 ? D.sprints[now]?.id : null, hidden = state.splayout.hidden;
  const cols = spOrdered().filter((sp) => !hidden.includes(sp.id));
  if (!cols.length) return `<div class="empty">No milestone matches the filter.</div>`;
  return boardHtml(cols.map((sp) => { const c = cnt.get(sp);
    return { id: sp.id, headCls: "sp-bhead", head: `<button class="link${isSel("sprint:" + sp.id)}" data-pick="sprint:${esc(sp.id)}">${kc("sprint", sp.id)}</button>${pill(sp.status)}${sp.id === nowId ? `<span class="nowtag">now</span>` : ""}
      <span class="frac">${doneOf(c)}</span>${progress(c, false)}`, body: sorted(shownKids(sp, "sprint"), MS_KEYS[sortOf().key], 1).map(spCard).join("") }; }));
}
function renderSprints() {
  if (state.smode === "board") return renderSprintBoard();
  const list = D.sprints.filter((sp) => pass(sp, "sprint"));
  if (sortOf().dir < 0) list.reverse();
  if (!list.length) return `<div class="empty">No milestone matches the filter.</div>`;
  return `<div class="spl">${list.map((sp) => {
    const c = cnt.get(sp), closed = spCollapsed(sp), ms = sorted(shownKids(sp, "sprint"), MS_KEYS[sortOf().key], 1);
    return `<section class="sp-sec"><div class="sp-hd" data-sp="${esc(sp.id)}" title="Click to ${closed ? "expand" : "collapse"}">
      <span class="tog${closed ? "" : " open"}">${icon("chevron")}</span>
      <button class="link${isSel("sprint:" + sp.id)}" data-pick="sprint:${esc(sp.id)}">${kc("sprint", sp.id)}</button>${pill(sp.status)}
      <span class="sp-n">${kids.get(sp).length} milestone${kids.get(sp).length === 1 ? "" : "s"}</span>${progress(c)}</div>
      ${closed ? "" : `<div class="sp-rows">${ms.map(msRow).join("")}</div>`}</section>`;
  }).join("")}</div>`;
}
function msRow(m) {
  const open = state.open.c.has(m.id), c = cnt.get(m);
  let h = `<div class="mr ${skOf(m.status)}${isSel("ms:" + m.id)}" data-pick="ms:${esc(m.id)}">
    <button class="tog${open ? " open" : ""}" data-tog="c:${esc(m.id)}" aria-label="${open ? "Hide" : "Show"} tasks" title="${open ? "Hide" : "Show"} tasks">${icon("chevron")}</button>
    ${icon("flag", "mi")}<span class="m-num">${kc("ms", label("ms", m))}</span><span class="m-name" title="${esc(m.name)}">${esc(m.name)}</span>
    <span class="m-epic">${kc("epic", m.epic)}</span><span class="r-pill">${pill(m.status)}</span>${progress(c)}</div>`;
  if (open) h += `<div class="mr-tasks"><ul class="checklist${fx.tog === m.id ? " reveal" : ""}">${shownKids(m, "ms").map((t, i) => taskCheck(t).replace("<li ", `<li style="--i:${Math.min(i, 10)}" `)).join("") || `<li class="ck">No tasks</li>`}</ul></div>`;
  return h;
}
const taskCheck = (t) => `<li class="ck ${skOf(t.status)}${isSel("task:" + t.id)}" data-pick="task:${esc(t.id)}" title="${esc(t.status + (t.reason ? ": " + t.reason : ""))}">${sicon(t.status)}${kc("task", t.number)}<span class="ck-name">${esc(t.title)}</span>${t.ownerCheck ? `<span class="owner">${icon("eye")}owner</span>` : ""}${t.type === "bug" ? `<span class="tag">bug</span>` : ""}</li>`;

// ---- Tasks view: one column per status, newest first ----
function renderTasks() {
  const cols = stSet ? STATUSES.filter((s) => stSet.has(s)) : STATUSES;
  const by = new Map(cols.map((s) => [s, []]));
  for (const t of D.tasks) if (by.has(t.status) && pass(t, "task")) by.get(t.status).push(t);
  const so = sortOf();
  for (const [st, list] of by) by.set(st, sorted(list, TASK_KEYS[so.key], so.dir));
  return boardHtml(shownIds().filter((st) => by.has(st)).map((st) => {
    const list = by.get(st), compact = st === "done" || st === "archived";
    const lim = compact && !state.more.includes(st) ? COMPACT_LIMIT : Infinity;
    const items = list.slice(0, lim).map(compact ? taskLine : taskCard).join("");
    const more = list.length > lim ? `<button class="more" data-more="${esc(st)}">Show all ${list.length} (${list.length - lim} more)</button>` : "";
    return { id: st, cls: compact ? " compact" : "", head: `${sicon(st)}<span>${esc(capWord(st))}</span><span class="frac">${list.length}</span>`, body: items ? items + more : "" };
  }));
}
const msText = (m) => `${label("ms", m)} ${m.name}`;
function taskCard(t) {
  const m = idx.ms.get(t.milestone);
  return `<div class="tc b-${skOf(t.status)}${isSel("task:" + t.id)}" data-pick="task:${esc(t.id)}">
    <div class="tc-top">${kc("task", `${t.spec}-${t.number}`)}<span class="tags">${t.ownerCheck ? `<span class="owner">${icon("eye")}owner check</span>` : ""}<span class="tag">${esc(t.type)}</span></span></div>
    <div class="tc-title">${esc(t.title)}</div>
    <div class="tc-meta" title="${esc(m ? msText(m) : t.milestone)}">${m ? icon("flag", "mi") : ""}${esc(m ? msText(m) : t.milestone)} · ${esc(m?.epic)}</div>
    ${t.reason ? `<div class="tc-reason">${esc(t.reason)}</div>` : ""}</div>`;
}
function taskLine(t) {
  const m = idx.ms.get(t.milestone);
  return `<div class="tl ${skOf(t.status)}${isSel("task:" + t.id)}" data-pick="task:${esc(t.id)}" title="${esc(t.title + (m ? "\n" + msText(m) + " · " + m.epic : "") + (t.reason ? "\n" + t.reason : ""))}">
    ${kc("task", `${t.spec}-${t.number}`)}<span class="tl-t">${esc(t.title)}</span>${t.type === "bug" ? `<span class="tag">bug</span>` : ""}${m?.epic ? kc("epic", m.epic) : ""}</div>`;
}

// ---- Queue view: the queue rows of dashboard.data.js, one row per queue item ----
let QD = null, qIdx = new Map(), qHay = new Map(), qShown = [];
function loadQueue(data) {
  QD = data && Array.isArray(data.items) ? data : null;
  qIdx = new Map((QD ? QD.items : []).map((x) => [x.id, x]));
  qHay = new Map((QD ? QD.items : []).map((x) => [x, [x.id, x.title, x.status, x.decision, x.reason, x.depends_on, dBy(x), x.notes, x.details, x.options].join("\n").toLowerCase()]));
  if (state.sel?.startsWith("q:") && !get(state.sel)) state.sel = null;
}
const Q_KEYS = {
  status: (x) => [QSTATUSES.indexOf(x.status) < 0 ? QSTATUSES.length : QSTATUSES.indexOf(x.status), x.number ?? 0],
  number: (x) => x.number ?? null,
};
const qSub = (x) => [x.status === "blocked" ? x.reason : "", dBy(x)].filter(Boolean).join(" · ");
function qVisible() {
  if (!QD) return [];
  const st = state.qstatus.length ? new Set(state.qstatus) : null;
  const list = QD.items.filter((x) => (!st || st.has(x.status)) && terms.every((t) => qHay.get(x).includes(t)));
  const so = sortOf(), key = Q_KEYS[so.key] || Q_KEYS.status, dir = so.dir;
  return list.map((x, i) => [key(x), x, i]).sort((p, q) => {
    if (p[0] == null || q[0] == null) return p[0] == null && q[0] == null ? p[2] - q[2] : p[0] == null ? 1 : -1;
    return (cmp(p[0], q[0]) || (p[1].number ?? 0) - (q[1].number ?? 0)) * dir;
  }).map((p) => p[1]);
}
function qRow(x) {
  return `<div class="qr ${skOf(x.status) || "qo"}${isSel("q:" + x.id)}" data-pick="q:${esc(x.id)}" title="${esc(x.id + ". " + x.title)}">
    <span class="q-id">${kc("queue", x.id)}</span><span class="q-t">${esc(x.title)}${qSub(x) ? `<span class="d-sub">${esc(qSub(x))}</span>` : ""}</span>
    <span class="q-dec">${x.decision ? kc("decision", x.decision) : ""}</span>
    <span class="q-st">${pill(x.status)}</span>
    <span class="frac q-ch" title="${esc(x.changed ? "Status changed " + x.changed : "")}">${x.changed ? esc(relTime(x.changed)) : ""}</span></div>`;
}
function renderQueue() {
  if (!QD) { qShown = []; return `<div class="empty">No queue data. The page reads ${esc(DATA_DIR)}dashboard.data.js.</div>`; }
  qShown = qVisible();
  if (!qShown.length) return `<div class="empty">${QD.items.length ? "No queue item matches the filter." : "The queue is empty."}</div>`;
  if (state.qmode === "board") return boardHtml(qCols().map(([st, list]) => ({ id: st, head: `${sicon(st)}<span>${esc(capWord(st))}</span><span class="frac">${list.length}</span>`, body: list.map(qCard).join("") })));
  if (sortOf().key === "status") return listSections(QSTATUSES.map((st) => [st, qShown.filter((x) => x.status === st)]).filter(([, l]) => l.length)
    .map(([st, list]) => ({ id: st, head: `${sicon(st)}${esc(st)}<span class="frac">${list.length}</span>`, rows: list.map(qRow).join("") })), listFoot());
  return listSections([{ id: "all", head: `${icon("inbox", "c-ns")}All<span class="frac">${qShown.length}</span>`, rows: qShown.map(qRow).join("") }], listFoot());
}
// Board columns in the saved layout order, each keeping the sorted order of qShown.
const qCols = () => (state.view === "queue" ? shownIds() : QSTATUSES).filter((s) => !state.qstatus.length || state.qstatus.includes(s)).map((st) => [st, qShown.filter((x) => x.status === st)]);
function qCard(x) {
  return `<div class="tc qcard b-${skOf(x.status) || "qo"}${isSel("q:" + x.id)}" data-pick="q:${esc(x.id)}" title="${esc(x.id + ". " + x.title)}">
    <div class="tc-top">${kc("queue", x.id)}<span class="tags">${x.decision ? kc("decision", x.decision) : ""}</span></div>
    <div class="tc-title">${esc(x.title)}</div>
    ${qSub(x) ? `<span class="d-sub" style="margin-top:3px">${esc(qSub(x))}</span>` : ""}
    ${x.changed ? `<span class="frac q-ch" title="${esc("Status changed " + x.changed)}">${esc(relTime(x.changed))}</span>` : ""}</div>`;
}
// The picked option of a queue item: the number of the card of option_list that has picked set, "" when none.
const qPicked = (x) => { const o = (x.option_list || []).find((y) => y.picked); return o ? String(o.number) : ""; };
// The three texts of a queue item (D21): Notes and Details as Markdown, each under its own heading; an empty text has no heading.
// Options as the option cards of the approved page (Q30), from option_list; the text of "options" as Markdown only when no card was read.
const qTexts = (x, sec) => {
  const opts = x.option_list || [], picked = qPicked(x);
  let h = [["Notes", x.notes], ["Details", x.details]]
    .filter(([, t]) => typeof t === "string" && t).map(([n, t]) => sec(n, `<div class="md">${md(t)}</div>`)).join("");
  if (opts.length) h += sec(`Options (${opts.length})`, `<div class="opts">${opts.map((o) => {
    const isPick = !!o.picked;
    return `<div class="opt${isPick ? " picked" : picked ? " faded" : ""}"><div class="opt-h"><span class="opt-k">${esc(o.number)}.</span><span class="opt-t">${mdInline(o.title || "")}</span>
      <span class="opt-tags">${o.recommended ? `<span class="tag rec">recommended</span>` : ""}${isPick ? `<span class="tag pick">${icon("check")}picked</span>` : ""}</span></div>
      ${o.body ? `<div class="md">${md(o.body)}</div>` : ""}</div>`;
  }).join("")}</div>`);
  else if (typeof x.options === "string" && x.options) h += sec("Options", `<div class="md">${md(x.options)}</div>`);
  return h;
};
function queuePanel(x) {
  const abs = QD.root && x.file ? QD.root.replace(/\/+$/, "") + "/" + x.file : "";
  const qsec = (h, body, none) => `<div class="p-sec"><h3>${h}</h3>${body || `<p class="none">${none}</p>`}</div>`;
  const pos = qShown.findIndex((y) => y.id === x.id), picked = qPicked(x);
  let h = `<div class="p-top"><div class="crumbs"><span class="cur">${esc(QD.release || "")} queue${pos >= 0 ? ` · ${pos + 1} of ${qShown.length}` : ""}</span></div>
    <button class="ibtn sm" data-close aria-label="Close" data-tip="Close (Esc)" data-tip-end>${icon("x")}</button></div>
    <div class="p-kind">${KIND_LABEL.q} ${kc("queue", x.id)}</div><h2>${esc(x.title)}</h2>
    <div class="p-row">${pill(x.status)}${x.turn ? `<span class="d-turn t-${x.turn}">${icon(TURN_INFO[x.turn][1])}${TURN_INFO[x.turn][2]}</span>` : ""}${x.decision ? kc("decision", x.decision) : ""}${picked ? `<span class="tag pick">${icon("check")}option ${esc(picked)} picked</span>` : ""}</div>
    <div class="p-sec"><dl class="kv"><dt>Decision</dt><dd>${x.decision ? `<code>${esc(x.decision)}</code>${picked ? `, option ${esc(picked)}` : ""}` : `<span class="frac">none</span>`}</dd>
      ${x.reason ? `<dt>Reason</dt><dd>${esc(x.reason)}</dd>` : ""}${x.depends_on ? `<dt>Depends on</dt><dd>${esc(x.depends_on)}</dd>` : ""}
      ${x.decider ? `<dt>Decider</dt><dd>${esc(DECIDER[x.decider] || x.decider)}</dd>` : ""}${x.turn ? `<dt>Turn</dt><dd>${esc(x.turn)}</dd>` : ""}
      ${x.changed ? `<dt>Changed</dt><dd>${esc(x.changed)}</dd>` : ""}</dl></div>`;
  h += qsec("Item file", x.file ? `<div class="lnk"><code class="path">${esc(x.file)}</code>${abs ? `<a class="fbtn" href="${esc(vscodeUrl(abs))}" title="${esc(abs)}">VS Code</a><a class="fbtn" href="${esc(fileUrl(abs))}" target="_blank" title="${esc(abs)}">Browser</a>` : ""}</div>` : "", "No file.");
  h += qTexts(x, qsec);
  h += `<p class="pnote">Paths are relative to the plan folder${QD.root ? `: <code>${esc(QD.root)}</code>` : ""}.</p>`;
  return h;
}

// ---- Dashboard and All rows: one row per thing that needs a look, from dashboard.data.js ----
let DD = null, dIdx = new Map(), dHay = new Map(), dShown = [];
function loadDash(data) {
  DD = data && Array.isArray(data.rows) ? data : null;
  const rows = DD ? DD.rows : [];
  rows.forEach((r, i) => (r.order = i));
  dIdx = new Map(rows.map((r) => [r.id, r]));
  loadQueue(DD && { release: DD.release, root: DD.roots?.plan, items: rows.filter((r) => r.kind === "queue").map((r) => ({ ...r, number: +r.id.slice(1) })) });
  dHay = new Map(rows.map((r) => [r, [r.kind, r.id, r.label, r.title, r.reason, r.depends_on, r.decider ? "decided by " + r.decider : "", r.turn, TURN_INFO[r.turn]?.[2], r.status, r.command, r.ready ? "ready" : "", r.details].join("\n").toLowerCase()]));
  if (state.sel?.startsWith("r:") && !dIdx.has(state.sel.slice(2))) state.sel = null;
}
const D_KEYS = { group: (r) => [GROUPS.indexOf(r.status), r.order], kind: (r) => [KINDS.indexOf(r.kind), r.order], order: (r) => r.order };
function dVisible() {
  if (!DD) return [];
  const so = sortOf(), key = D_KEYS[so.key] || D_KEYS.group;
  return DD.rows.filter((r) => (!state.gfilter.length || state.gfilter.includes(r.status)) && (!state.kfilter.length || state.kfilter.includes(r.kind)) && (!state.tfilter.length || state.tfilter.includes(r.turn)) && terms.every((t) => dHay.get(r).includes(t)))
    .map((r) => [key(r), r]).sort((a, b) => cmp(a[0], b[0]) * so.dir || a[1].order - b[1].order).map((p) => p[1]);
}
const dPill = (r) => { const [k, ic] = DSTATUS[r.status] || ["ns", "circle"]; return `<span class="pill s-${k}">${icon(ic)}${esc(r.status)}</span>`; };
const dYou = (r) => { const t = TURN_INFO[r.turn]; return t ? `<span class="d-turn t-${r.turn}" title="${t[2]}" aria-label="${t[2]}" role="img">${icon(t[1])}</span>` : ""; };
// Muted second line: an epic's task count, a blocked item's reason, who decided (a closed queue item, a decision).
const DECIDER = { you: "you", lead: "the lead", agent: "an agent" };
const dBy = (r) => r.decider && (r.kind === "decision" || r.kind === "queue") ? "decided by " + (DECIDER[r.decider] || r.decider) : "";
// The chip shows the item's label in its kind's color; the kind word is the tooltip.
const dKind = (r) => `<span class="kchip k-${esc(r.kind)}" title="${esc(r.kind)}">${esc(r.label)}</span>`;
const dSub = (r) => !state.dlayout.sub ? "" : [r.progress ? `${r.progress.done}/${r.progress.total} done` : "", r.status === "blocked" ? r.reason : "", dBy(r)].filter(Boolean).join(" · ");
function dRow(r) {
  return `<div class="qr${isSel("r:" + r.id)}" data-pick="r:${esc(r.id)}" title="${esc(r.label + ". " + r.title)}">
    <span class="q-t">${dKind(r)}${esc(r.title)}${dSub(r) ? `<span class="d-sub">${esc(dSub(r))}</span>` : ""}</span>
    <span class="d-right">${dYou(r)}</span></div>`;
}
function dCard(r) {
  return `<div class="tc qcard dcard${isSel("r:" + r.id)}" data-pick="r:${esc(r.id)}" title="${esc(r.label + ". " + r.title)}">
    <div class="tc-top">${dKind(r)}<span class="tags">${dYou(r)}</span></div>
    <div class="tc-title">${esc(r.title)}</div>
    ${dSub(r) ? `<span class="d-sub" style="margin-top:3px">${esc(dSub(r))}</span>` : ""}</div>`;
}
const dCols = () => (state.view === "dash" ? shownIds() : GROUPS).filter((g) => !state.gfilter.length || state.gfilter.includes(g)).map((g) => [g, dShown.filter((r) => r.status === g)]);
function renderDash() {
  if (!DD) { dShown = []; return `<div class="empty">No dashboard data. The page reads ${esc(DATA_DIR)}dashboard.data.js.</div>`; }
  dShown = dVisible();
  if (state.dmode === "board") return boardHtml(dCols().map(([g, list]) => { const [name, ic, cls] = GROUP_INFO[g];
    return { id: g, head: `${icon(ic, cls)}<span>${esc(name)}</span><span class="frac">${list.length}</span>`, body: list.map(dCard).join("") }; }));
  if (!dShown.length) return `<div class="empty">No row matches the filter.</div>`;
  const foot = listFoot(" · <kbd>1</kbd>-<kbd>6</kbd> views");
  if (sortOf().key === "group") return listSections(GROUPS.map((g) => [g, dShown.filter((r) => r.status === g)]).filter(([, l]) => l.length)
    .map(([g, list]) => { const [name, ic, cls] = GROUP_INFO[g]; return { id: g, head: `${icon(ic, cls)}${esc(name)}<span class="frac">${list.length}</span>`, rows: list.map(dRow).join("") }; }), foot);
  return listSections([{ id: "all", head: `${icon("inbox", "c-ns")}All items<span class="frac">${dShown.length}</span>`, rows: dShown.map(dRow).join("") }], foot);
}
function dashPanel(r) {
  const root = DD.roots?.[r.root], abs = root && r.file ? root.replace(/\/+$/, "") + "/" + r.file : "";
  const pos = dShown.findIndex((y) => y.id === r.id);
  const dsec = (h, body, none) => `<div class="p-sec"><h3>${h}</h3>${body || `<p class="none">${none}</p>`}</div>`;
  let h = `<div class="p-top"><div class="crumbs"><span class="cur">${esc(GROUP_INFO[r.status]?.[0] || r.status)}${pos >= 0 ? ` · ${pos + 1} of ${dShown.length}` : ""}</span></div>
    <button class="ibtn sm" data-close aria-label="Close" data-tip="Close (Esc)" data-tip-end>${icon("x")}</button></div>
    <div class="p-head"><div class="p-kind">${esc(r.kind)} ${dKind(r)}</div><h2>${esc(r.title)}</h2>
    <div class="p-row">${dPill(r)}${r.turn ? `<span class="d-turn t-${r.turn}">${icon(TURN_INFO[r.turn][1])}${TURN_INFO[r.turn][2]}</span>` : ""}</div></div>
    <div class="p-sec"><dl class="kv">${r.reason ? `<dt>Reason</dt><dd>${esc(r.reason)}</dd>` : ""}${r.progress ? `<dt>Tasks</dt><dd>${r.progress.done}/${r.progress.total} done</dd>` : ""}
      ${r.ready ? `<dt>Ready</dt><dd>waits for your go (<code>${esc(r.command)} ${esc(r.id)}</code>)</dd>` : ""}${r.depends_on ? `<dt>Depends on</dt><dd>${esc(r.depends_on)}</dd>` : ""}
      ${r.decider ? `<dt>Decider</dt><dd>${esc(DECIDER[r.decider] || r.decider)}</dd>` : ""}${r.turn ? `<dt>Turn</dt><dd>${esc(r.turn)}</dd>` : ""}
      <dt>Id</dt><dd><code>${esc(r.id)}</code></dd></dl></div>`;
  h += dsec("File", r.file ? `<div class="lnk"><code class="path">${esc(r.file)}</code>${abs ? `<a class="fbtn" href="${esc(vscodeUrl(abs))}" title="${esc(abs)}">VS Code</a><a class="fbtn" href="${esc(fileUrl(abs))}" target="_blank" title="${esc(abs)}">Browser</a>` : ""}</div>` : "", "No file for this row.");
  h += r.kind === "queue" ? qTexts(r, dsec) : dsec("Details", r.details ? `<div class="md">${md(r.details)}</div>` : "", "No details.");
  return h;
}

// ---- Render ----
const RENDER = { sprints: renderSprints, epics: renderLanes, milestones: renderLanes, tasks: renderTasks, queue: renderQueue, dash: renderDash, all: renderDash };
