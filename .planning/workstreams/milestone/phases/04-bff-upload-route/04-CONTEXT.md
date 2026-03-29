# Phase 4: BFF Upload Route - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Admin BFF correctly proxies media upload requests to image_backend. Creates POST /api/media/upload route that forwards to image_backend POST /api/v1/media/upload using imageBackendFetch() from Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key constraints from ROADMAP:
- Forward POST /api/media/upload to image_backend POST /api/v1/media/upload (not main backend)
- Strip product-specific fields (mediaType, role, sortOrder) before forwarding
- Response must return presignedUrl and storageObjectId from image_backend to browser

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
