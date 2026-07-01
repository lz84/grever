# -*- coding: utf-8 -*-
"""
Pydantic request/response models for goals exploration mode.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class SetGoalModeRequest(BaseModel):
    mode: str = Field(..., description="engineering|research")
    diversity: Optional[str] = Field(default='best', description="best|portfolio")
    portfolio_size: Optional[int] = Field(default=3, description="组合方案数量")
    optimization_target: Optional[str] = None
    convergence_threshold: Optional[float] = None
    max_rounds: Optional[int] = None

class StartIterationRequest(BaseModel):
    diversity: Optional[str] = Field(default=None, description="best|portfolio")
    initial_constraints: Optional[Dict[str, Any]] = None

class IterateRequest(BaseModel):
    diversity: Optional[str] = Field(default=None, description="best|portfolio")
    constraint_adjustments: Optional[Dict[str, Any]] = None