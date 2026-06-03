"""
app/models/jes_factor.py — JESFactor re-export shim.

The JESFactor class is defined in app.models.classification because it
only makes sense as part of a Classification. This file re-exports it
so callers can do `from app.models.jes_factor import JESFactor` if they
prefer a dedicated import path.
"""
from .classification import JESFactor

__all__ = ["JESFactor"]
