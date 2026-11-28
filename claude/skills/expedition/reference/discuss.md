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
- In a release of format 2.2, the first message of a session to the owner holds the held block: the output of `status/waits.py <release> --held`, unchanged ([formats.md](formats.md), Waits for you line). Nothing printed: no block.
- The details and the options of an item are written in chat while it is discussed, and go into its item file when it settles (Item format, Storing).
- Each accepted decision is a decision file, `decisions/D<n>-<slug>.md` ([formats.md](formats.md), Decision file): its front matter holds its status, its decider and where it came from, and its body says what was decided. `decisions.md` is the list of every decision file, written by the scripts ([formats.md](formats.md), decisions.md). The scripts set every status of a decision; nobody edits the front matter or the list. A number is never reused or renumbered. A release that keeps its decisions on a board (format 2.1 or lower, or format 2.2 before its decisions moved to files): [old-form/format-2.1.md](old-form/format-2.1.md), Decision board.
- Each item filed in the release is one item file, `queue/Q<n>-<slug>.md` ([formats.md](formats.md), Item file), and `queue.md` is the list of every item file, written by the scripts ([formats.md](formats.md), queue.md). The item's `status` is its state: `to-do`, `blocked`, `done`, `backlog` or `archived`. The `to-do` items are the queue; a `blocked` item waits for other items (below); the others are the history. The owner sees the queue in the Queue view of the dashboard page. A release of format 2.1 keeps the five words of that format and shows the queue on its task board: [old-form/format-2.1.md](old-form/format-2.1.md). A release of format 2.0 or 1.0 keeps its queue as a kanban board: [old-form/queue-board.md](old-form/queue-board.md).
- Writes to plan files go only through the scripts, apart from the targeted edits this file names (an item's `## Details` and `## Options:`, the body of a decision file). Reads are free: `queue/next.py` and `queue/list.py` cover the usual ones; any other read is the session's own read-only command.
- Research: inline, or one or two agents for lookups. The lead never launches a Workflow.
- One item is open in chat at a time. The next item is posted only after the owner's explicit word on the open one (SKILL.md, Explicit word).
- Every item raised by the owner, and every item from the lead, a lookup or the run that passes the bar at filing ([formats.md](formats.md), Item file), is filed with `queue/item.py <release> Q "<title>" --bullet "<the owner's remark>"` in the turn it is raised, before it is posted. The script makes the item file with `status: to-do` and the bullet under `## Notes`, and prints the Q id. For an item the lead raises, the bullet is its first fact line. An owner message with five remarks files five items. An item the owner raises with its answer in the same message ("fix the link right now") is filed and posted like any other, and waits for the explicit word.
- Outcomes for the open item, only on the explicit word (SKILL.md, Explicit word). Each `D` call and each command that closes an item takes `--decider`: `you` when the owner made the call, `lead` when the lead made it alone; the script refuses the call without it, before anything is written.
  - "record it": first write the item to its file (Item format, Storing), then run `queue/item.py <release> D "<title>" --source Q<n> --option <n> --decider you` with the number of the picked option. It sets `status: done`, `decision: D<n>`, `option: <n>` and `decider: you` in the item file, and writes the decision file with `status: to-do`, `decider: you` and `source: Q<n>`. The decider is stored in both files.
  - An item the lead settles alone (Screen): `queue/item.py <release> D "<title>" --source Q<n> --decider lead`.
  - "iterate": records it as "record it" does and starts it at once (Epics, `iterate`).
  - "later": `queue/item.py <release> --move Q<n> Later`, with no `--decider` (sets `status: backlog`).
  - "drop it": `queue/item.py <release> --move Q<n> Dropped --decider you` (sets `status: archived`).
  - A parked item is reopened with `--move Q<n> Open`: it becomes `to-do` and loses its `decision`, `option` and `decider` lines.
- A decision with nothing to run (a process rule, a fact) is closed when it is recorded: `decisions/close.py <release> D<n>` sets `done`. A decision that moves to another release: `decisions/close.py <release> D<n> --backlog` sets `backlog`, and that release's specs cite it as `(v0.<m>.x D<n>)`.
- A decision file with no `decider` line was recorded before its release moved to decision files. `status/report.py` counts them in one line. When the lead knows who made the call: `decisions/decider.py <release> D<n> you|lead|agent` writes the line; it refuses a file that has one.
- The owner switches to another item while one is open without the explicit word ("let's do Q14 first"): the open item settles, so write it to its file (Item format, Storing), add the points made so far to its `## Notes` with `queue/item.py <release> --fact Q<n> "<text>"`, worded as what was said ("Owner leans to separate folders, because ..."), never as a decision ("Owner decides ..."), leave it `to-do`, and post the item the owner asked for. The switched-from item comes back in queue order like any other.
- The lead never invents an item number: every item carries the Q id `queue/item.py` printed, a settled item also its D id.
- An item that needs a lookup: start the lookup agent and give it the Q id and the path of the item file. The agent adds its facts to `## Notes` with `queue/item.py <release> --fact Q<n> "<text>"` and reports one line. The lead skips that item while its lookup runs. A lookup that returns while another item is open gets exactly one line in chat, `Q15 ready`, never a full item.
- **Waits for other items.** An item that cannot be decided before other items are: `queue/item.py <release> --depends Q<n> "Q14, Q15"`, with the Q ids it waits for (`""` removes the line). The scripts then keep its `status` at `blocked` while a named item is not `done`, and set it to `to-do` again when every named item is `done`. `queue/next.py` never prints a blocked item; `queue/list.py <release> Open` lists it with `(blocked: waits for Q14, Q15)` after its title. Nobody sets `blocked` by hand.
- Next item: `queue/next.py <release>` prints the path and the text of the `to-do` item with the lowest number, or `none`. The item open in chat is also `to-do` in its file, so the lead asks for the next item only after the explicit word on the open one. No session reads every item file to find what is next.
- **Route.** A remark that belongs to a spec in progress becomes a module, task and milestone of that spec: once its decision is recorded, `plan/milestone.py add <release> <spec> "<Name>" --decision D<n>` and one `NOTE E<n>: milestone <name> added` to the runner. The lead fills the new module and the new task file (Goals, Verification) and commits them before the NOTE line. Other work is a decision for a new spec (Epics). The lead says which in one line.
- The lead asks the runner for a review or a Workflow only where the Review rule of [plan.md](plan.md) applies (a public API, shared state, a change across specs), or when the owner asked for it.
- **Screen.** Before it posts an item, the lead runs three checks on it, in order:
  1. Already decided or rejected: `grep -rn -i -s '<key word>' .ai/plans/v*.x/<owner>/decisions.md .ai/plans/v*.x/<owner>/decisions/` from the repo root, for this release and the earlier ones (a release with a decision board has no `decisions/` folder, and `-s` keeps grep quiet about it), and `queue/list.py <release> Dropped --facts`.
  2. A duplicate of another item in the queue: `queue/list.py <release> Open --facts`.
  3. The weight test (SKILL.md, Owner input).

  An item that fails 1 or 2, or is not a problem: Lead-side close. An item that passes the weight test: the lead settles it. Only an item that fails the weight test is posted.
- **Lead-side close.** An item that is a duplicate, already decided or rejected, or not a problem is closed without the owner: `queue/item.py <release> --fact Q<n> "<reason, naming the other item or the decision>"`, then `queue/item.py <release> --move Q<n> Dropped --decider lead`.
- What the lead settled or closed reaches the owner in the settled list ([formats.md](formats.md), Settled list).
- Both sessions may discuss and record decisions, under the shared-file rules in [formats.md](formats.md).
- A finished lookup agent stays idle, not stopped: it costs nothing idle, and a follow-up on the same area goes to it by name (`SendMessage`) so its context is reused. Stop agents only when the owner says so.
- **Waits for you line.** In a release of format 2.2, every message of the lead to the owner ends with one line that names each thing that waits for the owner and each decision the owner holds ([formats.md](formats.md), Waits for you line). The steps:
  1. After the last plan write of the turn, make one call of `status/waits.py <release>`: with no flag in a turn the owner started, with `--new` in every other turn (Epics, Push). With an item in the same message, add `--skip Q<n>` for that item.
  2. Put the first line it prints, unchanged, as the last line of the message, after the `Say:` block. The `new:` lines of `--new` are for the push, not for the message. Nothing printed: no line.
  3. Never edit the line, and never write one without the command. Never make two calls for one message: each call records what it printed, so a second call loses the `new:` lines.

  An entry stays in the line until the owner's answer changes the fact behind it:

  | Entry | Leaves on |
  |---|---|
  | `E3 planned: delegate` | `delegate` |
  | `D14 ready: compose` | `compose`, `iterate D14`, or `hold D14` (it moves to `Held:`) |
  | `D14: hold over, ready: compose` | `compose`, `iterate D14`, or a new `hold D14` |
  | `05-04: your look` | the owner's word on the look: the lead ticks the `Owner:` box and runs `status/status.py <release> set 05-04 done` |
  | `Q18: record it` | "record it", "iterate", "later" or "drop it" on that item |

  A release of format 2.1 or lower has no line: [old-form/format-2.1.md](old-form/format-2.1.md), What differs.

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
- The `Say:` block is the last part of an item and of an epic message. In a release of format 2.2 the Waits for you line follows it as the last line of the message (Discussing items, Waits for you line). A letter alone is the command. In an item with several options the owner gives the option number with it ("2, A"); no number means the recommended option.
- **Repost.** During a discussion the lead answers in chat. The whole item comes again only when the talk on it ended and the proposal changed, or on the owner's word `restate`. The talk on an item ended when the owner's reply to it holds no question, asks for no change, and is no explicit word (SKILL.md, Explicit word). Then, if the proposal changed since the last post, the lead posts the whole item one time, with every agreed change in it and the `Say:` block, and waits. If the proposal did not change: no post. `restate` posts the item as it stands and records nothing.
- A repost is the whole item. It keeps every line word for word; only the lines the owner asked to change are changed. No rephrasing. No line and no option from the lead's own answers goes into it. It shows the title, all bullets and all options: no "unchanged" line, no part left out.

No question at the end: the item ends with its `Say:` block, and the options are the question. Options are about the decision only: fix, keep, drop, or which variant. An option never names an epic, a sprint or a release, and never offers to decide later; the owner says "later" or "drop it" unprompted. Record the decision only on the explicit word (SKILL.md, Explicit word), in that same turn, then post the next item.
- Recording: the item is written to its file before it is recorded (Storing). Then run `python3 -I ${CLAUDE_SKILL_DIR}/scripts/queue/item.py <release> D "<title>" --source Q<n> --decider you` (`--source Q<n>` for a queued item; `--option <n>` only when the owner picked option `<n>` of a posted item; an item the lead settles itself is recorded with `--source Q<n> --decider lead` and no `--option`; the script refuses an option number the item file does not have, and a `D` call without `--decider`). The decider is stored in the decision file and in the item file (`decider: you`). The script writes the decision file with its front matter and its title line. Then the lead writes the body of that file by a targeted edit, and commits: lines taken from the picked option stay word for word; the body is free, bullets by default, a table or a code block where it reads better ([formats.md](formats.md), Decision file); no `- Source:` line, because `source` is in the front matter. Then it replies with the id the script printed. The item has no D number before that.
- Handoff: only when the owner asks. State and Open only, what the next session needs; never history. State names the runner window and the writer's session name and uuid (formats.md, Handoff).
- Before a handoff and before a roll over, the lead runs `status/sync.py <release>`: in format 2.2 a status change makes no commit, and the sync commits the release folder in one commit.

## Epics

- Epic hint: a nudge, never a question and never a step the owner must take. After each recorded decision, run `epics/overlap.py <release>` with no id. It writes nothing and prints the decisions under `Ready:` (`to-do` and in no epic) and under `Blocked:` (each with what it waits for), one line each, in the shape of the message. A decision with a row in the table of an epic file, a planned epic, is in neither list: it is planned already. As soon as 1 decision is ready, add the `Epic ready: E<n>` message under the next item, in the shape of [../templates/epic-messages.md](../templates/epic-messages.md) (filled: [../example/epic-messages.md](../example/epic-messages.md)):
  - The lines under `Ready:` are the decisions of the message. The lead still leaves out a ready decision whose dependency on another decision is not satisfied.
  - The lines under `Blocked:` are its block `Blocked`, word for word. The lead does not work the block out by itself, and the block is absent when the command prints no `Blocked:` line.
  - A blocked decision never waits for a word: it is `to-do` again by itself when the epic it waits for has merged, and the next hint lists it as ready. `compose delegate with D<n>` puts a blocked decision into this epic.
  - A decision never waits for others to fill an epic, and an epic of one decision is normal.
  - Post it when a decision becomes ready. After that the Waits for you line carries the entry `D<n> ready: compose` in every message until the owner answers (Discussing items, Waits for you line); the message is not posted again for the same decisions. A held decision is not in it. The next item is posted in the same message; discussion never waits for `compose`. The owner says `compose` when they choose, or names items to add (`compose with D<n>`) or hold. Nothing else triggers it.
  - In a release with a decision board the lead works the list and the block out by itself: [old-form/format-2.1.md](old-form/format-2.1.md), Decision board.
- The files of a new decision: when the lead records a decision that no spec cites and knows the files it changes, it gives them in the same turn, `epics/overlap.py <release> D<n> --files "<files>"` (paths as the project writes them, separated by `, `; `""` removes them). The scripts then set the decision `blocked` while a running epic owns one of those files. The files are dropped once a spec cites the decision.
- **Hold.** Only the owner holds. The lead never holds a decision on its own judgment; a decision that does not exist yet is not a dependency. The hold is stored in the status file by `decisions/hold.py`, and a held decision is not in the `Epic ready` message:

  | Owner | Lead |
  |---|---|
  | `hold D14` | `decisions/hold.py <release> D14` |
  | `hold D14 until Q8` | `decisions/hold.py <release> D14 --until Q8` (a queue item, a decision or an epic) |
  | `hold D9`, with a reason in words | `decisions/hold.py <release> D9 --reason "<the owner's words>"` |
  | `compose with D14`, `iterate D14` | the regular steps; `epics/new.py` removes the hold |
  | the reason is gone (Q8 is closed) | nothing to run: the line says `D14: hold over, ready: compose`, and the lead says that sentence one time, in the message where it first shows |

  - A hold with a reason in words, or with none, ends only on the owner's word: `decisions/hold.py <release> D<n> --off` when the owner lifts it. Only a hold `until <id>` ends by itself, when `<id>` is `done` or `archived`.
  - The held block (`status/waits.py <release> --held`) is posted in the first message of a session (Discussing items) and in the message that reports `DONE E<n>`.
  - A release with a decision board stores no hold: [old-form/format-2.1.md](old-form/format-2.1.md), What differs.
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
- On the `SPECS E<n> <spec numbers>` message: compare each spec with its decisions and fix inline. Check the plan by judgment, reading the epic file only and running no script for it: the same file under two specs, or a long run of different sprints, is a question, not an error. Send the spec writer back (type into its window) when a clearly better cut exists. The lead reports nothing it fixed; a choice for the owner found in the check is posted as an item, and the epic waits for it. Then post the `Epic planned: E<n>` message ([../templates/epic-messages.md](../templates/epic-messages.md)): the specs, one plain line each. In a release of format 2.2 the lead makes its one call with `--new` for that message, and sends the push (Push, below).
- On `delegate` (old name `go`): `run/go.py <release> E<n> --from <lead>` (`<lead>` is this session's name, from `ListAgents`: "This session is <name>"), then post the next item. Its steps, in order:
  1. `epics/tag.py` (tags the specs, writes `epic: E<n>` into the file of each decision, which makes it `in progress`, writes the `starts:` sprint; the item files keep only their decision id, and in a release of format 2.0 it ticks the epic's cards in `queue.md` and tags them `#E<n>`).
  2. Commit specs, tags, plan rows and the queue.
  3. `sprints/refresh.py`.
  4. The final Ownership table of the epic file, with its Sprint column, committed.
  5. `run/runner.sh stop "<release> specs E<n>"` (closes the spec writer's window).
  6. `run/runner.sh start <release>` when `run/runner.sh list` shows no runner, then the RUN line `run/runner.sh send --confirm <release> "RUN E<n> <release folder> epic <release folder>/plan/epics/E<n>.md from <lead>"`; the go confirms that the runner has the line: it goes on only when the line is in the runner's transcript.
  7. The next epic's stub.
  A failed step stops it with one line naming the step: fix the cause and run `run/go.py` again. An epic never gains a decision after go, with one exception: a decision for a spec in progress joins that spec's epic (`plan/milestone.py add --decision`).
- On `DONE` or `BLOCKED` from the runner: read the grid with `sprints/grid.py <release>`, the tracker and `queue/next.py <release>`, and set no status by hand; the run's items are queue items like any other. The lead runs `sprints/refresh.py` only through `run/go.py`, or in Changing a decision. In a release of format 2.2 the message that reports `DONE E<n>` holds the held block (`status/waits.py <release> --held`, unchanged), and the lead makes its one call with `--new` and sends the push (Push).
- **Push.** In a release of format 2.2, in a turn the owner did not start (a `SPECS`, `DONE`, `BLOCKED` or `NOTE` message of another session, a task notification), the lead makes its one call of `status/waits.py <release> --new` and sends at most one push for the turn, with the tool `PushNotification`:

  | The turn is on | The push names |
  |---|---|
  | `DONE E<n>` | `E<n> done`, always, and each `new:` entry |
  | `BLOCKED E<n>` | `E<n> blocked`, always, and each `new:` entry |
  | `SPECS`, `NOTE`, a task notification | each `new:` entry; no `new:` line, no push |

  - The message is `<release>: ` and the parts joined by ` · `, for example `v2.1.x: E3 done · 05-04: your look`. It stays under 200 characters: the parts that do not fit are left out, and the message ends with `· more in chat`.
  - A turn the owner started gets no push: the lead makes its one call with no flag, and the owner sees the line in chat.
  - A session with no `PushNotification` tool sends no push and says nothing about it.
  - A "not sent" result of the tool is not tried again.
  - Each call records what it printed, so no entry is pushed twice.
  - The runner sends `NOTE <task id>: waits for the owner's look` when a task starts to wait for the owner's look ([run.md](run.md), Epics): the lead's turn on that note sends its push.
- Release is a spec. The owner decides which epic it joins.

## Changing a decision

Changing a decision (D7 changed to D15). Built means a milestone citing D7 is `in progress`, `blocked` after its launch, or `done`; `status/report.py` lists the decisions still editable.

- Not recorded: change in chat, record once.
- Not built: edit the body of D7's file in place, same id, commit first.
  - Spec writer writing the specs: type the change into its window; the SPECS check catches the rest.
  - Specs written, no go: small, the lead edits the citing specs (`grep '(D7)'`); larger, open the spec writer for the epic a second time (`run/runner.sh fork`), then SPECS and the lead check.
  - RUN sent, every milestone of the epic still `to-do`: type `HOLD E<n>`, edit D7, rewrite the citing specs, `epics/table.py <release> E<n>`, `sprints/refresh.py`, commit, a Notes line in `plan/epics/E<n>.md`, then the RUN line again.
- Built: `decisions/supersede.py <release> D7 D15` makes D7 `archived` with `replaced_by: D15`. It writes nothing into D15: when a reader of D15 needs to know what it replaces, the lead writes a line about D7 into the body of D15 (targeted edit, then commit). Send `NOTE D7: superseded by D15` to the other session; D15 waits for the next epic, or starts at once when the owner said `iterate`.
  - A citing milestone `in progress`: two moves only, by size. Big change: `SKIP <spec>` plus a Notes line naming D15. Small: let it finish; the next epic patches it.
  - A citing milestone `done`, or D7 `done`: no skip, never a revert; the next epic patches forward.
  - The epic also releases: type `SKIP <release spec>` at once (default hold) and post an item: the release ships the old behaviour, release now or hold. Release only on the owner's explicit yes; otherwise release and patch join the next epic.
- D7 already superseded: a change to D7 is a change to its current decision; apply that decision's stage.
