# Stage 1: discuss

For the lead: read this file whole before the first discussion turn of a session and after a compaction. The rules for what the owner's words mean are in [SKILL.md](../SKILL.md), Owner input, and are not repeated here.

## Contents
- Discussing items
- Item format
- Epics
- Changing a decision

## Discussing items

Interactive. You research and propose; the owner gives feedback and accepts.

- Read the last handoff in full and run `queue/next.py <release>` before saying anything. Something the work needs is not in them: `/recall` (transcript grep, ctx_search, ask the prior session named in the handoff), never re-derive it from the code.
- A lead that starts fresh on a release with a live runner (`run/runner.sh list`) first sends `run/runner.sh send <release> "HELLO from <lead>"`, before anything else.
- Options are written once, in chat, when the item is posted; never in a file.
- `decisions.md` holds accepted decisions only, as `**D<n>**` cards on a kanban board ([formats.md](formats.md), decisions.md) in three lanes, To do, In progress and Done, set by the scripts. A number is never reused or renumbered.
- `queue.md` holds every card filed in the release, as `**Q<n>**` cards on a kanban board ([formats.md](formats.md), queue.md): the Open lane is the queue, the other lanes are the history. The owner may view and drag it in the Unified Kanban extension.
- Writes to plan files go only through the scripts. Reads are free: `queue/next.py` and `queue/list.py` cover the usual ones; any other read is the session's own read-only command.
- Research: inline, or one or two agents for lookups. The lead never launches a Workflow.
- One item is open in chat at a time. The next item is posted only after the owner's explicit word on the open one (SKILL.md, Explicit word).
- Every item raised by the owner, and every item from the lead, a lookup or the run that passes the bar at filing ([formats.md](formats.md), queue.md), is filed with `queue/item.py <release> Q "<title>"` in the turn it is raised, before it is posted. An owner message with five remarks files five cards. An item the owner raises with its answer in the same message ("fix the link right now") is filed and posted like any other, and waits for the explicit word.
- Outcomes for the open item, only on the explicit word (SKILL.md, Explicit word): "record it" runs `queue/item.py <release> D "<title>" --source Q<n>` (moves the card to Decided with the tag `#D<n>` and writes the decision's last bullet `- Source: Q<n>`); "later" runs `queue/item.py <release> --move Q<n> Later`; "drop it" `--move Q<n> Dropped`. A parked card is reopened with `--move Q<n> Open`.
- The owner switches to another item while one is open without the explicit word ("let's do Q14 first"): add the points made so far to the open item's card with `queue/item.py <release> --fact Q<n> "<text>"`, worded as what was said ("Owner leans to separate folders, because ..."), never as a decision ("Owner decides ..."), leave it in Open, and post the item the owner asked for. The switched-from item comes back in queue order like any other.
- The lead never invents an item number: every item carries the Q id `queue/item.py` printed, a settled item also its D id.
- An item that needs a lookup: start the lookup agent and give it the Q id and the `queue.md` path. The agent adds its facts with `queue/item.py <release> --fact Q<n> "<text>"` and reports one line. The lead skips that card while its lookup runs. A lookup that returns while another item is open gets exactly one line in chat, `Q15 ready`, never a full item.
- Next item: `queue/next.py <release>` prints the first card in Open with its facts, or `none`. The open item's card is also in Open, so the lead asks for the next item only after the explicit word on the open one. No session reads the whole file to find what is next.
- **Route.** A remark that belongs to a spec in progress becomes a module, task and milestone of that spec: once its decision is recorded, `plan/milestone.py add <release> <spec> "<Name>" --decision D<n>` and one `NOTE E<n>: milestone <name> added` to the runner. The lead fills the new module and the new task file (Goals, Verification) and commits them before the NOTE line. Other work is a decision for a new spec (Epics). The lead says which in one line.
- **Screen.** Before it posts a card, the lead runs three checks on it, in order:
  1. Already decided or rejected: `grep -n -i '<key word>' .ai/plans/v*.x/<owner>/decisions.md` from the repo root, for this release and the earlier ones, and `queue/list.py <release> Dropped --facts`.
  2. A duplicate of another open card: `queue/list.py <release> Open --facts`.
  3. The weight test (SKILL.md, Owner input).

  A card that fails 1 or 2, or is not a problem: Lead-side close. A card that passes the weight test: the lead settles it. Only a card that fails the weight test is posted.
- **Lead-side close.** A card that is a duplicate, already decided or rejected, or not a problem leaves Open without the owner: `queue/item.py <release> --fact Q<n> "<reason, naming the other card or the decision>"`, then `queue/item.py <release> --move Q<n> Dropped`.
- What the lead settled or closed reaches the owner in the settled list ([formats.md](formats.md), Settled list).
- Both sessions may discuss and record decisions, under the shared-file rules in [formats.md](formats.md).
- A finished lookup agent stays idle, not stopped: it costs nothing idle, and a follow-up on the same area goes to it by name (`SendMessage`) so its context is reused. Stop agents only when the owner says so.

## Item format

Item format, one item per message, the next item only after the explicit word on this one (SKILL.md, Explicit word). Every item is headed `# Q<n>. <sentence>`; there is no unnumbered item header:

```
# Q<n>. <Title>: one plain sentence a non-expert reads in one pass, in everyday words, no ids, paths or jargon.
- the first bullet, required: what is wrong today, where, and what the change is (file:line, ids, measurements)
- optional bullets: facts, how the common references do it (measured or read, never assumed)
## Options:
- recommended: ...
- ...
```

No question at the end; the options are the question. Options are about the decision only: fix, keep, drop, or which variant. An option never names an epic, a sprint or a release, and never offers to decide later; the owner says "later" or "drop it" unprompted. Write the decision into `decisions.md` only on the explicit word (SKILL.md, Explicit word), in that same turn, then post the next item.
- Recording: run `python3 -I ${CLAUDE_SKILL_DIR}/scripts/queue/item.py <release> D "<title>"` (with `--source Q<n>` for a queued item), write the bullets under the card it made, each indented with one tab, above a `- Source:` line (targeted edit, then commit), and reply with the id it printed. The item has no D number before that.
- Handoff: only when the owner asks. State and Open only, what the next session needs; never history. State names the runner window and the writer's session name and uuid (formats.md, Handoff).

## Epics

- Epic hint: a nudge, never a question and never a step the owner must take. After each recorded decision, take the cards in the To do lane of `decisions.md` whose dependencies are satisfied, and run `epics/overlap.py` on them; an overlapping item is held, with the one line `Held: D8 shares <file> with D7.` As soon as 1 item is ready, add the one line `Epic ready: D1, D4, D5. Say "epic go" to start it now.` under the next item; a decision never waits for others to fill an epic, and an epic of one decision is normal. Post it once per set, and not again until another item becomes ready. The next item is posted in the same message; discussion never waits for `epic`. The owner says `epic` when they choose, or names items to add or hold. Nothing else triggers it.
- `hold D<n>`: the item leaves this epic and waits for the next hint. Only the owner holds. The lead never holds an item on its own judgment; a decision that does not exist yet is not a dependency.
- Epic file `plan/epics/E<n>.md` (formats.md, Epic file): started by `epics/new.py` on `epic`; run/go.py writes the next epic's stub the moment the RUN is sent. A Notes line, with `epics/new.py <release> E<n> --note "<text>"`, only when discussion yields what the specs cannot hold: a rule change since the last epic, an owner tried-and-rejected, a wish with no decision, a cross-epic order, a SKIP, HOLD or RESUME during the run.
- A note for the running epic is typed into the runner (`run/runner.sh send <release> "NOTE E<n>: <note>"`) only once its item is closed; an urgent note (`Urgent:` first) at once, re-typed every runner tick until its ack lands. A note without ack is re-typed at the next RUN or DONE (`status/report.py` lists them).
- A committed change to how the runner works (a P bullet, run.md, tick.md, the brief, this skill): in the same turn, unasked, an urgent note in the running epic's file and the line `RULES: <files>, <one line why>` typed into the runner; it replies `ACK RULES <the first words of that line>`, so two RULES lines sent close together are told apart.
- On `epic`: one recheck message listing the epic's decisions as a set; `epics/new.py <release> E<n> <D ids>` (the `Decisions:` line and one Ownership row per decision, committed). Then `run/runner.sh fork <release> E<n> "<D ids>" --from <lead>`: the spec writer, a forked session of the lead, in window `<release> specs E<n>`, fills the Files column, cuts the epic into specs by the three aims, writes them with `plan/new_spec.py`, completes the table with `epics/table.py`, checks the plan, and sends `SPECS` ([plan.md](plan.md)). Discussion continues.
- `epic go` (or `epic` and `go` in one message): the go is given in advance. The recheck message is still posted, the spec writer writes the specs, and on the `SPECS` message the lead does its check and then runs `run/go.py` at once; no ready line, no wait. A check that finds a spec contradicting a decision stops there and posts the ready line instead.
- On the `SPECS E<n> <spec numbers>` message: compare each spec with its decisions and fix inline. Check the plan by judgment, reading the epic file only and running no script for it: the same file under two specs, or a long run of different sprints, is a question, not an error. Send the spec writer back (type into its window) when a clearly better cut exists. Then post one line: `Epic E12 ready: specs 39 to 49, sprints S17 to S18. Changed: <what or nothing>. Say go.`
- On `go`: `run/go.py <release> E<n> --from <lead>` (`<lead>` is this session's name, from `ListAgents`: "This session is <name>"), then post the next item. Its steps, in order:
  1. `epics/tag.py` (tags the specs, adds `#E<n>` to the decisions and moves them to In progress, writes `Starts:`, ticks the epic's cards in `queue.md` and tags them `#E<n>`).
  2. Commit specs, tags, plan rows and `queue.md`.
  3. `sprints/refresh.py`.
  4. `Specs:` and the final Sprint column in the epic file, committed.
  5. `run/runner.sh stop "<release> specs E<n>"` (closes the spec writer's window).
  6. `run/runner.sh start <release>` when `run/runner.sh list` shows no runner, then the RUN line `run/runner.sh send <release> "RUN E<n> <release folder> epic <release folder>/plan/epics/E<n>.md from <lead>"`.
  7. The next epic's stub.
  A failed step stops it with one line naming the step: fix the cause and run `run/go.py` again. An epic never gains a decision after go, with one exception: a decision for a spec in progress joins that spec's epic (`plan/milestone.py add --decision`).
- On `DONE` or `BLOCKED` from the runner: read `status/sprints.md`, the tracker and `queue/next.py <release>`, and write nothing to the grid; the run's cards are queue cards like any other. The lead runs `sprints/refresh.py` only through `run/go.py`, or in Changing a decision.
- Release is a spec. The owner decides which epic it joins.

## Changing a decision

Changing a decision (D7 changed to D15). Built means a milestone citing D7 has a `[ ]`, `[~]` or `[x]` cell; `status/report.py` lists the decisions still editable.

- Not recorded: change in chat, record once.
- Not built: edit D7's bullets in place, same id, commit first.
  - Spec writer writing the specs: type the change into its window; the SPECS check catches the rest.
  - Specs written, no go: small, the lead edits the citing specs (`grep '(D7)'`); larger, open the spec writer for the epic a second time (`run/runner.sh fork`), then SPECS and the lead check.
  - RUN sent, every row `·`: type `HOLD E<n>`, edit D7, rewrite the citing specs, `epics/table.py <release> E<n>`, `sprints/refresh.py`, commit, a Notes line in `plan/epics/E<n>.md`, then the RUN line again.
- Built: `decisions/supersede.py <release> D7 D15` and send `NOTE D7: superseded by D15` to the other session; D15 waits for the next epic.
  - Row `[ ]`: two moves only, by size. Big change: `SKIP <spec>` plus a Notes line naming D15. Small: let it finish; the next epic patches it.
  - Row `[x]` or D7 in Done: no skip, never a revert; the next epic patches forward.
  - The epic also releases: type `SKIP <release spec>` at once (default hold) and post an item: the release ships the old behaviour, release now or hold. Release only on the owner's explicit yes; otherwise release and patch join the next epic.
- D7 already superseded: a change to D7 is a change to its current decision; apply that decision's stage.
