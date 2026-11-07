// Expedition workflow template: a stage library plus a short composition; one Workflow run covers one milestone
// (several when a stage is rerun: edit the script, resume with resumeFromRunId).
// Stages (each returns its result, or a stop result with `status` that ends only its milestone):
//   build(p), filesCheck(p, build), reviewBounce(p, build) (only when p.review === 'fable'), verify(p),
//   judges(p, src) (when p.judged is set), merge(p, verify), check(sprint), release(sprint).
// The composition at the bottom runs the one MILESTONES entry (this milestone) build to merge. Only the release milestone's
// script sets RELEASE_MILESTONE and composes check and release over MERGED_MILESTONES (the [x] rows of sprints.md).
// The MILESTONES entry is one milestone: a "### Milestone:" block of an epic (a row of ownership.md and of sprints.md).
// Copy, then edit meta, INTEGRATION, RELEASE_LABEL, RELEASE_PREFIX, RELEASE_EPIC, GATE_JUDGED, MIRROR,
// the RUN_* switches, SERIAL_GATES, SHIP_PARTIAL, RELEASE_MILESTONE, MERGED_MILESTONES, STOPPED_MILESTONES, MILESTONES, BASE_SHA
// and SPECIFICS. Keep the rest.
// Project facts live in the release's process.md (P<n> rules); prompts name it by path instead of repeating it.
export const meta = {
  name: 'v<release>-milestone-<slug>',
  description: 'v<release> milestone <name> (epic NN, worktree <name>): build, files check, review, verify, judges, merge; the release milestone adds check and release',
  phases: [
    { title: 'Milestone NN build' }, { title: 'Milestone NN review' }, { title: 'Milestone NN verify' },
    // release milestone only:
    { title: 'Release check' }, { title: 'Release' },
  ],
}

const ROOT = '/abs/path/to/repo' // the main checkout: merge, check and release run here
const PLANS = '.ai/plans/v<release>/<owner>'
const PROCESS_FILE = `${PLANS}/process.md`
const INTEGRATION = '<integration branch>'
const MIRROR = 'dev' // the staging branch: untouched during the sprints, fast-forwarded to INTEGRATION once after the last feature column (process.md P1)
const RELEASE_LABEL = '<release label>'
const RELEASE_PREFIX = 'v<release>' // merge commit subject: `merge: <milestone> (<epic>)`
const RELEASE_EPIC = `${PLANS}/epics/<release epic>.md` // the release milestone's check and release steps
const GATE_JUDGED = null // { question: '...', captures: ['...'] | 'tracker' } when RELEASE_EPIC names a judged clause
// Stage switches: a milestone turns a stage off here.
const RUN_FILES_CHECK = true, RUN_REVIEW = true, RUN_VERIFY = true, RUN_JUDGES = true, RUN_MERGE = true, RUN_GATE = true, RUN_RELEASE = true
const SERIAL_GATES = false // true: check bases one after another (loaded machine, per process.md)
const SHIP_PARTIAL = true // release what merged when some milestone stopped
// Release milestone only: RELEASE_MILESTONE true runs check and release after this milestone's own stages.
const RELEASE_MILESTONE = false
const MERGED_MILESTONES = [] // release milestone: the milestones marked [x] in sprints.md, by their grid names
const STOPPED_MILESTONES = [] // release milestone: { milestone: '<name>', status: 'blocked' | ... } for rows not merged
const MILESTONES = [
  // One entry: this milestone (empty for a release milestone with no build of its own). `epic` is the epic number; `plan` is the epic file and `tracker` the milestone's tracker (a string or an array).
  // review: 'fable' runs the review bounce (the milestone block says `Review: fable`); judged: { question, captures: [...] | 'tracker' }, judgeCount (default 3).
  { id: 'NN', epic: 'NN', wt: `${ROOT}.worktrees/<slug>`, branch: 'v<release>/<slug>', plan: `${PLANS}/epics/NN-<slug>.md`, tracker: `${PLANS}/trackers/NN-<milestone-slug>-tracker.md`, title: '<milestone name>', review: 'fable', judged: null },
  // releaseLabel overrides RELEASE_LABEL for a milestone whose label differs (P6): { ..., releaseLabel: '<label>' }.
  // A shared run: several file sets, one branch. `lead` is the shared prework prompt on the run worktree,
  // `fileSets` one builder each; `plan` and `tracker` may be arrays, one per epic or milestone, joined by `list`.
  // Each file set has its own worktree `wt` and branch `branch` (`<slug>-<set>` for both), cut from the run branch after the lead's last commit.
  // { id: '02-05', wt: ..., branch: ..., plan: [...], tracker: [...], title: '<milestone names>', lead: '...', fileSets: [{ label: 'a', wt: `${ROOT}.worktrees/<slug>-a`, branch: 'v<release>/<slug>-a', files: ['...'], prompt: '...' }] },
]
const list = (x) => [].concat(x).join(', ')
const BASE_SHA = '<sha of origin/INTEGRATION the branch started from>'

