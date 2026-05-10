"""Downed/rescue state for a single player."""

from dataclasses import dataclass


@dataclass
class DownedState:
    player_id: int
    timer: float                   # counts down to 0 → definitive death
    rescue_progress: float = 0.0  # 0.0 → 1.0
    rescuer_id: int | None = None