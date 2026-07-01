# -*- coding: utf-8 -*-
"""KnowledgeBase — alias for KnowledgeEntry (knowledge.py).

Provides backward compatibility; the authoritative model is KnowledgeEntry.
Both map to the 'knowledge_base' table.
"""

from .knowledge import KnowledgeEntry

# Backward-compatibility alias: existing code may import KnowledgeBase
KnowledgeBase = KnowledgeEntry

__all__ = ["KnowledgeBase"]