const RULES = (p, wt = p.wt, branch = p.branch) => `
Rules that bind you: read ${PROCESS_FILE} first (the project facts: branches, merge, checks, agent sandbox) and follow every line. In addition:
- Work ONLY in the git worktree ${wt} on branch ${branch} (checked out, clean, dependencies installed, at ${BASE_SHA} = origin/${INTEGRATION}).
- Commit trailer and PR body line exactly as the harness reminder gives them.
- Decisions: ${PLANS}/decisions.md (read it first; the plan implements decisions, never re-decides).
- Questions are not possible. Pick the sensible default; record a judgment call the owner may want to revert as one bullet under "## Attention" in ${list(p.tracker)}. Never stop the run. If your milestone cannot be finished (contradicts an accepted decision, Acceptance unreachable), commit what is coherent, write why under "## Attention" in ${list(p.tracker)}, return blocked=true with blockedReason; the run continues with the other milestones.
- Your final text is a return value for a script, not a message to a human.`

const BUILD_SCHEMA = { type: 'object', properties: {
  blocked: { type: 'boolean' }, blockedReason: { type: 'string' }, head: { type: 'string' },
  commits: { type: 'array', items: { type: 'object', properties: { sha: { type: 'string' }, subject: { type: 'string' } }, required: ['sha', 'subject'] } },
  notes: { type: 'array', items: { type: 'string' } },
  attention: { type: 'array', items: { type: 'string' } },
}, required: ['blocked', 'head', 'commits', 'notes', 'attention'] }

const REVIEW_SCHEMA = { type: 'object', properties: {
  pass: { type: 'boolean' },
  contradictsDecision: { type: 'boolean' },
  findings: { type: 'array', items: { type: 'object', properties: {
    severity: { type: 'string', enum: ['major', 'minor', 'nit'] }, file: { type: 'string' }, line: { type: 'integer' },
    problem: { type: 'string' }, fix: { type: 'string' }, standardSection: { type: 'string' } }, required: ['severity', 'file', 'problem', 'fix'] } },
}, required: ['pass', 'contradictsDecision', 'findings'] }

const VERIFY_SCHEMA = { type: 'object', properties: {
  allPass: { type: 'boolean' }, head: { type: 'string' },
  checks: { type: 'array', items: { type: 'object', properties: { check: { type: 'string' }, pass: { type: 'boolean' }, output: { type: 'string' } }, required: ['check', 'pass', 'output'] } },
  failures: { type: 'array', items: { type: 'string' } }, notes: { type: 'array', items: { type: 'string' } },
  attention: { type: 'array', items: { type: 'string' } },
}, required: ['allPass', 'head', 'checks', 'failures', 'notes', 'attention'] }

// Everything the plan leaves to implementation but must be done one way: which helper to
// reuse, exact UI strings, which files to git mv, known name clashes, what must stay byte-identical.
const SPECIFICS = {
  'NN': `Milestone NN specifics: ...`,
}

