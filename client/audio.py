"""Game audio (client-side).

- World does not play sounds (low coupling).
- World generates events (strings) and Game decides what to play.
"""

from dataclasses import dataclass
from pathlib import Path

import pygame as pg
from core import config as C


@dataclass(slots=True)
class SoundPack:
    player_shoot: pg.mixer.Sound
    ufo_shoot: pg.mixer.Sound
    asteroid_explosion: pg.mixer.Sound
    ship_explosion: pg.mixer.Sound
    thrust_loop: pg.mixer.Sound
    ufo_siren_big: pg.mixer.Sound
    ufo_siren_small: pg.mixer.Sound
    # rescue
    player_downed:      pg.mixer.Sound
    rescue_beep:        pg.mixer.Sound
    rescue_complete:    pg.mixer.Sound
    rescue_failed:      pg.mixer.Sound


def _load_or_silent(path: str) -> pg.mixer.Sound:
    """Load a sound file, or return a silent placeholder if missing."""
    if Path(path).exists():
        return pg.mixer.Sound(path)
    # 50 ms of silence — avoids crashes during development
    silent = pg.mixer.Sound(buffer=bytes(4410))
    return silent


def load_sounds(base_path: str) -> SoundPack:
    def s(name: str) -> pg.mixer.Sound:
        return _load_or_silent(f"{base_path}/{name}")

    return SoundPack(
        player_shoot = s(C.PLAYER_SHOOT),
        ufo_shoot = s(C.UFO_SHOOT),
        asteroid_explosion = s(C.ASTEROID_EXPLOSION),
        ship_explosion = s(C.SHIP_EXPLOSION),
        thrust_loop = s(C.THRUST_LOOP),
        ufo_siren_big = s(C.UFO_SIREN_BIG),
        ufo_siren_small = s(C.UFO_SIREN_SMALL),
        player_downed = s(C.PLAYER_DOWNED),
        rescue_beep = s(C.RESCUE_BEEP),
        rescue_complete = s(C.RESCUE_COMPLETE),
        rescue_failed = s(C.RESCUE_FAILED),
    )