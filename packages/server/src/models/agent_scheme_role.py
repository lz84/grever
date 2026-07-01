# -*- coding: utf-8 -*-
"""AgentSchemeRole model for Agent role definitions within a scheme."""

from sqlalchemy import Column, String, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class AgentSchemeRole(Base):
    """Role definition within an Agent scheme."""

    __tablename__ = "agent_scheme_roles"

    id = Column(String, primary_key=True)
    scheme_id = Column(
        String,
        ForeignKey("agent_schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_name = Column(String, nullable=False)
    required_tags = Column(Text, nullable=False, default="[]")
    priority = Column(Integer, nullable=False, default=0)

    # Relationships
    scheme = relationship("AgentScheme", back_populates="role_entries")

    def __repr__(self) -> str:
        return f"<AgentSchemeRole {self.id} role={self.role_name!r}>"
