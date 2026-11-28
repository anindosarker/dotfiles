---
status: to-do
decider: lead
source: Q17
---
# D14. The skill's own scripts build the dashboard data

- Settled by the lead: tooling with one answer. The owner's word on it (2026-11-28): no local server; the data is rebuilt by the commands, plus one refresh command for a hand edit.
- The Python scripts of the skill write `status/data/dashboard.data.js` and `status/data/dashboard.json`, in the same step that writes `status.data.js` and `queue.data.js`.
- The fields and the rules are those of the dashboard page's README, section Data (today `plans/sprint-swimlanes/status-board/v2.1-dashboard/README.md` in the React-table workspace). `turn` and `ready` are worked out at build time, not stored.
- The status words and `decider` come from D8, D9 and D11 as stored; the builder maps nothing. Where D11 and the README differ (a planned epic: turn `you`), D11 holds.
- The Node script `src/build.js` of the page folder is not copied into the skill. The skill needs no Node.
- The copy of the page itself is Q8 and is not part of this decision.
