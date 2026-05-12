"""CQRS command handlers for the Identity module (application layer).

Each sub-module defines a frozen dataclass command, an optional result, and a
handler that orchestrates domain logic within a Unit of Work transaction.
"""
