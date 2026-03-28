# Phase 4: Brand, Category & Attribute Command Handlers - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove all command handlers for Brand, Category, and Attribute entities orchestrate correctly — calling the right repositories, enforcing preconditions, committing through UoW. This phase tests the APPLICATION layer (command handlers), not the domain layer (Phase 2-3) or infrastructure layer (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### Handler Test Granularity
- **D-01:** One test CLASS per handler: TestCreateBrand, TestUpdateBrand, TestDeleteBrand, etc. Each handler is a separate use case with its own inputs, validations, and side effects — they deserve isolated test classes.
- **D-02:** One test FILE per entity domain: `test_brand_handlers.py`, `test_category_handlers.py`, `test_attribute_handlers.py`. Classes are per-handler inside the file.

### Mock Strategy
- **D-03:** FakeUoW (from Phase 1) for ALL handlers, no exceptions. No simple AsyncMock even for "trivial" CRUD handlers. FakeUoW validates real repository interactions (adds, commits, event collection). Consistency over convenience — every handler test follows the same pattern.
- **D-04:** Per-test inline AsyncMock (Phase 1 D-11) only for cross-module dependencies (e.g., ILogger, external services), NOT for repositories or UoW.

### Test Patterns (from prior phases)
- **D-05:** Use Phase 1 builders (BrandBuilder, CategoryBuilder, AttributeBuilder, etc.) for test data.
- **D-06:** Test both happy path AND rejection paths for every handler.
- **D-07:** Verify UoW.commit() called on success, NOT called on validation failure.
- **D-08:** Verify domain events collected by FakeUoW on relevant operations.

### Claude's Discretion
- Number of edge cases per handler
- Whether to test ILogger interactions (bind, info, warning calls)
- Exact error message assertions vs exception type assertions
- Test method naming style within each class

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Command handlers (source of truth for what to test)
- `backend/src/modules/catalog/application/commands/` — All Brand, Category, Attribute command handler files
- `backend/src/modules/catalog/domain/interfaces.py` — Repository interfaces (what FakeUoW repos implement)
- `backend/src/modules/catalog/domain/exceptions.py` — Domain exceptions handlers should raise

### Test infrastructure (built in Phase 1)
- `backend/tests/fakes/fake_uow.py` — FakeUnitOfWork implementation
- `backend/tests/fakes/fake_catalog_repos.py` — All 10 fake catalog repositories
- `backend/tests/factories/brand_builder.py` — BrandBuilder
- `backend/tests/factories/attribute_builder.py` — AttributeBuilder, AttributeValueBuilder
- `backend/tests/factories/attribute_template_builder.py` — AttributeTemplateBuilder

### Existing handler test patterns
- `backend/tests/unit/modules/user/application/commands/test_commands.py` — Existing handler test pattern with make_uow()
- `backend/tests/unit/modules/catalog/application/commands/test_create_brand.py` — May exist from prior work

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- FakeUnitOfWork + 10 fake repos from Phase 1 — primary test doubles
- All entity builders — test data construction
- `make_logger()` pattern from identity tests — ILogger mock

### Established Patterns
- Command handlers follow: construct Command dataclass → call handler.handle(command) → verify repo state + UoW commit
- All handlers use constructor injection via Dishka (repos, UoW, logger)
- Validation: handlers check FK existence, slug uniqueness, business rules before entity creation
- Error handling: raise domain exceptions (NotFoundError, ConflictError, etc.) — UoW NOT committed

### Integration Points
- New test files go under `backend/tests/unit/modules/catalog/application/commands/`
- Tests import handlers from `src.modules.catalog.application.commands.*`
- Tests use FakeUoW from `tests.fakes.fake_uow`
- Tests use builders from `tests.factories.*_builder`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User wants FakeUoW-first consistency and per-handler test classes for maximum clarity.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-brand-category-attribute-command-handlers*
*Context gathered: 2026-03-28*
