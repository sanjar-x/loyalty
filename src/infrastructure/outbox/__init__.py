"""Transactional outbox infrastructure package.

Implements the Polling Publisher pattern: the relay polls unprocessed
outbox rows and dispatches domain events to the message broker.
"""
