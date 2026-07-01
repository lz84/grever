# -*- coding: utf-8 -*-
"""Knowledge Entry model — alias for the knowledge_base table.

Sprint 75 Phase 2 Task 2.2
Maps to the 'knowledge_base' table in the database.
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class KnowledgeEntry(Base):
    """Knowledge base entry belonging to an industry pack.

    Alias: KnowledgeBase (defined in knowledge_base.py)
    Table: knowledge_base
    """

    __tablename__ = "knowledge_base"

    id = Column(String, primary_key=True)
    pack_id = Column(
        String,
        ForeignKey("industry_packs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    category = Column(String, nullable=False, default="general", index=True)
    content = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    version = Column(String, nullable=False, default="1.0.0")
    tags = Column(Text, nullable=False, default="[]")
    created_at = Column(Integer, nullable=False)

    # Relationships
    pack = relationship("IndustryPack", back_populates="knowledge_entries")

    def __repr__(self) -> str:
        return f"<KnowledgeEntry {self.id} name={self.name!r}>"
