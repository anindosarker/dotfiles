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
- The details and the options of an item are written in chat while it is discussed, and go into its item file when it settles (Item format, Storing).
- `decisions.md` holds accepted decisions only, as `**D<n>**` cards on a kanban board ([formats.md](formats.md), decisions.md) in three lanes, To do, In progress and Done, set by the scripts. A number is never reused or renumbered.
- Each item filed in the release is one item file, `queue/Q<n>-<slug>.md` ([formats.md](formats.md), Item file), and `queue.md` is the list of every item file, written by the scripts ([formats.md](formats.md), queue.md). The item's `status` is its state: `to-do`, `blocked`, `done`, `backlog` or `archived`. The `to-do` items are the queue; a `blocked` item waits for other items (below); the others are the history. The owner sees the queue in the Queue view of the dashboard page. A release of format 2.1 keeps the five words of that format and shows the queue on its task board: [old-form/format-2.1.md](old-form/format-2.1.md). A release of format 2.0 or 1.0 keeps its queue as a kanban board: [old-form/queue-board.md](old-form/queue-board.md).
- Writes to plan files go only through the scripts, apart from the targeted edits this file names (an item's `## Details` and `## Options:`, a decision's bullets). Reads are free: `queue/next.py` and `queue/list.py` cover the usual ones; any other read is the session's own read-only command.
- Research: inline, or one or two agents for lookups. The lead never launches a Workflow.
- One item is open in chat at a time. The next item is posted only after the owner's explicit word on the open one (SKILL.md, Explicit word).
- Every item raised by the owner, and every item from the lead, a lookup or the run that passes the bar at filing ([formats.md](formats.md), Item file), is filed with `queue/item.py <release> Q "<title>" --bullet "<the owner's remark>"` in the turn it is raised, before it is posted. The script makes the item file with `status: to-do` and the bullet under `## Notes`, and prints the Q id. For an item the lead raises, the bullet is its first fact line. An owner message with five remarks files five items. An item the owner raises with its answer in the same message ("fix the link right now") is filed and posted like any other, and waits for the explicit word.
- Outcomes for the open item, only on the explicit word (SKILL.md, Explicit word). Each command that closes an item takes `--decider`: `you` when the owner made the call, `lead` when the lead made it alone; the script refuses the call without it, before anything is written.
  - "record it": first write the item to its file (Item format, Storing), then run `queue/item.py <release> D "<title>" --source Q<n> --option <n> --decider you` with the number of the picked option. It sets `status: done`, `decision: D<n>`, `option: <n>` and `decider: you` in the item file, and writes the decision's last bullet `- Source: Q<n>`.
  - An item the lead settles alone (Screen): `queue/item.py <release> D "<title>" --source Q<n> --decider lead`.
  - "iterate": records it as "record it" does and starts it at once (Epics, `iterate`).
  - "later": `queue/item.py <release> --move Q<n> Later`, with no `--decider` (sets `status: backlog`).
  - "drop it": `queue/item.py <release> --move Q<n> Dropped --decider you` (sets `status: archived`).
  - A parked item is reopened with `--move Q<n> Open`: it becomes `to-do` and loses its `decision`, `option` and `decider` lines.
- The owner switches to another item while one is open without the explicit word ("let's do Q14 first"): the open item settles, so write it to its file (Item format, Storing), add the points made so far to its `## Notes` with `queue/item.py <release> --fact Q<n> "<text>"`, worded as what was said ("Owner leans to separate folders, because ..."), never as a decision ("Owner decides ..."), leave it `to-do`, and post the item the owner asked for. The switched-from item comes back in queue order like any other.
- The lead never invents an item number: every item carries the Q id `queue/item.py` printed, a settled item also its D id.
- An item that needs a lookup: start the lookup agent and give it the Q id and the path of the item file. The agent adds its facts to `## Notes` with `queue/item.py <release> --fact Q<n> "<text>"` and reports one line. The lead skips that item while its lookup runs. A lookup that returns while another item is open gets exactly one line in chat, `Q15 ready`, never a full item.
- **Waits for other items.** An item that cannot be decided before other items are: `queue/item.py <release> --depends Q<n> "Q14, Q15"`, with the Q ids it waits for (`""` removes the line). The scripts then keep its `status` at `blocked` while a named item is not `done`, and set it to `to-do` again when every named item is `done`. `queue/next.py` never prints a blocked item; `queue/list.py <release> Open` lists it with `(blocked: waits for Q14, Q15)` after its title. Nobody sets `blocked` by hand.
- Next item: `queue/next.py <release>` prints the path and the text of the `to-do` item with the lowest number, or `none`. The item open in chat is also `to-do` in its file, so the lead asks for the next item only after the explicit word on the open one. No session reads every item file to find what is next.
- **Route.** A remark that belongs to a spec in progress becomes a module, task and milestone of that spec: once its decision is recorded, `plan/milestone.py add <release> <spec> "<Name>" --decision D<n>` and one `NOTE E<n>: milestone <name> added` to the runner. The lead fills the new module and the new task file (Goals, Verification) and commits them before the NOTE line. Other work is a decision for a new spec (Epics). The lead says which in one line.
- The lead asks the runner for a review or a Workflow only where the Review rule of [plan.md](plan.md) applies (a public API, shared state, a change across specs), or when the owner asked for it.
- **Screen.** Before it posts an item, the lead runs three checks on it, in order:
  1. Already decided or rejected: `grep -n -i '<key word>' .ai/plans/v*.x/<owner>/decisions.md` from the repo root, for this release and the earlier ones, and `queue/list.py <release> Dropped --facts`.
  2. A duplicate of another item in the queue: `queue/list.py <release> Open --facts`.
  3. The weight test (SKILL.md, Owner input).

  An item that fails 1 or 2, or is not a problem: Lead-side close. An item that passes the weight test: the lead settles it. Only an item that fails the weight test is posted.
