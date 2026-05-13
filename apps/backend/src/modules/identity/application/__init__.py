"""Application layer of the Identity module.

Orchestrates domain logic via CQRS command handlers (writes) and query handlers
(reads). Depends only on domain interfaces; infrastructure is injected at runtime.
"""
