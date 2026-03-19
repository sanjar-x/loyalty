"""Aiogram middleware chain.

Registration order (configured in ``factory.py``):

1. ``LoggingMiddleware``      — outer, logs every update with timing
2. ``UserIdentifyMiddleware`` — outer, extracts telegram_user + locale
3. ``ThrottlingMiddleware``   — message-level, anti-flood per user
"""
