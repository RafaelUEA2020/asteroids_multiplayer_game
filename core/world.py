"""Game systems (World, waves, score,coop).

Player lifecycle
----------------
ALIVE  → hit by asteroid/UFO bullet → DOWNED  (if ally alive)
                                     → _ship_die (if alone)
DOWNED → ally rescues in time        → ALIVE   (no life lost)
       → timer expires               → _ship_die (life lost, respawn)
"""

import math
from random import uniform
from typing import Dict

import pygame as pg

from core import config as C
from core.collisions import CollisionManager
from core.commands import PlayerCommand
from core.entities import Asteroid, Ship, UFO
from core.rescue import DownedState
from core.utils import Vec, rand_edge_pos

PlayerId = int


class World:
    """World state and game rules.

    Multiplayer-ready:
    - World receives commands indexed by player_id.
    - World generates events (strings) for the client (sounds/effects).
    """

    def __init__(self) -> None:
        self.ships: Dict[PlayerId, Ship] = {}
        self.bullets = pg.sprite.Group()
        self.asteroids = pg.sprite.Group()
        self.ufos = pg.sprite.Group()
        self.all_sprites = pg.sprite.Group()

        self.scores: Dict[PlayerId, int] = {}
        self.lives: Dict[PlayerId, int] = {}
        self.wave = 0
        self.wave_cool = float(C.WAVE_DELAY)
        self.ufo_timer = float(C.UFO_SPAWN_EVERY)
        # Rescue state — only players currently downed appear here
        self.downed: Dict[PlayerId, DownedState] = {}
        self._beep_timers: Dict[PlayerId, float] = {}

        self.events: list[str] = []
        self._collision_mgr = CollisionManager()

        self.game_over = False

        self.spawn_player(C.LOCAL_PLAYER_ID)

    def begin_frame(self) -> None:
        self.events.clear()

    def reset(self) -> None:
        """Reset the world (used on Game Over)."""
        self.__init__()

    def spawn_player(self, player_id: PlayerId) -> None:
        if player_id in self.ships:
            return
        offset_x = (player_id - 1) * 40
        pos = Vec(C.WIDTH / 2 + offset_x, C.HEIGHT / 2)
        ship = Ship(player_id, pos)
        ship.invuln = float(C.SAFE_SPAWN_TIME)

        self.ships[player_id] = ship
        self.scores[player_id] = 0
        self.lives[player_id] = C.START_LIVES
        self.all_sprites.add(ship)

    def get_ship(self, player_id: PlayerId) -> Ship | None:
        return self.ships.get(player_id)

    def start_wave(self) -> None:
        self.wave += 1
        count = C.WAVE_BASE_COUNT + self.wave

        ship_positions = [s.pos for s in self.ships.values()]

        for _ in range(count):
            pos = rand_edge_pos()
            while any(
                (pos - sp).length() < C.AST_MIN_SPAWN_DIST
                for sp in ship_positions
            ):
                pos = rand_edge_pos()

            ang = uniform(0, math.tau)
            speed = uniform(C.AST_VEL_MIN, C.AST_VEL_MAX)
            vel = Vec(math.cos(ang), math.sin(ang)) * speed
            self.spawn_asteroid(pos, vel, "L")

    def spawn_asteroid(self, pos: Vec, vel: Vec, size: str) -> None:
        ast = Asteroid(pos, vel, size)
        self.asteroids.add(ast)
        self.all_sprites.add(ast)

    def spawn_ufo(self) -> None:
        small = uniform(0, 1) < 0.5
        pos = rand_edge_pos()
        target = self._get_nearest_ship_pos(pos)
        ufo = UFO(pos, small, target_pos=target)
        self.ufos.add(ufo)

        self.all_sprites.add(ufo)

    def update(
        self,
        dt: float,
        commands_by_player_id: Dict[PlayerId, PlayerCommand],
    ) -> None:
        self.begin_frame()

        if self.game_over:
            return

        for player_id in commands_by_player_id:
            if player_id not in self.ships:
                self.spawn_player(player_id)

        self._apply_commands(dt, commands_by_player_id)
        self.all_sprites.update(dt)

        self._update_ufos(dt)
        self._update_timers(dt)
        self._handle_collisions()
        self._update_rescue(dt)
        self._maybe_start_next_wave(dt)

    def _apply_commands(
        self,
        dt: float,
        commands_by_player_id: Dict[PlayerId, PlayerCommand],
    ) -> None:
        for player_id, cmd in commands_by_player_id.items():
            if player_id in self.downed:
                continue   # downed players cannot act

            ship = self.get_ship(player_id)
            if ship is None:
                continue

            if cmd.hyperspace:
                ship.hyperspace()
                self.scores[player_id] = max(
                    0, self.scores[player_id] - C.HYPERSPACE_COST
                )

            bullet = ship.apply_command(cmd, dt, self.bullets)
            if bullet is not None:
                self.bullets.add(bullet)
                self.all_sprites.add(bullet)
                self.events.append("player_shoot")

    def _update_ufos(self, dt: float) -> None:
        for ufo in list(self.ufos):
            ufo.target_pos = self._get_nearest_ship_pos(ufo.pos)
            ufo.update(dt)
            if not ufo.alive():
                continue

            bullet = ufo.try_fire()
            if bullet is not None:
                self.bullets.add(bullet)
                self.all_sprites.add(bullet)
                self.events.append("ufo_shoot")

            if not ufo.alive():
                self.ufos.remove(ufo)

    def _get_nearest_ship_pos(self, from_pos: Vec) -> Vec | None:
        """Return position of the nearest living ship to from_pos."""
        nearest = None
        min_dist = float("inf")
        for ship in self.ships.values():
            d = (ship.pos - from_pos).length()
            if d < min_dist:
                min_dist = d
                nearest = ship
        return nearest.pos if nearest else None

    def _update_timers(self, dt: float) -> None:
        self.ufo_timer -= dt
        if self.ufo_timer <= 0.0:
            self.spawn_ufo()
            self.ufo_timer = float(C.UFO_SPAWN_EVERY)

    def _maybe_start_next_wave(self, dt: float) -> None:
        if self.asteroids:
            return

        self.wave_cool -= dt
        if self.wave_cool <= 0.0:
            self.start_wave()
            self.wave_cool = float(C.WAVE_DELAY)

    def _handle_collisions(self) -> None:
        result = self._collision_mgr.resolve(
            self.ships, self.bullets, self.asteroids, self.ufos,
        )

        self.events.extend(result.events)

        for player_id, delta in result.score_deltas.items():
            if player_id in self.scores:
                self.scores[player_id] += delta

        for pos, vel, size in result.asteroids_to_spawn:
            self.spawn_asteroid(pos, vel, size)

        for player_id in result.ship_deaths:
            if player_id in self.downed:
                continue   # already downed, ignore duplicate hit
            ship = self.get_ship(player_id)
            if ship is not None:
                self._on_ship_hit(ship)
    def _on_ship_hit(self, ship: Ship) -> None:
        pid = ship.player_id
        if self._can_be_downed(pid):
            self._ship_go_downed(ship)
        else:
            self._ship_die(ship)

    def _can_be_downed(self, player_id: PlayerId) -> bool:
        for pid in self.ships:
            if pid == player_id:
                continue
            if pid not in self.downed and self.lives.get(pid, 0) > 0:
                return True
        return False

    def _ship_go_downed(self, ship: Ship) -> None:
        pid = ship.player_id
        ship.vel.xy = (0, 0)
        ship.invuln = 999.0   # immune while downed

        self.downed[pid] = DownedState(
            player_id=pid,
            timer=float(C.RESCUE_WINDOW),
        )
        self._beep_timers[pid] = 0.0   # fire first beep immediately

        self.events.append("player_downed")

    def _update_rescue(self, dt: float) -> None:
        for pid, ds in list(self.downed.items()):
            ds.timer -= dt

            downed_ship = self.ships.get(pid)
            if downed_ship is None:
                self.downed.pop(pid, None)
                continue

            # Find rescuer
            rescuer_found = False
            for ally_id, ally_ship in self.ships.items():
                if ally_id == pid or ally_id in self.downed:
                    continue
                dist = (ally_ship.pos - downed_ship.pos).length()
                if dist <= C.RESCUE_RANGE:
                    rescuer_found = True
                    ds.rescuer_id = ally_id
                    ds.rescue_progress += dt / C.RESCUE_TIME_NEEDED
                    ds.rescue_progress  = min(ds.rescue_progress, 1.0)
                    break

            if not rescuer_found:
                ds.rescuer_id = None
                if C.RESCUE_PROGRESS_DECAY > 0:
                    ds.rescue_progress = max(
                        0.0,
                        ds.rescue_progress - C.RESCUE_PROGRESS_DECAY * dt,
                    )

            # Urgency beep
            self._tick_rescue_beep(pid, ds, dt)

            # Resolution
            if ds.rescue_progress >= 1.0:
                self._complete_rescue(pid, ds.rescuer_id)
            elif ds.timer <= 0.0:
                self._fail_rescue(pid)

    def _tick_rescue_beep(
        self,
        pid: PlayerId,
        ds: DownedState,
        dt: float,
    ) -> None:
        ratio    = max(0.0, ds.timer / C.RESCUE_WINDOW)
        interval = (
            C.RESCUE_BEEP_INTERVAL_MIN
            + (C.RESCUE_BEEP_INTERVAL_MAX - C.RESCUE_BEEP_INTERVAL_MIN) * ratio
        )
        self._beep_timers[pid] -= dt
        if self._beep_timers[pid] <= 0.0:
            self.events.append("rescue_beep")
            self._beep_timers[pid] = interval

    def _complete_rescue(
        self,
        pid: PlayerId,
        rescuer_id: PlayerId | None,
    ) -> None:
        ship = self.ships[pid]
        ship.vel.xy = (0, 0)
        ship.invuln = float(C.SAFE_SPAWN_TIME)

        self.downed.pop(pid, None)
        self._beep_timers.pop(pid, None)

        if rescuer_id is not None and rescuer_id in self.scores:
            self.scores[rescuer_id] += C.RESCUE_SCORE_BONUS

        self.events.append("rescue_complete")

    def _fail_rescue(self, pid: PlayerId) -> None:
        self.downed.pop(pid, None)
        self._beep_timers.pop(pid, None)

        self.events.append("rescue_failed")
        ship = self.ships.get(pid)
        if ship is not None:
            self._ship_die(ship)

    def _ship_die(self, ship: Ship) -> None:
        pid = ship.player_id
        self.lives[pid] -= 1
        ship.pos.xy = (C.WIDTH / 2, C.HEIGHT / 2)
        ship.vel.xy = (0, 0)
        ship.angle = -90.0
        ship.invuln = float(C.SAFE_SPAWN_TIME)

        self.events.append("ship_explosion")
        if all(v <= 0 for v in self.lives.values()):
            self.game_over = True
