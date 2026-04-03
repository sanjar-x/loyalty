Synchronize current project state to the Obsidian Knowledge vault. Review what changed and update all relevant vault documents.

## Instructions

1. **Assess what changed** — check git status, recent commits, and current conversation context to understand what work was done.

2. **Update project documents as needed:**

   For each area of change, update the corresponding vault document:

   | What changed                | Update in vault                                     |
   | --------------------------- | --------------------------------------------------- |
   | New module/feature designed | Add FR in [[Loyality FRD]], update [[Loyality TRD]] |
   | Architecture decision made  | Create new ADR-{NNN}                                |
   | Bug/issue discovered        | Add to Known Issues in [[Loyality Project]]         |
   | API endpoints added/changed | Update API section in [[Loyality TRD]]              |
   | Data model changed          | Update Data Model in [[Loyality TRD]]               |
   | Research completed          | Should already be saved via /research               |
   | Sprint work completed       | Update sprint note or create new one                |
   | Tech stack changed          | Update Tech Stack table in [[Loyality TRD]]         |

3. **Update Loyality Project.md dashboard:**
   - Verify Documents table is current
   - Update Known Issues if resolved
   - Check all wikilinks resolve

4. **Report changes** — list what was updated in the vault.

## Rules
- Read each vault file before updating — preserve existing content
- Only update what actually changed — don't rewrite unchanged sections
- Russian text, English technical terms
- [[wikilinks]] for all internal references
- Verify frontmatter is valid after edits
