"""CQRS query handlers for the Identity module (application layer).

Each sub-module defines a read-optimized query handler that executes raw SQL
against the database, bypassing the domain layer for performance (CQRS read side).
"""
