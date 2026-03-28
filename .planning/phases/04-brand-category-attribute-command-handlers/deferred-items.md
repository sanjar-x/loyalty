# Deferred Items -- Phase 04

## Pre-existing Test Failures

1. **test_image_backend_client.py::test_delete_sends_correct_request**
   - File: `backend/tests/unit/modules/catalog/infrastructure/test_image_backend_client.py`
   - Issue: KeyError on `call_args[1]["headers"]` -- mock patching of `httpx.AsyncClient.delete` does not capture keyword args properly
   - Root cause: Pre-existing, not caused by Phase 04 changes
   - Impact: 1 test failure in isolation, does not affect brand/category/attribute handler tests
