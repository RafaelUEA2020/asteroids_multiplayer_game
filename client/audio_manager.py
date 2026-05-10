"""Audio playback manager for the game client."""

import pygame as pg

from client.audio import SoundPack


class AudioManager:
    """Manages audio channels and event-driven sound playback."""

    def __init__(self, sounds: SoundPack) -> None:
        self.sounds = sounds
        self._thrust_ch = pg.mixer.Channel(1)
        self._sfx_ch = pg.mixer.Channel(2)
        self._ufo_ch = pg.mixer.Channel(3)
        self._rescue_ch = pg.mixer.Channel(4)   # beep loop during downed
        self._ufo_siren_kind: str | None = None

    def play_events(self, events: list[str]) -> None:
        for ev in events:
            if ev == "player_shoot":
                self._sfx_ch.play(self.sounds.player_shoot)
            elif ev == "ufo_shoot":
                self._sfx_ch.play(self.sounds.ufo_shoot)
            elif ev == "asteroid_explosion":
                self._sfx_ch.play(self.sounds.asteroid_explosion)
            elif ev == "ship_explosion":
                self._sfx_ch.play(self.sounds.ship_explosion)
            elif ev == "player_downed":
                self._sfx_ch.play(self.sounds.player_downed)
            elif ev == "rescue_beep":
                # Only play if the sfx channel is free (avoid overlap spam)
                if not self._rescue_ch.get_busy():
                    self._rescue_ch.play(self.sounds.rescue_beep)
            elif ev == "rescue_complete":
                self._rescue_ch.stop()
                self._sfx_ch.play(self.sounds.rescue_complete)
            elif ev == "rescue_failed":
                self._rescue_ch.stop()
                self._sfx_ch.play(self.sounds.rescue_failed)

    def update_thrust(self, active: bool) -> None:
        if active:
            if not self._thrust_ch.get_busy():
                self._thrust_ch.play(self.sounds.thrust_loop, loops=-1)
        else:
            if self._thrust_ch.get_busy():
                self._thrust_ch.stop()

    def update_ufo_siren(self, ufos: list) -> None:
        kind = self._choose_ufo_siren(ufos)
        if kind is None:
            if self._ufo_ch.get_busy():
                self._ufo_ch.stop()
            self._ufo_siren_kind = None
            return

        if self._ufo_siren_kind == kind:
            return

        self._ufo_ch.stop()
        snd = self.sounds.ufo_siren_small if kind == "small" else self.sounds.ufo_siren_big
        self._ufo_ch.play(snd, loops=-1)
        self._ufo_siren_kind = kind

    def stop_all(self) -> None:
        self._thrust_ch.stop()
        self._ufo_ch.stop()
        self._rescue_ch.stop()
        self._ufo_siren_kind = None

    def _choose_ufo_siren(self, ufos: list) -> str | None:
        if not ufos:
            return None
        return "small" if any(getattr(u, "small", False) for u in ufos) else "big"
