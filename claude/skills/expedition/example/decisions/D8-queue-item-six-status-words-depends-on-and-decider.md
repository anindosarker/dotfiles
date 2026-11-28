---
status: to-do
decider: you
source: Q16
---
# D8. Queue item: six status words, depends_on and decider

| Today | New | Decider |
|---|---|---|
| `open` | `to-do` | |
| | `blocked`: waits for an item that is not `done` | |
| `decided` | `done` | `you` or `lead` |
| `autofix` | `done` | `agent` |
| `later` | `backlog` | |
| `dropped` | `archived` | `you` or `lead` |

- `in progress`: not used.
- `depends_on`: the ids the item waits for.
	- `queue/item.py <release> --depends Q8 "Q14, Q15"`
	- The script sets `blocked`, and `to-do` again when all are `done`.
- `decider`: written when the item is closed. No default: the command refuses without it.
- Not changed: the commands, the owner's words.
- Needs a migration.
