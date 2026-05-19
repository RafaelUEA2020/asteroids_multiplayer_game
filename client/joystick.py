"""Joystick input mapper for local co-op (PS3 / generic gamepads).

Button layout targets PS3 DualShock 3 via pygame on Linux/Windows.
Run  python -m client.joystick_debug  to print raw button/axis indices
for your specific driver so you can adjust BUTTON_MAP / AXIS_MAP below.

PS3 via pygame (typical mapping)
---------------------------------
Axes:
  0  Left stick X   (−1 = left,  +1 = right)
  1  Left stick Y   (−1 = up,    +1 = down)
  2  Right stick X
  3  Right stick Y
  4  L2 analog
  5  R2 analog

Buttons:
  0   Select
  1   L3 (left stick click)
  2   R3 (right stick click)
  3   Start
  4   D-pad Up
  5   D-pad Right
  6   
  7   D-pad Left
  8   L2
  9   R2
  10  L1
  11  R1
  12  D-pad Left
  13  D-pad Down
  14  Cross  (X)
  15  Square
"""

import pygame as pg

from core.commands import PlayerCommand

# Axis indices
AXIS_LX = 0   # left stick horizontal (rotate)

# Button indices  — adjust here if your driver differs
BTN_THRUST    = 0   # d-pad up  → thrust
BTN_SHOOT     = 2   # square     → shoot
BTN_HYPERSPACE = 10  # R1        → hyperspace

# Dead-zone for analog sticks
DEAD_ZONE = 0.25


class JoystickMapper:
    """Reads one pygame Joystick and converts it to PlayerCommand."""

    def __init__(self, joystick_id: int) -> None:
        self._joy = pg.joystick.Joystick(joystick_id)
        self._joy.init()
        self._shoot_pressed   = False
        self._hyper_pressed   = False

    # ------------------------------------------------------------------
    # Called once per pygame event in the event loop
    # ------------------------------------------------------------------
    def handle_event(self, event: pg.event.Event) -> None:
        if event.type != pg.JOYBUTTONDOWN:
            return
        if event.joy != self._joy.get_id():
            return

        if event.button == BTN_SHOOT:
            self._shoot_pressed = True
        elif event.button == BTN_HYPERSPACE:
            self._hyper_pressed = True

    # ------------------------------------------------------------------
    # Called once per frame to build the command
    # ------------------------------------------------------------------
    def build_command(self) -> PlayerCommand:
        axis_x = self._safe_axis(AXIS_LX)

        rotate_left  = axis_x < -DEAD_ZONE
        rotate_right = axis_x >  DEAD_ZONE
        thrust       = self._safe_button(BTN_THRUST)

        # D-pad fallback for rotate (buttons 7 / 5)
        if self._safe_button(7):   # D-pad left
            rotate_left = True
        if self._safe_button(5):   # D-pad right
            rotate_right = True
        if self._safe_button(4):   # D-pad up
            thrust = True

        cmd = PlayerCommand(
            rotate_left  = rotate_left,
            rotate_right = rotate_right,
            thrust       = thrust,
            shoot        = self._shoot_pressed,
            hyperspace   = self._hyper_pressed,
        )

        self._shoot_pressed = False
        self._hyper_pressed = False
        return cmd

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _safe_axis(self, index: int) -> float:
        try:
            return self._joy.get_axis(index)
        except pg.error:
            return 0.0

    def _safe_button(self, index: int) -> bool:
        try:
            return bool(self._joy.get_button(index))
        except pg.error:
            return False

    @property
    def name(self) -> str:
        return self._joy.get_name()