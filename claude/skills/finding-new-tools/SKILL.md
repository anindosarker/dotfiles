---
name: finding-new-tools
description: Finds new and trending tools, repos, apps and libraries from GitHub, Product Hunt, BetaList, Reddit, Hacker News, Lobsters, dev.to, npm, Hugging Face and more. Use when the user asks for cool, new, trending, underrated or lesser-known tools, alternatives, libraries or projects for a topic, or "what's out there" / "anything new for X", or when ordinary web search would only return well-known basic answers.
---

# Finding new tools

Speed first: one script run plus parallel searches, then answer. Target under 15 s. No planning step.

## 1. Pick keywords

Take 1-4 keywords from the request, most specific first (`mcp server`, `self-hosted notes`, `screen recorder`).
Drop filler like "cool", "new", "best", "alternative". For "alternatives to X", search for what X does (Loom -> `screen recorder`), not only the name X.

## 2. One parallel turn

In a single tool-call turn, send all of these together:

- `python3 ~/.claude/skills/finding-new-tools/scripts/scout.py "<keywords>"`
  (options: `--days 30`, `--top 15`, `--json`, `--only github,hn_show`, `--feed <rss/atom/json url>`)
- 1-3 WebSearch queries aimed at niche sources the script does not cover. Pick freely, for example:

| Topic | Good niche sources |
|---|---|
| dev tools, CLIs | news.ycombinator.com "Show HN", dev.to, console.dev |
| self-hosted | r/selfhosted, awesome-selfhosted, selfh.st |
| design, no-code, SaaS | alternativeto.net, uneed.best, saashub.com |
| AI, LLM, agents | huggingface.co/spaces, r/LocalLLaMA, mcp.so, glama.ai |
| Mac apps | r/macapps, macmenubar.com |
| open-source alternatives | opensourcealternative.to, r/opensource |

Add the current month and year to searches ("2026") so results are fresh.

## 3. Answer directly

- Table of 8-12 rows: **Name | What it is | Cost | Signal + date | Link**. Signal is stars, points, likes or downloads from the script line. Cost is `FOSS`, `Free` or `Paid`.
- Order: FOSS first, then Free, then at most 2-3 Paid rows at the end. Take cost from the search snippet or repo (a GitHub repo with a license = FOSS); write `?` if unknown, never guess.
- Judge fit against the user's real criterion, not just the keyword match.
- Then a short "Also seen" line with a few extra names.
- Prefer new and rising over famous. Skip items the user surely knows.
- No per-item verification fetches. Trust the script lines and search snippets.
- Only if the script prints 0 items and searches are thin: retry once with one broader keyword.

Script output: a header (sources hit/skipped, elapsed), then one line per item:
`[source] title | desc | signal (412★ 6d) | url`. `[a+b]` means both sources found it. Stderr `skipped: <name> (<reason>)` lines are normal; ignore them.

## 4. Growing the sources

If a site found through WebSearch gave good results and has an RSS, Atom or JSON feed, propose a new entry for `sources.json`. Show the entry, and write it only after the user approves. Example:

```json
{"name": "selfhst", "type": "rss", "url": "https://selfh.st/rss/", "keyword": "local"}
```

The schema is documented in the `_schema` block at the top of `sources.json` (types, `{q}` / `{tag}` / `{since_date}` / `{since_ts}` placeholders, field paths, `keyword: server|local`, `topics`, `weight`). Ranking and timeout constants are documented at the top of `scripts/scout.py`.

## Known limits

- Reddit allows about one unauthenticated request per minute; back-to-back runs skip it.
- Hugging Face runs only for AI/ML keywords and npm only for dev keywords (see `topics`).
- npm keeps only packages first published within `--days` (signal `new 9d, 1.2kdl/wk`). It checks the creation date of at most 20 likely-new search hits, so it often returns few or no rows, and well-known packages never show.
- Product Hunt, BetaList, Lobsters and GitHub trending are fixed feeds filtered locally, so niche keywords often match nothing there. That is expected.
