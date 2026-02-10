"""
Re-export Action protocol for backward compatibility.
Prefer: from app.actions.protocol import Action, ActionOutput
"""
from app.actions.protocol import Action, ActionOutput

__all__ = ["Action", "ActionOutput"]
