"""Input hub: aggregates keyboard (fallback) and joystick input.

Priority rules
--------------
- 1 joystick  → P1 = joystick 0,  P2 = teclado
- 2 joysticks → P1 = joystick 0,  P2 = joystick 1   (teclado desativado)
- 0 joysticks → P1 = teclado  (single-player / fallback)

Hot-plug: reconectar/desconectar controles durante o jogo é suportado.
"""

import pygame as pg

from core.commands import PlayerCommand
from core import config as C
from client.controls import InputMapper
from client.joystick import JoystickMapper

PlayerId = int


class InputHub:
    """Single entry point for all local player input."""

    def __init__(self) -> None:
        self._keyboard = InputMapper()
        # device_index → JoystickMapper (preserva ordem de conexão)
        self._joysticks: dict[int, JoystickMapper] = {}
        self._scan_joysticks()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle_event(self, event: pg.event.Event) -> None:
        # Teclado sempre recebe eventos (pode ser fallback de P2)
        self._keyboard.handle_event(event)

        if event.type == pg.JOYDEVICEADDED:
            self._add_joystick(event.device_index)
        elif event.type == pg.JOYDEVICEREMOVED:
            self._remove_joystick(event.instance_id)

        if event.type == pg.JOYBUTTONDOWN:
            mapper = self._joysticks.get(event.joy)
            if mapper:
                mapper.handle_event(event)

    def build_commands(self) -> dict[PlayerId, PlayerCommand]:
        joy_list = list(self._joysticks.values())
        n = len(joy_list)

        if n == 0:
            # Sem controles — P1 no teclado
            keys = pg.key.get_pressed()
            return {1: self._keyboard.build_command(keys)}

        if n == 1:
            # Um controle — P1 no joystick, P2 no teclado
            keys = pg.key.get_pressed()
            return {
                1: joy_list[0].build_command(),
                2: self._keyboard.build_command(keys),
            }

        # Dois ou mais controles — P1 e P2 nos joysticks, teclado ignorado
        cmds: dict[PlayerId, PlayerCommand] = {}
        for slot, mapper in enumerate(joy_list, start=1):
            cmds[slot] = mapper.build_command()
            if slot >= C.MAX_PLAYERS:
                break
        return cmds

    @property
    def active_player_ids(self) -> list[PlayerId]:
        return list(self.build_commands().keys())

    @property
    def joystick_count(self) -> int:
        return len(self._joysticks)

    def input_summary(self) -> str:
        """Human-readable description of current input layout (for menu/debug)."""
        n = len(self._joysticks)
        if n == 0:
            return "P1: Teclado"
        if n == 1:
            return "P1: Controle   P2: Teclado"
        return "  ".join(f"P{i+1}: Controle" for i in range(min(n, C.MAX_PLAYERS)))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _scan_joysticks(self) -> None:
        for i in range(pg.joystick.get_count()):
            self._add_joystick(i)

    def _add_joystick(self, device_index: int) -> None:
        if device_index in self._joysticks:
            return
        try:
            mapper = JoystickMapper(device_index)
            self._joysticks[device_index] = mapper
            print(f"[InputHub] Conectado: [{device_index}] {mapper.name}")
            print(f"[InputHub] Layout atual: {self.input_summary()}")
        except pg.error as exc:
            print(f"[InputHub] Erro ao abrir joystick {device_index}: {exc}")

    def _remove_joystick(self, instance_id: int) -> None:
        if instance_id in self._joysticks:
            del self._joysticks[instance_id]
            print(f"[InputHub] Desconectado: joystick {instance_id}")
            print(f"[InputHub] Layout atual: {self.input_summary()}")