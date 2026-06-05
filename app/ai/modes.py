"""
AI modes used to shape prompt behavior.
"""

from enum import Enum


class AIMode(str, Enum):
    """Supported AI assistant modes."""

    NORMAL = "normal"
    BUDGET = "budget"
    DIET = "diet"
    INVENTORY = "inventory"
    WEEKLY = "weekly"