const buildPrompt = (p, wt = p.wt, branch = p.branch) => `You are the coder for milestone ${p.id}. Implement its "### Milestone:" block of the epic ${list(p.plan)} (read the epic whole, plus ${PLANS}/plan.md, ${PLANS}/ownership.md and ${PLANS}/decisions.md) on worktree ${wt}.
${RULES(p, wt, branch)}
How to work:
- The branch may already hold commits from an interrupted earlier attempt: read \`git log --oneline ${BASE_SHA}..HEAD\` and \`git status\` first and continue from that state; do not redo finished tasks.
- The epic's "Acceptance:" line (section 1.2) is your check: run it yourself and keep going until it passes; for a judged check, capture, compare against the named reference, run the judges, fix, repeat.
- Follow your milestone's Task lines in order (its block in section 2.1). Each task ends with its checks green and one or more commits pushed. Per task run only tsc and lint on your own files; at milestone end run the unit tests plus one base of the long per-base checks. The verifier runs every base. Slow checks run in parallel, not one after another: per-base checks on separate ports at once, builds at once, test runs at once.
- Record every check you ran in ${list(p.tracker)} under "Checks:" as one bullet: command, commit, result. The verifier trusts that record and does not repeat it. Set "Status: running" when you start; add one line per task with its last commit. No narration, no check output, no commit lists.
- Design decisions are in the epic; implementation is yours. Where the epic says "does NOT", respect it.
- ${SPECIFICS[p.id]}
- Push after each task; no PR: a milestone merges into ${INTEGRATION} on its recorded local checks (process.md P1). Do not wait for CI.
Return: blocked, blockedReason (when blocked), head (short sha after your last push), commits (sha and subject, in order), notes (facts the reviewer and verifier need), attention (what needs the owner; usually empty).`

const reviewPrompt = (p, round, prior) => `You are the reviewer for milestone ${p.id}, round ${round}. Review the branch ${p.branch} on worktree ${p.wt}: \`git diff ${BASE_SHA}..HEAD\` plus \`git log --oneline ${BASE_SHA}..HEAD\`, against the epic ${list(p.plan)} (its milestone block), ${PLANS}/decisions.md and the project standards (cite the section for each finding).
${RULES(p)}
Review for: correctness against the epic (every "does" done, every "does NOT" respected), a finding that contradicts an accepted decision (set contradictsDecision=true and say which), dead code, docs and changelog accuracy, tracker completeness, the project's forbidden patterns, missing commit trailer. Read the actual files; do not trust commit messages. Run the cheap checks yourself.
${round > 1 && prior ? `Round ${round} is incremental: review only \`git diff ${prior.head}..HEAD\` (the fixer's commits), not the whole branch. Previous round findings and the fixer's report: ${JSON.stringify(prior)}. Confirm each was fixed or re-raise it.` : ''}
Do not edit files. Return pass (true only when no major findings remain), contradictsDecision, and findings, each with severity, file, line, problem, fix, standardSection.`

const fixPrompt = (p, findings) => `You are the fixer for milestone ${p.id} on worktree ${p.wt}. Read the findings and \`git diff ${BASE_SHA}..HEAD\` only; open an epic or decisions line only where a finding may contradict it. Apply these review findings (major first; minor and nit too unless they contradict the epic ${list(p.plan)} or ${PLANS}/decisions.md, in which case say why in notes): ${JSON.stringify(findings)}.
${RULES(p)}
One commit per concern, pushed. Re-record in ${list(p.tracker)} every check you reran after a code change (command, commit, result). Return blocked (true only when a finding cannot be fixed without contradicting an accepted decision), blockedReason, head, commits, notes (per finding: fixed or declined, and why), attention.`

const verifyPrompt = (p) => `You are the verifier for milestone ${p.id} on worktree ${p.wt}, branch ${p.branch}. Read the Checks section of ${list(p.tracker)} first. Do NOT rerun a check recorded there whose commit is HEAD, or whose \`git diff --name-only <recorded commit>..HEAD\` touches only plan files and the changelog. Run only the checks of section 2.2 of ${list(p.plan)} that are missing, from a clean tree, in parallel where independent, and record them. The long checks (pages check, Storybook build, browser tests per base) run here once, every base concurrently, never per task. CI is the second run for tsc, lint, tests and builds; do not repeat those locally when recorded green.
${RULES(p)}
Rerun the epic's "Acceptance:" check (section 1.2) once and record it. No PR exists for a milestone (process.md P1): the main session merges on the recorded checks.
Append or extend the Checks section in ${list(p.tracker)} with one line per check and who ran it, commit ("docs(plan): milestone ${p.id} checks"), push.
Return allPass, head, checks (check, pass, output excerpt), failures, notes, attention.`

