"""Media full-replace diff logic for product create/update."""

from __future__ import annotations


def compute_media_diff(
    current: list[dict],
    incoming: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Full-replace diff for media arrays.

    Both current and incoming are lists of dicts with at minimum:
    - storage_object_id (str UUID or None)
    - role, sort_order, variant_id (for change detection)
    - is_external, url (for external URL matching)
    - id (only in current, for identifying existing records)

    Returns: (to_add, to_update, to_delete)
    """
    current_by_sid = {
        c["storage_object_id"]: c
        for c in current
        if c.get("storage_object_id") and not c.get("is_external")
    }
    incoming_by_sid = {
        i["storage_object_id"]: i
        for i in incoming
        if i.get("storage_object_id") and not i.get("is_external")
    }

    to_add = [i for sid, i in incoming_by_sid.items() if sid not in current_by_sid]
    to_delete = [c for sid, c in current_by_sid.items() if sid not in incoming_by_sid]
    to_update = []
    for sid in incoming_by_sid:
        if sid in current_by_sid:
            inc = incoming_by_sid[sid]
            cur = current_by_sid[sid]
            if any(
                inc.get(k) != cur.get(k) for k in ("role", "sort_order", "variant_id")
            ):
                to_update.append({**cur, **inc, "id": cur.get("id")})

    # Handle external URLs (no storage_object_id)
    current_external = {
        c["url"]: c
        for c in current
        if c.get("is_external") and not c.get("storage_object_id") and c.get("url") is not None
    }
    incoming_external = {
        i["url"]: i
        for i in incoming
        if i.get("is_external") and not i.get("storage_object_id") and i.get("url") is not None
    }
    to_add.extend(
        i for url, i in incoming_external.items() if url not in current_external
    )
    to_delete.extend(
        c for url, c in current_external.items() if url not in incoming_external
    )

    return to_add, to_update, to_delete
