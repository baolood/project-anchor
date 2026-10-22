"""Offline Official Fake-Fill scoring helpers.

This package does not write a ledger, place an order, or read the ledger
StateDirectory. Callers pass an already-copied JSONL file. Public funding
is read from a hashed EXTERNAL_PUBLIC_FUNDING_V1 cache. This package does
not fetch that cache.
"""
