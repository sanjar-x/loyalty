Research a topic for the loyality project and save findings to the Obsidian Knowledge vault.

## Instructions

The user wants to research: $ARGUMENTS

1. **Detect current component** — check your working directory against the Component Identity Map in the root CLAUDE.md. Determine the component ID (backend, image-backend, frontend-main, frontend-admin, or project).

2. **Research the topic thoroughly:**
   - Read relevant code in this repository (grep for related modules, schemas, routes, models)
   - If working in a sub-component, also check other components for cross-service concerns
   - Read existing vault notes that may be related (check `Projects/loyality/` and `Notes/`)
   - If needed, search the web for best practices, patterns, and prior art

3. **Create a research note:**
   - If component-specific → `/home/sanjar/Desktop/Knowledge/Projects/loyality/{component-id}/Research - {Topic}.md`
   - If cross-cutting (spans multiple components) → `/home/sanjar/Desktop/Knowledge/Projects/loyality/Research - {Topic}.md`

   ```markdown
   ---
   tags: [project/loyality, {component-id}]
   type: research
   date: {TODAY YYYY-MM-DD}
   status: active
   project: "[[Loyality Project]]"
   component: {component-id}
   ---

   # Research - {Topic}

   {Self-contained opening paragraph explaining what was researched and why.}

   ## Context

   **Component:** {component name} (`{path/}`)
   **Trigger:** {Why this research was initiated}

   ## Current State

   {What exists now in the codebase — modules, files, schemas, endpoints. Reference actual code paths relative to the component.}

   ## Findings

   {Main research results, organized by sub-topic. Use tables, Mermaid diagrams, code blocks.}

   ## Cross-Service Impact

   {How this affects other components — API contracts, shared types, data flow. Skip if not applicable.}

   ## Recommendations

   {Concrete, actionable recommendations based on findings.}

   ## Open Questions

   - {Questions that need clarification or further research}

   ## Related

   - [[Loyality Project]]
   - [[Loyality TRD]] (if architectural)
   - [[Loyality FRD]] (if functional)
   - {Links to relevant ADRs and existing vault notes}
   ```

4. **Update vault:**
   - Add to Documents table in `[[Loyality Project]]` if it's a new document
   - If findings warrant FRD/TRD updates, mention that in Recommendations

5. **Report to user** — summarize key findings and confirm the note was saved.

## Rules
- Russian text, English technical terms
- [[wikilinks]] for all internal vault references
- Mermaid diagrams for architecture/flow
- Reference actual file paths (verify by reading first — do NOT hallucinate)
- Self-contained opening paragraph
- Always include component tag in frontmatter
