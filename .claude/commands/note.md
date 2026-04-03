Save a reusable knowledge note to the Obsidian vault (Notes/ folder — not project-specific).

## Instructions

The user wants to save knowledge about: $ARGUMENTS

This is for **reusable concepts** that apply beyond this project — patterns, technologies, techniques, learnings.

1. **Check if a note already exists** — search `/home/sanjar/Desktop/Knowledge/Notes/` for similar topics. If found, UPDATE the existing note instead of creating a duplicate.

2. **Create/update at `/home/sanjar/Desktop/Knowledge/Notes/{Concept Name}.md`:**

```markdown
---
tags: [{relevant-flat-tags}]
type: note
date: {TODAY YYYY-MM-DD}
status: active
---

# {Concept Name}

{Self-contained opening paragraph — the note is understandable without any external context. Explain what this is and why it matters.}

## {Organized sections}

{Content with code examples, diagrams, tables as needed.}

## Related

- {[[wikilinks]] to other Notes/ that connect to this concept}
- {[[wikilinks]] to project docs if relevant}
```

3. **Link from relevant MOCs** — if there's an existing MOC (Map of Content) in the vault root that covers this topic area, add a link to the new note there.

4. **Link from project docs** — if this note was discovered during project work, add a link from the relevant project document.

## Rules
- Tags: flat, lowercase, no project/ prefix (these are reusable notes): `#docker`, `#postgresql`, `#cqrs`, `#auth`
- NO `project:` field in frontmatter — this is project-independent knowledge
- Minimum 3 outgoing [[wikilinks]]
- Self-contained opening paragraph
- One concept per note (atomic notes)
- Russian text, English technical terms
- Code blocks with language tags
