"""Catalog management CLIs (operator-facing).

Houses ``python -m`` scripts that don't fit the request/response shape
of the FastAPI surface — initial Elasticsearch reindex, ad-hoc data
migrations, etc. Each module is self-contained: parses argv, builds a
short-lived Dishka container, runs to completion, exits.
"""
