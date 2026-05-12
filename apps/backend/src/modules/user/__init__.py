"""User bounded context module.

Manages user profile data (PII) separately from authentication concerns.
The User aggregate shares a primary key with the Identity aggregate via
a 1:1 relationship, enabling GDPR-compliant data isolation.
"""