- **Lead-side close.** An item that is a duplicate, already decided or rejected, or not a problem is closed without the owner: `queue/item.py <release> --fact Q<n> "<reason, naming the other item or the decision>"`, then `queue/item.py <release> --move Q<n> Dropped --decider lead`.
- What the lead settled or closed reaches the owner in the settled list ([formats.md](formats.md), Settled list).
- Both sessions may discuss and record decisions, under the shared-file rules in [formats.md](formats.md).
- A finished lookup agent stays idle, not stopped: it costs nothing idle, and a follow-up on the same area goes to it by name (`SendMessage`) so its context is reused. Stop agents only when the owner says so.

## Item format

Item format, one item per message, the next item only after the explicit word on this one (SKILL.md, Explicit word). Every item is headed `# Q<n>. <sentence>`; there is no unnumbered item header:

- The shape: [../templates/queue-item.md](../templates/queue-item.md). The item in chat is the title, `Details` and `Options:` as they are in the file, then the `Say:` block; `## Notes` is not shown. The `Say:` block is the one of [../templates/item.md](../templates/item.md) (A `record it`, B `iterate`), in every format. Filled items: `example/v1.0.x/owner/queue/`, for example [Q42](../example/v1.0.x/owner/queue/Q42-the-sidebar-has-no-shortcut-to-open-and-close-it.md) and [Q49](../example/v1.0.x/owner/queue/Q49-a-select-menu-in-the-sidebar-turns-translucent-after-a.md). Read both before the first item. In a release of format 2.0 or lower the chat form is [../templates/item.md](../templates/item.md) (filled: [../example/item-examples.md](../example/item-examples.md)).
- The first post comes before the file has `## Details` and `## Options:`: the lead posts them in that same shape and writes them to the file when the item settles (Storing).
- **Storing.** During the back and forth: no write to the file. The lead works in chat. The lead writes the item (`## Details`, `## Options:`) to its file when the item settles. It judges that itself: the owner reaches a final state on it, or the talk moves to another item, or another item comes in. The write is a targeted edit of the item file and one commit. Each line goes into the file as it was last posted, word for word. When the owner agreed to a change in chat after the last post, the file holds the final form: the posted lines with that change in them. `## Notes` and the front matter are the scripts' (`--bullet`, `--fact`, `D`, `--move`); the lead never edits them, and never edits `queue.md`.
- **Form.** Fixed are the title (one plain sentence, no ids, paths or jargon), the numbered options, the recommended one first, the `Say:` block. Inside an option: bullets by default. A table or a code block only where bullets do not work.
- **Check before every post**, the first post too. The four checks come after the Screen, on an item that is posted:
  - Each line is needed for this decision. Nothing that another decision settled.
  - What the owner needs to finish the item is in it.
  - ASD-STE100 words, short lines.
  - Option 2 is a different idea. If there is none: one option.
- The `Say:` block is the last part of an item and of an epic message. A letter alone is the command. In an item with several options the owner gives the option number with it ("2, A"); no number means the recommended option.
- **Repost.** During a discussion the lead answers in chat. The whole item comes again only when the talk on it ended and the proposal changed, or on the owner's word `restate`. The talk on an item ended when the owner's reply to it holds no question, asks for no change, and is no explicit word (SKILL.md, Explicit word). Then, if the proposal changed since the last post, the lead posts the whole item one time, with every agreed change in it and the `Say:` block, and waits. If the proposal did not change: no post. `restate` posts the item as it stands and records nothing.
- A repost is the whole item. It keeps every line word for word; only the lines the owner asked to change are changed. No rephrasing. It shows the title, all bullets and all options: no "unchanged" line, no part left out.

