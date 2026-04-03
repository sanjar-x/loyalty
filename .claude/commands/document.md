Create or update a project document (BRD/FRD/TRD/ADR/SPEC) in the Obsidian Knowledge vault.

## Instructions

The user wants to create/update: $ARGUMENTS

1. **Detect current component** — check working directory against Component Identity Map in root CLAUDE.md.
2. Parse the argument to determine:
   - **Document type**: brd, frd, trd, adr, spec (from the first word or context)
   - **Topic/scope**: what the document covers
3. Include `component: {component-id}` in frontmatter and component tag in tags array.

### For BRD (Business Requirements)

File: `/home/sanjar/Desktop/Knowledge/Projects/loyality/Loyality BRD.md` (update existing) or new section.

```markdown
---
tags: [project/loyality, {component-id}]
type: brd
date: {TODAY}
status: draft
project: "[[Loyality Project]]"
component: {component-id}
---
```

Sections: Executive Summary, Business Objectives, Scope (In/Out), Stakeholders, Success Criteria, Constraints & Assumptions, Timeline, Related.

### For FRD (Functional Requirements)

File: `/home/sanjar/Desktop/Knowledge/Projects/loyality/Loyality FRD.md` (update existing) or new section.

Add new FR-{NNN} blocks with: Priority (Must/Should/Could Have), Source (link to BRD), Description, Endpoints, Acceptance Criteria (checkboxes).

### For TRD (Technical Requirements)

File: `/home/sanjar/Desktop/Knowledge/Projects/loyality/Loyality TRD.md` (update existing).

Sections: Architecture (with Mermaid diagrams), Components table, Tech Stack table, API Design, Data Model, NFR, Security, Deployment, Risks.

### For ADR (Architecture Decision Record)

**Scope routing:**
- Cross-cutting (auth, infrastructure, project architecture) → `/home/sanjar/Desktop/Knowledge/Projects/loyality/ADR-{NNN} {Title}.md`
- Component-specific → `/home/sanjar/Desktop/Knowledge/Projects/loyality/{component-id}/ADR-{NNN} {Title}.md`

Determine the next ADR number by checking existing ADRs across all folders.

```markdown
---
tags: [project/loyality]
type: adr
date: {TODAY}
status: proposed
project: "[[Loyality Project]]"
parent: "[[Loyality TRD]]"
superseded_by: ""
---

# ADR-{NNN} {Title}

## Context
{Why this decision is needed — constraints, requirements, forces}

## Options
1. **Option A** — {description, pros, cons}
2. **Option B** — {description, pros, cons}

## Decision
{What was decided and why}

## Consequences
### Positive
### Negative
### Risks
```

### For SPEC (Specification)

File: `/home/sanjar/Desktop/Knowledge/Projects/loyality/SPEC - {Topic}.md` (new file).

Detailed technical design: API contracts, data models (with SQL), sequence diagrams (Mermaid), edge cases, error handling.

## After creating/updating

1. Update the Documents table in `[[Loyality Project]]` dashboard
2. Add cross-links in Related sections of referenced documents
3. Report what was created/changed to the user

## Rules
- Read the EXISTING document first if updating — preserve existing content, add/modify sections
- Russian text, English technical terms
- [[wikilinks]] for all internal references
- Mermaid for diagrams, tables for structured data
- Reference actual code paths from the repository
- Link to related ADRs, other project docs
