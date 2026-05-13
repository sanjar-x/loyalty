"""Anti-corruption infrastructure adapters bridging logistics to other modules.

These adapters translate ORM rows from other bounded contexts (catalog,
pricing) into pure logistics value objects. Cross-module ORM access is
restricted to this package and explicitly whitelisted in
``tests/architecture/test_boundaries.py``.
"""