No question at the end: the item ends with its `Say:` block, and the options are the question. Options are about the decision only: fix, keep, drop, or which variant. An option never names an epic, a sprint or a release, and never offers to decide later; the owner says "later" or "drop it" unprompted. Write the decision into `decisions.md` only on the explicit word (SKILL.md, Explicit word), in that same turn, then post the next item.
- Recording: the item is written to its file before it is recorded (Storing). Then run `python3 -I ${CLAUDE_SKILL_DIR}/scripts/queue/item.py <release> D "<title>" --source Q<n> --decider you` (`--source Q<n>` for a queued item; `--option <n>` only when the owner picked option `<n>` of a posted item; an item the lead settles itself is recorded with `--source Q<n> --decider lead` and no `--option`; the script refuses an option number the item file does not have, and a `--source` call without `--decider`). The decider is stored in the item file (`decider: you`); the decision card is written as before and holds no decider. Then write the bullets under the card it made (lines taken from the picked option stay word for word), each indented with one tab, above a `- Source:` line (targeted edit, then commit), and reply with the id it printed. The item has no D number before that.
- Handoff: only when the owner asks. State and Open only, what the next session needs; never history. State names the runner window and the writer's session name and uuid (formats.md, Handoff).

## Epics

- Epic hint: a nudge, never a question and never a step the owner must take. After each recorded decision, take the cards in the To do lane of `decisions.md` whose dependencies are satisfied, and run `epics/overlap.py` on them. As soon as 1 item is ready, add the `Epic ready: E<n>` message under the next item, in the shape of [../templates/epic-messages.md](../templates/epic-messages.md) (filled: [../example/epic-messages.md](../example/epic-messages.md)): the ready decisions, one plain line each. A decision that overlaps a running epic is not in the list; it is under `Decided, not in this epic:` with the epic it waits for, and that block is absent when no decision waits; a decision never waits for others to fill an epic, and an epic of one decision is normal. Post it once per set, and not again until another item becomes ready. The next item is posted in the same message; discussion never waits for `compose`. The owner says `compose` when they choose, or names items to add (`compose with D<n>`) or hold. Nothing else triggers it.
- `hold D<n>`: the item leaves this epic and waits for the next hint. Only the owner holds. The lead never holds an item on its own judgment; a decision that does not exist yet is not a dependency.
- Epic file `plan/epics/E<n>.md` (formats.md, Epic file): started by `epics/new.py` on `compose`; run/go.py writes the next epic's stub the moment the RUN is sent. A Notes line, with `epics/new.py <release> E<n> --note "<text>"`, only when discussion yields what the specs cannot hold: a rule change since the last epic, an owner tried-and-rejected, a wish with no decision, a cross-epic order, a SKIP, HOLD or RESUME during the run.
- A note for the running epic is typed into the runner (`run/runner.sh send <release> "NOTE E<n>: <note>"`) only once its item is closed; an urgent note (`Urgent:` first) at once, re-typed every runner tick until its ack lands. A note without ack is re-typed at the next RUN or DONE (`status/report.py` lists them).
- A committed change to how the runner works (a P bullet, run.md, tick.md, the brief, this skill): in the same turn, unasked, an urgent note in the running epic's file and the line `RULES: <files>, <one line why>` typed into the runner; it replies `ACK RULES <the first words of that line>`, so two RULES lines sent close together are told apart.
- On `compose` (old name `epic`): one recheck message listing the epic's decisions as a set; `epics/new.py <release> E<n> <D ids>` (one Ownership row per decision, committed). Then `run/runner.sh fork <release> E<n> "<D ids>" --from <lead>`: the spec writer, a forked session of the lead, in window `<release> specs E<n>`, fills the Files column, cuts the epic into specs by the three aims, writes them with `plan/new_spec.py`, completes the table with `epics/table.py`, checks the plan, and sends `SPECS` ([plan.md](plan.md)). Discussion continues.
- `compose delegate` (or `compose` and `delegate` in one message; old names `epic delegate`, `epic go`): the go is given in advance. The recheck message is still posted, the spec writer writes the specs, and on the `SPECS` message the lead does its check and then runs `run/go.py` at once; no `Epic planned` message, no wait. A check that finds a choice for the owner stops there and posts it as an item.
- `iterate` on the open item: this one item is decided, planned and sent to the runner at once, by the regular steps and with no wait for other items. The lead records it as for "record it", decides by itself which case it is, and says so in one line. The owner says nothing more after it. `iterate D<n>` does the same for a decision that is already recorded and waits.
  - The item belongs to a spec in progress: Route (above). It becomes the next module, task file and milestone of that spec, it joins that spec's epic, and the `NOTE` line tells the runner.
  - No spec in progress fits (a spec that is done takes nothing): an epic of this one decision, by the steps of `compose delegate`: `epics/new.py`, the spec writer, the SPECS check, then `run/go.py` at once.
  - The item replaces work that is built or runs: Changing a decision, in the same turn.
  - The plan files and the line to the runner hold what the runner needs to choose the moment: the files the item changes and the work it replaces. The runner decides when it starts ([run.md](run.md), Orchestration).