// A blocked result never throws and never stops the other MILESTONES entries: the main session
// records it, skips the milestones that depend on it, and merges everything else.
const blocked = (p, reason, extra) => ({ milestone: p.id, status: 'blocked', blockedReason: reason, ...extra })

const strs = { type: 'array', items: { type: 'string' } }
const FILES_CHECK_SCHEMA = { type: 'object', properties: { filesMatch: { type: 'boolean' }, extra: strs, missing: strs, notes: strs }, required: ['filesMatch', 'extra', 'missing', 'notes'] }
const JUDGE_SCHEMA = { type: 'object', properties: { pass: { type: 'boolean' }, lines: strs }, required: ['pass', 'lines'] }
const MERGE_SCHEMA = { type: 'object', properties: { mergeSha: { type: 'string' }, notes: strs, attention: strs }, required: ['mergeSha', 'notes', 'attention'] }
const GATE_SCHEMA = { type: 'object', properties: { pass: { type: 'boolean' }, perBase: { type: 'array', items: { type: 'object', properties: { base: { type: 'string' }, pass: { type: 'boolean' }, output: { type: 'string' } }, required: ['base', 'pass', 'output'] } }, captures: strs, attention: strs }, required: ['pass', 'perBase', 'captures', 'attention'] }
const RELEASE_SCHEMA = { type: 'object', properties: { version: { type: 'string' }, tag: { type: 'string' }, prs: strs, runs: strs, smoke: { type: 'string' }, attention: strs }, required: ['version', 'tag', 'prs', 'runs', 'smoke', 'attention'] }

// Rules for agents in the main checkout (merge, check, release): no worktree, plan files committed by path.
const ROOT_RULES = `
Rules that bind you: read ${PROCESS_FILE} first (the project facts: branches, merge, checks, agent sandbox) and follow every line. In addition:
- Work in the main checkout ${ROOT}. Run \`git -C ${ROOT} status\` first; leave unrelated changes as they are. Commit plan files only with named paths (\`git commit -- <paths>\`), never \`git add -A\` or \`git commit -a\`.
- Commit trailer and PR body line exactly as the harness reminder gives them.
- Decisions: ${PLANS}/decisions.md (read it first; never re-decide).
- Questions are not possible. Record a judgment call the owner may want to revert as one line in attention. Never stop the run.
- Your final text is a return value for a script, not a message to a human.`

const filesCheckPrompt = (p, b) => `You are the files checker for milestone ${p.id} on worktree ${p.wt}, branch ${p.branch} (head ${b.head}). Run \`git diff ${BASE_SHA}..HEAD --stat\` and compare the touched files with the Files owned line of the milestone's block and the file list in sections 1.4 and 1.6 of ${list(p.plan)}. Plan files under ${PLANS}, the changelog and generated copies the epic names count as listed.
${RULES(p)}
Do not edit files. Return filesMatch (true when no file is extra or missing), extra (touched, not listed), missing (listed, not touched), notes.`

const LENSES = ['overall: does the evidence answer the question as asked', 'consistency: do the captures agree across every base and theme, with no base or theme off', 'refutation: look for the one capture that proves the answer wrong; pass only when none does']
const judgePrompt = (p, src, lens) => `You are a judge for ${p.id}. Question: ${p.judged.question}
Lens: ${lens}.
Captures: ${p.judged.captures === 'tracker' ? `the capture paths recorded in ${list(p.tracker)}` : list(p.judged.captures)}${src?.captures?.length ? `, plus ${list(src.captures)}` : ''}. Open every capture; read ${PROCESS_FILE} and ${PLANS}/decisions.md for the reference the question names.
Do not edit files. Your final text is a return value for a script. Return pass and lines (one line per capture or finding, file path first).`

