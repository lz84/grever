# -*- coding: utf-8 -*-
"""AgentScheme model for industry pack Agent方案 definitions."""

from sqlalchemy import Column, String, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class AgentScheme(Base):
    """Agent scheme belonging to an industry pack."""

    __tablename__ = "agent_schemes"

    id = Column(String, primary_key=True)
    pack_id = Column(
        String,
        ForeignKey("industry_packs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    roles = Column(Text, nullable=False, default="[]")
    created_at = Column(Integer, nullable=False)

    # Relationships
    pack = relationship("IndustryPack", back_populates="agent_schemes")
    role_entries = relationship(
        "AgentSchemeRole",
        back_populates="scheme",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AgentScheme {self.id} name={self.name!r}>"