- On the `SPECS E<n> <spec numbers>` message: compare each spec with its decisions and fix inline. Check the plan by judgment, reading the epic file only and running no script for it: the same file under two specs, or a long run of different sprints, is a question, not an error. Send the spec writer back (type into its window) when a clearly better cut exists. The lead reports nothing it fixed; a choice for the owner found in the check is posted as an item, and the epic waits for it. Then post the `Epic planned: E<n>` message ([../templates/epic-messages.md](../templates/epic-messages.md)): the specs, one plain line each.
- On `delegate` (old name `go`): `run/go.py <release> E<n> --from <lead>` (`<lead>` is this session's name, from `ListAgents`: "This session is <name>"), then post the next item. Its steps, in order:
  1. `epics/tag.py` (tags the specs, adds `#E<n>` to the decisions and moves them to In progress, writes the `starts:` sprint; the item files keep only their decision id, and in a release of format 2.0 it ticks the epic's cards in `queue.md` and tags them `#E<n>`).
  2. Commit specs, tags, plan rows and the queue.
  3. `sprints/refresh.py`.
  4. The final Ownership table of the epic file, with its Sprint column, committed.
  5. `run/runner.sh stop "<release> specs E<n>"` (closes the spec writer's window).
  6. `run/runner.sh start <release>` when `run/runner.sh list` shows no runner, then the RUN line `run/runner.sh send <release> "RUN E<n> <release folder> epic <release folder>/plan/epics/E<n>.md from <lead>"`.
  7. The next epic's stub.
  A failed step stops it with one line naming the step: fix the cause and run `run/go.py` again. An epic never gains a decision after go, with one exception: a decision for a spec in progress joins that spec's epic (`plan/milestone.py add --decision`).
- On `DONE` or `BLOCKED` from the runner: read the grid with `sprints/grid.py <release>`, the tracker and `queue/next.py <release>`, and set no status by hand; the run's items are queue items like any other. The lead runs `sprints/refresh.py` only through `run/go.py`, or in Changing a decision.
- Release is a spec. The owner decides which epic it joins.

## Changing a decision

Changing a decision (D7 changed to D15). Built means a milestone citing D7 is `in progress`, `blocked` after its launch, or `done`; `status/report.py` lists the decisions still editable.

- Not recorded: change in chat, record once.
- Not built: edit D7's bullets in place, same id, commit first.
  - Spec writer writing the specs: type the change into its window; the SPECS check catches the rest.
  - Specs written, no go: small, the lead edits the citing specs (`grep '(D7)'`); larger, open the spec writer for the epic a second time (`run/runner.sh fork`), then SPECS and the lead check.
  - RUN sent, every milestone of the epic still `to-do`: type `HOLD E<n>`, edit D7, rewrite the citing specs, `epics/table.py <release> E<n>`, `sprints/refresh.py`, commit, a Notes line in `plan/epics/E<n>.md`, then the RUN line again.
- Built: `decisions/supersede.py <release> D7 D15` and send `NOTE D7: superseded by D15` to the other session; D15 waits for the next epic, or starts at once when the owner said `iterate`.
  - A citing milestone `in progress`: two moves only, by size. Big change: `SKIP <spec>` plus a Notes line naming D15. Small: let it finish; the next epic patches it.
  - A citing milestone `done`, or D7 in Done: no skip, never a revert; the next epic patches forward.
  - The epic also releases: type `SKIP <release spec>` at once (default hold) and post an item: the release ships the old behaviour, release now or hold. Release only on the owner's explicit yes; otherwise release and patch join the next epic.
- D7 already superseded: a change to D7 is a change to its current decision; apply that decision's stage.
