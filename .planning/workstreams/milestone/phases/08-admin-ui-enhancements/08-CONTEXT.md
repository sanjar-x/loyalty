# Phase 8: Admin UI Enhancements - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped — success criteria fully specified)

<domain>
## Phase Boundary

Admin product form uses completeness endpoint, supports all FSM transitions, and sends version for optimistic locking. Three distinct enhancements to the product management admin UI.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion. Use ROADMAP success criteria and codebase patterns.

Key constraints from ROADMAP:
- Completeness endpoint: display missing required/recommended attributes
- FSM UI: show all 5 valid transitions, disable invalid ones based on current status
- Optimistic locking: all PATCH requests include version field from last-fetched product

FSM transitions (from product-creation-flow.md):
- DRAFT → ENRICHING
- ENRICHING → DRAFT, READY_FOR_REVIEW
- READY_FOR_REVIEW → ENRICHING, PUBLISHED
- PUBLISHED → ARCHIVED
- ARCHIVED → DRAFT

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — implementation details at Claude's discretion.

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