const mergePrompt = (p, v) => `You are the merger for milestone ${p.id}. Verify is green on ${p.branch} (head ${v.head}).
${ROOT_RULES}
Steps, from ${ROOT}: fetch; check out ${INTEGRATION} and fast-forward it to origin; \`git merge --no-ff origin/${p.branch}\` with the subject \`merge: ${p.title} (${p.epic})\`; push; delete ${p.branch} local and remote. Set the "Status:" line of ${list(p.tracker)} to merged with the merge sha, commit those paths only ("docs(plan): milestone ${p.id} merged"), push. Never touch ${MIRROR}: it is fast-forwarded once, after the last feature column (process.md P1). A conflict: abort the merge, return mergeSha "" and the conflicting files in attention.
Return mergeSha, notes, attention.`

const gatePrompt = (sprint) => `You are the release check for this release: milestones ${sprint.merged.join(', ')} merged into ${INTEGRATION}. Run the check of ${RELEASE_EPIC} on ${INTEGRATION} in ${ROOT}, every base it names, ${SERIAL_GATES ? 'one base after another' : 'bases concurrently on separate ports'}. Captures go to the scratchpad the release epic names, never the repo.
${ROOT_RULES}
Record one line per check and base in the release milestone's tracker (command, commit, result), commit that path only, push. Return pass, perBase (base, pass, output excerpt), captures (paths), attention.`

const releasePrompt = (sprint) => `You are the releaser for this release: milestones ${sprint.merged.join(', ')} merged${sprint.stopped.length ? `; not shipped: ${sprint.stopped.map(r => `${r.milestone} (${r.status})`).join(', ')}` : ''}. Do the release steps of ${RELEASE_EPIC} from ${ROOT}, in its order (process.md P1, P3): fast-forward ${INTEGRATION} into ${MIRROR} once, open the PR ${MIRROR} into master with label ${RELEASE_LABEL} and auto-merge enabled, arm the background watcher on \`gh pr checks\`; pr.yml bumps the version onto the PR after green and the owner approves; never merge it yourself; after the merge watch release.yml and smoke the published package.
${ROOT_RULES}
Return version, tag, prs (URLs), runs (run URLs with result), smoke (result line), attention.`

async function build(p) {
  let build
  if (p.fileSets) {
    const lead = p.lead ? await agent(`${p.lead}\n${RULES(p)}`, { label: `lead:${p.id}`, phase: `Milestone ${p.id} build`, schema: BUILD_SCHEMA, model: 'opus' }) : null
    if (p.lead && (!lead || lead.blocked)) return blocked(p, lead?.blockedReason || 'lead returned no result', { build: lead })
    const from = lead?.head || BASE_SHA
    const builds = await parallel(p.fileSets.map(set => () => agent(`${buildPrompt(p, set.wt, set.branch)}\nWork ONLY in worktree ${set.wt} on branch ${set.branch}, cut from ${p.branch} at ${from}.\nYour file set (${set.label}), the only files you may change: ${set.files.join(', ')}. ${set.prompt}`, { label: `build:${p.id}:${set.label}`, phase: `Milestone ${p.id} build`, schema: BUILD_SCHEMA, model: 'opus' })))
    // Merge the sets that returned unblocked; mark the others in the result.
    const ready = p.fileSets.map((set, i) => ({ set, b: builds[i] })).filter(x => x.b && !x.b.blocked)
    const blockedSets = p.fileSets.map((set, i) => ({ set: set.label, reason: builds[i] ? builds[i].blockedReason || 'blocked' : 'no result' })).filter((_, i) => !builds[i] || builds[i].blocked)
    const done = builds.filter(Boolean)
    build = { blocked: false, blockedSets, head: lead?.head || BASE_SHA, commits: [...(lead?.commits || []), ...done.flatMap(b => b.commits || [])], notes: done.flatMap(b => b.notes || []), attention: [...done.flatMap(b => b.attention || []), ...blockedSets.map(x => `file set ${x.set} blocked: ${x.reason}`)] }
    if (!ready.length) return blocked(p, 'every file set blocked', { build })
    const labels = ready.map(x => x.set.branch).join(', ')
    const merge = await agent(`Merge each set branch into ${p.branch} in ${p.wt} in this order: ${labels}. Fast-forward or merge commit, no rebase. Push. Return head.\n${RULES(p)}`, { label: `merge:${p.id}`, phase: `Milestone ${p.id} build`, schema: BUILD_SCHEMA, model: 'opus' })
    if (!merge || merge.blocked) return blocked(p, merge?.blockedReason || 'merge returned no result', { build, merge })
    build.head = merge.head
    build.commits.push(...(merge.commits || []))
    build.notes.push(...(merge.notes || []))
    build.attention.push(...(merge.attention || []))
  } else {
    build = await agent(buildPrompt(p), { label: `build:${p.id}`, phase: `Milestone ${p.id} build`, schema: BUILD_SCHEMA, model: 'opus' })
  }
  if (!build || build.blocked) return blocked(p, build?.blockedReason || 'build returned no result', { build })
  return build
}

