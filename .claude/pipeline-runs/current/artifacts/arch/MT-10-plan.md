# MT-10 Architecture Plan (Simple — Application Layer)

**Type:** Simple (Application layer — no architect needed per CLAUDE.md)
**Decision:** Main agent delegates directly to senior-backend. This MT involves pure domain/application logic with no DI, migrations, or library API integration.

**Implementation:** Follow pm-spec.md MT-10 section exactly. Follow existing handler patterns in the codebase.
