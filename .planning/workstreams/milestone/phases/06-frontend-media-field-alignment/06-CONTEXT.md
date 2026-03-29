# Phase 6: Frontend Media Field Alignment - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure/code-logic phase — discuss skipped)

<domain>
## Phase Boundary

Admin frontend uses correct field names and request schemas when communicating with image_backend via BFF. Fixes field name mismatches between what the frontend sends/reads and what the BFF proxy routes (from Phases 4+5) expect.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — code-logic phase fixing field name mismatches. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key constraints from ROADMAP:
- Frontend reads presignedUrl (not presignedUploadUrl) from upload response
- Frontend reads storageObjectId (not id) from upload response
- Frontend sends {contentType, filename} in upload request (not {mimeType, fileName, mediaType, role})

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — field alignment phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
