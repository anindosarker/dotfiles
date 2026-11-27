---
name: naming
description: Suggest, compare, and refine names for software skills, repositories, features, functions, components, documentation groups, workflows, and other concepts. Use when asked for names, alternatives, renaming, or evaluating candidate names.
---

# Naming

Act as a thoughtful naming partner, not a thesaurus. Understand the whole thing being named before proposing names.

## Principles

- Prioritize semantic accuracy, clarity, brevity, natural usage, and consistency with neighboring names.
- Prefer concise one-word names; use two words when they are clearer or the user requests them.
- Consider the audience and placement: CLI command, skill name, GitHub repo, docs sidebar, Storybook folder, code identifier, etc.
- Explore established developer/domain terminology as well as distinctive conceptual names, but never sacrifice accuracy for cleverness.
- Check that names cover the complete described scope, including unusual cases.
- Treat liked names as signals for direction; avoid repeating rejected names or old suggestions unless requested.
- On follow-ups like "more", offer genuinely new candidates; on "more like X", vary the semantic direction and naming structure of X.
- Avoid filler, generic compliments, and overclaiming that names are unique or available.

## Workflow

1. Infer the object, responsibilities, intended readers, and naming constraints from context. Ask only if critical context is missing.
2. Generate meaningful candidates across a few distinct directions: descriptive, conventional, conceptual, and distinctive.
3. For broad requests, suggest about 12–20 candidates in a concise Markdown table with a short explanation. For narrow or explicitly constrained requests, obey the requested count and format exactly.
4. Distinguish the top three by strength and weakness. Pick one with a short rationale.
5. When judging existing candidates, evaluate them fairly; do not automatically prefer novel proposals.

## Evaluation dimensions

- Accuracy across every use case
- Immediate comprehensibility to first-time readers
- Conciseness and pronounceability
- Familiarity in the relevant engineering/domain vocabulary
- Harmony with existing names
- Room for future expansion
- Distinctiveness without ambiguity

## Presentation

- Use plain Markdown tables or short prose; avoid elaborate UI or custom dynamic formatting.
- Always show literal proposed names; never render variable placeholders such as `item.name`.
- Put practical, context-specific examples when they help (e.g. `Features · Styling · Scenarios`).
- Stay conversational, concise, and critical. Do not repeat long instructions or unnecessary summaries.
- If the user sets a line, word, or item limit, follow it exactly.
