# -*- coding: utf-8 -*-
"""
Pydantic request/response models for goals exploration mode.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class SetGoalModeRequest(BaseModel):
    mode: str = Field(..., description="normal|exploration|optimization")
    optimization_target: Optional[str] = None
    convergence_threshold: Optional[float] = None
    max_rounds: Optional[int] = None

class StartIterationRequest(BaseModel):
    initial_constraints: Optional[Dict[str, Any]] = None

class IterateRequest(BaseModel):
    constraint_adjustments: Optional[Dict[str, Any]] = None