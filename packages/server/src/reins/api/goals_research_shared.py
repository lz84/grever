# -*- coding: utf-8 -*-
"""Goals Exploration — shared setup."""
import uuid, logging, re, json
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from reins.common.database import get_db

router = __import__("fastapi").APIRouter(prefix="/api/v1", tags=["goals"])

class _ExplorationState:
    def __init__(self, goal_id: str, direction: str = "both"):
        self.goal_id = goal_id
        self.direction = direction
        self.started_at = datetime.utcnow()
        self.rounds = 0

    def to_dict(self):
        return {
            "goal_id": self.goal_id,
            "direction": self.direction,
            "started_at": self.started_at.isoformat(),
            "rounds": self.rounds,
        }

_EXPLORATION_SYSTEM_PROMPT = """You are an expert scenario planner. Given a goal and context, generate diverse scenario configurations to explore."""
