# -*- coding: utf-8 -*-
"""
Skill model for industry pack skill definitions.

A Skill represents a callable capability within an industry pack,
with input/output schemas and tag dependencies.
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Skill(Base):
    """Skill definition belonging to an industry pack."""

    __tablename__ = "skills"

    id = Column(String, primary_key=True)
    pack_id = Column(
        String,
        ForeignKey("industry_packs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    input_schema = Column(Text, nullable=False, default="{}")
    output_schema = Column(Text, nullable=False, default="{}")
    required_tags = Column(Text, nullable=False, default="[]")
    tool_dependency = Column(Text, nullable=True)
    created_at = Column(Integer, nullable=False, default=lambda: int(func.now().op("unix_timestamp")()))
    updated_at = Column(Integer, nullable=True)

    # Relationships
    pack = relationship("IndustryPack", back_populates="skills")

    def __repr__(self) -> str:
        return f"<Skill {self.id} name={self.name!r}>"
