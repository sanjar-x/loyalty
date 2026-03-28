# Deferred Items -- Phase 02

## Pre-existing Test Failures

1. **test_category_effective_family.py::TestCategoryEffectiveTemplateId::test_update_clear_template_id_does_not_clear_effective**
   - Discovered during: 02-03 overall verification
   - Issue: Category.update() clears effective_template_id when template_id is set to None, but the test expects effective_template_id to be retained from a previous force-set
   - Impact: Pre-existing; not caused by 02-03 changes
   - Action: Should be investigated during Category entity testing phase

## Source Code Gaps

2. **AttributeGroup.create() does not validate code via _validate_slug**
   - Discovered during: 02-03 Task 1
   - Issue: Plan interface said code is validated via _validate_slug but source does not call it
   - Impact: Invalid codes (spaces, uppercase) are accepted for AttributeGroup
   - Action: Consider adding _validate_slug(code, "AttributeGroup") in entities.py

3. **AttributeTemplate.create() does not validate code via _validate_slug**
   - Discovered during: 02-03 Task 2
   - Issue: Same as above -- code is not validated at creation time
   - Action: Consider adding _validate_slug(code, "AttributeTemplate") in entities.py

4. **Attribute.create() does not validate code parameter**
   - Discovered during: 02-03 Task 1
   - Issue: Only slug is validated via _validate_slug, not code. Plan stated both were validated.
   - Action: Consider adding _validate_slug(code, "Attribute") for code parameter
