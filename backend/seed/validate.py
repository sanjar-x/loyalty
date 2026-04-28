"""Validate all seed JSON data for referential integrity."""

import json
import re
import sys
from collections import Counter
from pathlib import Path

root = Path(__file__).parent
brands = json.loads((root / "brands/brands.json").read_text(encoding="utf-8"))
categories = json.loads(
    (root / "categories/categories.json").read_text(encoding="utf-8")
)
attrs_data = json.loads(
    (root / "attributes/attributes.json").read_text(encoding="utf-8")
)

errors: list[str] = []
slug_re = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

brand_slugs = {b["slug"] for b in brands}
cat_slugs = {c["slug"] for c in categories}
cat_refs = {c["ref"] for c in categories if c.get("ref")}
attr_codes = {a["code"] for a in attrs_data["attributes"]}
attr_levels = {a["code"]: a.get("level", "product") for a in attrs_data["attributes"]}
value_codes: dict[str, set[str]] = {}
for a in attrs_data["attributes"]:
    value_codes[a["code"]] = {v["code"] for v in a.get("values", [])}

# 1. Brands
if len(brand_slugs) != len(brands):
    errors.append("brands: duplicate slugs")
if len({b["name"] for b in brands}) != len(brands):
    errors.append("brands: duplicate names")
for b in brands:
    if not slug_re.match(b["slug"]):
        errors.append(f"brands: invalid slug '{b['slug']}'")

# 2. Categories
ref_seen: set[str] = set()
for c in categories:
    if c.get("parentRef") and c["parentRef"] not in ref_seen:
        errors.append(
            f"categories: '{c['slug']}' parentRef '{c['parentRef']}' before ref"
        )
    if c.get("ref"):
        ref_seen.add(c["ref"])
    if len(c["slug"]) < 3:
        errors.append(f"categories: slug '{c['slug']}' < 3 chars")
    if not slug_re.match(c["slug"]):
        errors.append(f"categories: invalid slug '{c['slug']}'")
    i = c.get("nameI18N", {})
    if "ru" not in i or "en" not in i:
        errors.append(f"categories: '{c['slug']}' missing ru/en")
    if c.get("parentRef") and c["parentRef"] not in cat_refs:
        errors.append(f"categories: '{c['slug']}' parentRef '{c['parentRef']}' invalid")

for pr in list(cat_refs) + [None]:
    children = [
        c["slug"]
        for c in categories
        if c.get("parentRef") == pr or (pr is None and not c.get("parentRef"))
    ]
    dupes = [s for s, n in Counter(children).items() if n > 1]
    if dupes:
        errors.append(f"categories: duplicate slugs under '{pr}': {dupes}")

# 3. Attributes + values
for a in attrs_data["attributes"]:
    if not slug_re.match(a["slug"]):
        errors.append(f"attributes: invalid slug '{a['slug']}'")
    i = a.get("nameI18N", {})
    if "ru" not in i or "en" not in i:
        errors.append(f"attributes: '{a['code']}' missing ru/en nameI18N")
    if a.get("descriptionI18N"):
        d = a["descriptionI18N"]
        if "ru" not in d or "en" not in d:
            errors.append(f"attributes: '{a['code']}' missing ru/en descriptionI18N")
    sw = a.get("searchWeight", 5)
    if not 1 <= sw <= 10:
        errors.append(f"attributes: '{a['code']}' searchWeight {sw}")
    vcodes: set[str] = set()
    for v in a.get("values", []):
        if v["code"] in vcodes:
            errors.append(f"attributes: '{a['code']}' dup value code '{v['code']}'")
        vcodes.add(v["code"])
        vi = v.get("valueI18N", {})
        if "ru" not in vi or "en" not in vi:
            errors.append(f"attributes: '{a['code']}/{v['code']}' missing ru/en")

# 4. Templates + bindings
for t in attrs_data.get("templates", []):
    ti = t.get("nameI18N", {})
    if "ru" not in ti or "en" not in ti:
        errors.append(f"templates: '{t['code']}' missing ru/en")
    acs = t.get("assignToCategorySlug")
    if acs and acs not in cat_slugs:
        errors.append(f"templates: '{t['code']}' assignTo '{acs}' not in categories")
    seen_bindings: set[str] = set()
    for b in t.get("bindings", []):
        if b["attributeCode"] not in attr_codes:
            errors.append(
                f"templates: '{t['code']}' binding '{b['attributeCode']}' missing"
            )
        if b["attributeCode"] in seen_bindings:
            errors.append(
                f"templates: '{t['code']}' dup binding '{b['attributeCode']}'"
            )
        seen_bindings.add(b["attributeCode"])

# Report
print(
    "Brands:%d  Categories:%d  Attrs:%d  Values:%d  Templates:%d  Bindings:%d"
    % (
        len(brands),
        len(categories),
        len(attr_codes),
        sum(len(v) for v in value_codes.values()),
        len(attrs_data.get("templates", [])),
        sum(len(t.get("bindings", [])) for t in attrs_data.get("templates", [])),
    )
)

if errors:
    print(f"\nFAILED ({len(errors)} errors):")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("\nALL CHECKS PASSED")
