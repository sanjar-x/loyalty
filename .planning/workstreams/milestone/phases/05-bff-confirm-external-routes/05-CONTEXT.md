# Phase 5: BFF Confirm & External Routes - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Admin BFF correctly proxies media confirm and external import requests to image_backend. Creates two routes using imageBackendFetch() from Phase 3: confirm route and external import route.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key constraints from ROADMAP:
- POST /api/media/{id}/confirm forwards to image_backend POST /api/v1/media/{id}/confirm
- POST /api/media/external forwards to image_backend POST /api/v1/media/external
- Both routes use imageBackendFetch() with X-API-Key auth (not backendFetch with JWT)

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
