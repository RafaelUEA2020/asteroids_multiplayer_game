"""Player color palette for local co-op.

Each player gets a distinct color used for:
- Ship polygon
- Bullets
- HUD labels
- Invulnerability ring
"""

from typing import Tuple

Color = Tuple[int, int, int]

# Index 0 is unused (player ids start at 1)
PLAYER_COLORS: dict[int, Color] = {
    1: (240, 240, 240),   # White  — classic Asteroids feel
    2: (80,  200, 255),   # Cyan
    3: (255, 100,  80),   # Orange-red
    4: (120, 255, 120),   # Green
    5: (255, 220,  50),   # Yellow
    6: (200, 100, 255),   # Purple
    7: (255, 160, 200),   # Pink
    8: (100, 230, 200),   # Teal
}

FALLBACK_COLOR: Color = (200, 200, 200)


def player_color(player_id: int) -> Color:
    return PLAYER_COLORS.get(player_id, FALLBACK_COLOR)