"""Client-side rendering (pygame)."""

import pygame as pg
import math
from core import config as C
from core.entities import Asteroid, Bullet, Ship, UFO
from core.rescue import DownedState
from core.scene import SceneState
from client.colors import player_color


class Renderer:
    """Draws scenes and entities without coupling game rules to Game."""

    def __init__(
        self,
        screen: pg.Surface,
        config: object = C,
        fonts: dict[str, pg.font.Font] | None = None,
    ) -> None:
        self.screen = screen
        self.config = config
        safe_fonts = fonts or {}
        self.font = safe_fonts["font"]
        self.big = safe_fonts["big"]

        self._draw_dispatch: dict[type, callable] = {
            Bullet: self._draw_bullet,
            Asteroid: self._draw_asteroid,
            Ship: self._draw_ship,
            UFO: self._draw_ufo,
        }

    def clear(self) -> None:
        self.screen.fill(self.config.BLACK)

    def draw_world(self, world: object) -> None:
        sprites = getattr(world, "all_sprites", [])
        for sprite in sprites:
            drawer = self._draw_dispatch.get(type(sprite))
            if drawer is not None:
                drawer(sprite)

    def draw_rescue_overlay(
        self,
        ships: dict[int, Ship],
        downed: dict[int, DownedState],
    ) -> None:
        """Draw downed ship indicators and rescue progress arcs."""
        for pid, ds in downed.items():
            ship = ships.get(pid)
            if ship is None:
                continue
            self._draw_downed_ship(ship, ds)
            self._draw_rescue_range_hint(ship, ds)
    def draw_hud(
        self,
        scores: dict[int, int],
        lives: dict[int, int],
        wave: int,
        state: SceneState,
        downed: dict[int, DownedState] | None = None,
    ) -> None:
        if state != SceneState.PLAY:
            return

        # Wave — centred top
        wave_label = self.font.render(f"WAVE {wave}", True, self.config.WHITE)
        self.screen.blit(
            wave_label,
            (self.config.WIDTH // 2 - wave_label.get_width() // 2, 10),
        )
        # Per-player panels
        positions = [
            (10, 10),
            (self.config.WIDTH - 230, 10),
            (10, 38),
            (self.config.WIDTH - 230, 38),
        ]

        for idx, pid in enumerate(sorted(scores.keys())):
            color = player_color(pid)
            score = scores.get(pid, 0)
            life  = lives.get(pid, 0)

            is_downed = downed and pid in downed
            if is_downed:
                ds   = downed[pid]
                text = f"P{pid}  {score:06d}  ♥ {life}  ↓ {ds.timer:.1f}s"
                # flash the panel in orange when downed
                color = (255, 140, 0) if int(ds.timer * 4) % 2 == 0 else (200, 80, 0)
            else:
                text = f"P{pid}  {score:06d}  ♥ {life}"

            label = self.font.render(text, True, color)
            pos   = positions[idx] if idx < len(positions) else (10, 10 + idx * 28)
            self.screen.blit(label, pos)
    def draw_menu(self, input_summary: str = "") -> None:
        self._draw_text(self.big,  "ASTEROIDS",    self.config.WIDTH // 2 - 170, 200)
        self._draw_text(self.font, "Press any key", self.config.WIDTH // 2 - 170, 350)
        hint = input_summary or "P1: Teclado"
        label = self.font.render(hint, True, self.config.WHITE)
        self.screen.blit(
            label,
            (self.config.WIDTH // 2 - label.get_width() // 2, 410),
        )

    def draw_game_over(self) -> None:
        self._draw_text(
            self.big,
            "GAME OVER",
            self.config.WIDTH // 2 - 170,
            260,
        )
        self._draw_text(
            self.font,
            "Press any key",
            self.config.WIDTH // 2 - 170,
            340,
        )

    def _draw_downed_ship(self, ship: Ship, ds: DownedState) -> None:
        """Flickering ship + countdown arc + rescue-progress arc."""
        # --- flickering ship polygon (orange / dark orange) ---
        tick  = int(ds.timer * 8) % 2
        color = (255, 100, 0) if tick == 0 else (180, 50, 0)
        p1, p2, p3 = ship.ship_points()
        points = [(int(p.x), int(p.y)) for p in (p1, p2, p3)]
        pg.draw.polygon(self.screen, color, points, width=1)

        cx = int(ship.pos.x)
        cy = int(ship.pos.y)

        # --- countdown arc (red, shrinks as timer falls) ---
        r_count = ship.r + 10
        rect_c  = pg.Rect(cx - r_count, cy - r_count, r_count * 2, r_count * 2)
        ratio   = max(0.0, ds.timer / self.config.RESCUE_WINDOW)
        # arc goes from top (-π/2) sweeping clockwise
        start_a = -math.pi / 2
        end_a   = start_a + math.pi * 2 * ratio
        if ratio > 0.01:
            pg.draw.arc(
                self.screen,
                (220, 40, 40),
                rect_c,
                min(start_a, end_a),
                max(start_a, end_a),
                width=2,
            )
        # --- rescue progress arc (green, grows as ally stays close) ---
        if ds.rescue_progress > 0.01:
            r_prog  = ship.r + 17
            rect_p  = pg.Rect(cx - r_prog, cy - r_prog, r_prog * 2, r_prog * 2)
            end_p   = start_a + math.pi * 2 * ds.rescue_progress
            pg.draw.arc(
                self.screen,
                (60, 255, 100),
                rect_p,
                min(start_a, end_p),
                max(start_a, end_p),
                width=3,
            )
    def _draw_rescue_range_hint(self, ship: Ship, ds: DownedState) -> None:
        """Faint circle showing rescue range — only when an ally is nearby."""
        if ds.rescuer_id is None:
            return
        cx = int(ship.pos.x)
        cy = int(ship.pos.y)
        # dim cyan ring at RESCUE_RANGE radius
        surf = pg.Surface(
            (self.config.RESCUE_RANGE * 2 + 4,
             self.config.RESCUE_RANGE * 2 + 4),
            pg.SRCALPHA,
        )
        pg.draw.circle(
            surf,
            (0, 200, 255, 55),
            (self.config.RESCUE_RANGE + 2, self.config.RESCUE_RANGE + 2),
            self.config.RESCUE_RANGE,
            width=1,
        )
        self.screen.blit(
            surf,
            (cx - self.config.RESCUE_RANGE - 2,
             cy - self.config.RESCUE_RANGE - 2),
        )
    def _draw_text(
        self,
        font: pg.font.Font,
        text: str,
        x: int,
        y: int,
        color: tuple[int, int, int] | None = None,
    ) -> None:
        label = font.render(text, True, color or self.config.WHITE)
        self.screen.blit(label, (x, y))

    def _draw_bullet(self, bullet: Bullet) -> None:
        color  = player_color(bullet.owner_id) if bullet.owner_id > 0 else self.config.WHITE
        center = (int(bullet.pos.x), int(bullet.pos.y))
        pg.draw.circle(
            self.screen,
            color,
            center,
            bullet.r,
            width=1,
        )

    def _draw_asteroid(self, asteroid: Asteroid) -> None:
        points = [
            (int(asteroid.pos.x + p.x), int(asteroid.pos.y + p.y))
            for p in asteroid.poly
        ]
        pg.draw.polygon(self.screen, self.config.WHITE, points, width=1)

    def _draw_ship(self, ship: Ship) -> None:
        # Downed ships are drawn by draw_rescue_overlay, not here
        # (invuln==999 is the sentinel for downed state)
        if ship.invuln >= 999.0:
            return
        color  = player_color(ship.player_id)
        p1, p2, p3 = ship.ship_points()
        points = [(int(p.x), int(p.y)) for p in (p1, p2, p3)]
        pg.draw.polygon(self.screen, color, points, width=1)

        # Invulnerability flicker ring
        if ship.invuln > 0.0 and int(ship.invuln * 10) % 2 == 0:
            center = (int(ship.pos.x), int(ship.pos.y))
            pg.draw.circle(
                self.screen,
                color,
                center,
                ship.r + 6,
                width=1,
            )

    def _draw_ufo(self, ufo: UFO) -> None:
        width = ufo.r * 2
        height = ufo.r

        body = pg.Rect(0, 0, width, height)
        body.center = (int(ufo.pos.x), int(ufo.pos.y))
        pg.draw.ellipse(self.screen, self.config.WHITE, body, width=1)

        cup = pg.Rect(0, 0, int(width * 0.5), int(height * 0.7))
        cup.center = (int(ufo.pos.x), int(ufo.pos.y - height * 0.3))
        pg.draw.ellipse(self.screen, self.config.WHITE, cup, width=1)
