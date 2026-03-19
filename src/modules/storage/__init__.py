"""Storage bounded-context module.

Centralised registry of all files stored in the S3-compatible object
storage.  Provides domain entities, repository contracts, infrastructure
implementations (S3 service, ORM models), background event consumers,
and a facade for cross-module interaction.
"""
