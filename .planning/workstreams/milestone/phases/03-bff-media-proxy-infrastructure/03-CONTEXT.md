# Phase 3: BFF Media Proxy Infrastructure - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Admin BFF has a working HTTP client for image_backend with correct auth and error handling. This creates the foundational `imageBackendFetch()` utility that Phase 4 (upload route) and Phase 5 (confirm/external routes) depend on.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key constraints from ROADMAP:
- Auth: X-API-Key header (NOT JWT Bearer) targeting IMAGE_BACKEND_URL
- Error handling: structured error (502) when image_backend unreachable
- Env vars: IMAGE_BACKEND_URL and IMAGE_BACKEND_API_KEY as server-only (not NEXT_PUBLIC_)

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