async function filesCheck(p, build) {
  const check = await agent(filesCheckPrompt(p, build), { label: `files-check:${p.id}`, phase: `Milestone ${p.id} review`, schema: FILES_CHECK_SCHEMA, model: 'opus' })
  if (!check) return blocked(p, 'files check returned no result', { build })
  if (!check.filesMatch) return { milestone: p.id, status: 'files-mismatch', build, check, attention: [...check.extra.map(f => `extra: ${f}`), ...check.missing.map(f => `missing: ${f}`)] }
  return { check }
}

// Nits and minors alone get no fixer: they come back as `deferred` and the stage passes.
async function reviewBounce(p, build) {
  let prior = null, review = null, fixes = [], deferred = [], reviewed = build.head
  for (let round = 1; round <= 2; round++) {
    review = await agent(reviewPrompt(p, round, prior), { label: `review:${p.id}:r${round}`, phase: `Milestone ${p.id} review`, effort: 'high', schema: REVIEW_SCHEMA, model: 'fable' })
    if (!review) break
    const findings = review.findings || []
    if (review.contradictsDecision) {
      return { milestone: p.id, status: 'needs-decision', build, review, fixes, attention: findings.map(f => `${f.file}: ${f.problem}`) }
    }
    const majors = findings.filter(f => f.severity === 'major')
    log(`milestone ${p.id} review round ${round}: ${findings.length} findings, ${majors.length} major`)
    if (findings.length === 0) break
    if (!majors.length) { deferred.push(...findings.map(f => `${f.severity} ${f.file}${f.line ? `:${f.line}` : ''}: ${f.problem} (fix: ${f.fix})`)); break }
    const fix = await agent(fixPrompt(p, findings), { label: `fix:${p.id}:r${round}`, phase: `Milestone ${p.id} review`, schema: BUILD_SCHEMA, model: 'opus' })
    fixes.push(fix)
    if (!fix || fix.blocked) return blocked(p, fix?.blockedReason || 'fix returned no result', { build, review, fixes })
    // head: the commit this round reviewed; the next round diffs from it to the fixer's head.
    prior = { findings, fixer: fix.notes, head: reviewed }
    reviewed = fix.head
    if (review.pass) break
  }
  let openMajors = review ? (review.findings || []).filter(f => f.severity === 'major') : []
  // Confirmation round: round 2 ended with a major and the round 2 fixer fixed it. One incremental
  // review of the fixer's commits decides; a major it still finds returns review-open.
  if (openMajors.length && fixes.length === 2 && prior) {
    const confirm = await agent(reviewPrompt(p, 3, prior), { label: `review:${p.id}:confirm`, phase: `Milestone ${p.id} review`, effort: 'high', schema: REVIEW_SCHEMA, model: 'fable' })
    if (confirm) { review = confirm; openMajors = (confirm.findings || []).filter(f => f.severity === 'major') }
    log(`milestone ${p.id} confirmation review: ${openMajors.length} major open`)
  }
  if (openMajors.length) {
    return { milestone: p.id, status: 'review-open', build, review, fixes, attention: openMajors.map(f => `${f.file}: ${f.problem}`) }
  }
  return { review, fixes, deferred }
}

const verify = (p) => agent(verifyPrompt(p), { label: `verify:${p.id}`, phase: `Milestone ${p.id} verify`, schema: VERIFY_SCHEMA, model: 'opus' })

// Judges inside the script: parallel fable agents with distinct lenses, majority decides.
async function judges(p, src) {
  const n = p.judgeCount || 3
  const verdicts = (await parallel(Array.from({ length: n }, (_, i) => () => agent(judgePrompt(p, src, LENSES[i % LENSES.length]), { label: `judge:${p.id}:${i + 1}`, phase: p.id === 'check' ? 'Round check' : `Milestone ${p.id} verify`, schema: JUDGE_SCHEMA, model: 'fable' })))).filter(Boolean)
  const pass = verdicts.filter(v => v.pass).length * 2 > n
  log(`${p.id} judges: ${verdicts.filter(v => v.pass).length} of ${n} pass`)
  return { pass, verdicts }
}

// Merges share one checkout (ROOT): they run one after another, in finishing order.
let mergeChain = Promise.resolve()
function merge(p, v) {
  const run = () => agent(mergePrompt(p, v), { label: `merge:${p.id}`, phase: `Milestone ${p.id} verify`, schema: MERGE_SCHEMA, model: 'opus' })
  return (mergeChain = mergeChain.then(run, run))
}

async function check(sprint) {
  const g = await agent(gatePrompt(sprint), { label: 'check', phase: 'Release check', schema: GATE_SCHEMA, model: 'opus' })
  if (!g) return { pass: false, perBase: [], captures: [], attention: ['check returned no result'] }
  if (GATE_JUDGED && RUN_JUDGES && g.pass) {
    g.judges = await judges({ id: 'check', judged: GATE_JUDGED, tracker: RELEASE_EPIC }, { captures: g.captures })
    g.pass = g.judges.pass
  }
  return g
}

const release = (sprint) => agent(releasePrompt(sprint), { label: 'release', phase: 'Release', schema: RELEASE_SCHEMA, model: 'opus' })

// One milestone: build, files check, review bounce (if asked), verify, judges (if asked), merge.
// Any stop result returns early; the other milestones continue.
async function runMilestone(p) {
  const b = await build(p)
  if (b.status) return b
  const check = RUN_FILES_CHECK ? await filesCheck(p, b) : {}
  if (check.status) return check
  const rv = RUN_REVIEW && p.review === 'fable' ? await reviewBounce(p, b) : { review: null, fixes: [], deferred: [] }
  if (rv.status) return rv
  const base = { milestone: p.id, blockedSets: b.blockedSets || [], build: b, check: check.check, review: rv.review, fixes: rv.fixes, deferred: rv.deferred }
  const v = RUN_VERIFY ? await verify(p) : null
  const attention = [...(b.attention || []), ...rv.fixes.flatMap(f => f?.attention || []), ...(v?.attention || [])]
  if (!v?.allPass) return { ...base, status: RUN_VERIFY ? 'failed' : 'built', verify: v, attention }
  const judged = p.judged && RUN_JUDGES ? await judges(p, v) : null
  if (judged && !judged.pass) return { ...base, status: 'judged-fail', verify: v, judged, attention }
  if (!RUN_MERGE) return { ...base, status: 'done', verify: v, judged, attention }
  const m = await merge(p, v)
  if (!m?.mergeSha) return { ...base, status: 'merge-failed', verify: v, judged, merged: m, attention: [...attention, ...(m?.attention || ['merge returned no result'])] }
  return { ...base, status: 'merged', verify: v, judged, merged: m, attention: [...attention, ...m.attention] }
}

// One milestone per script: a throw becomes a blocked result. Other milestones of the sprint run in their own scripts.
const milestone = MILESTONES[0] ? await runMilestone(MILESTONES[0]).catch(e => blocked(MILESTONES[0], `threw: ${e?.message || e}`)) : null
const ownOk = !milestone || ['merged', 'done'].includes(milestone.status)
// Release milestone only: check and release over the milestones sprints.md marks merged.
const sprint = { merged: MERGED_MILESTONES, stopped: STOPPED_MILESTONES }
const gateResult = RELEASE_MILESTONE && RUN_GATE && ownOk && sprint.merged.length ? await check(sprint) : null
const ship = RELEASE_MILESTONE && RUN_RELEASE && ownOk && sprint.merged.length && (!RUN_GATE || gateResult?.pass) && (!sprint.stopped.length || SHIP_PARTIAL)
const releaseResult = ship ? await release(sprint) : null
return { milestone, check: gateResult, release: releaseResult }
