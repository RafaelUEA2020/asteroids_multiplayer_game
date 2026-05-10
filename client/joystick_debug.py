"""Debug tool: print raw joystick button / axis events to the terminal.

Usage:
    python -m client.joystick_debug

Press every button and move every stick; use the printed indices to
update AXIS_MAP / BUTTON_MAP in client/joystick.py for your driver.
Press Ctrl-C or close the window to quit.
"""

import sys
import pygame as pg


def main() -> None:
    pg.init()
    pg.display.set_mode((400, 200))
    pg.display.set_caption("Joystick Debug — press buttons / move sticks")

    count = pg.joystick.get_count()
    if count == 0:
        print("No joystick detected. Plug in your controller and try again.")
        sys.exit(1)

    joysticks = []
    for i in range(count):
        joy = pg.joystick.Joystick(i)
        joy.init()
        joysticks.append(joy)
        print(f"[{i}] {joy.get_name()}  "
              f"axes={joy.get_numaxes()}  "
              f"buttons={joy.get_numbuttons()}")

    print("\nListening for events… (Ctrl-C to quit)\n")

    AXIS_THRESHOLD = 0.15
    axis_states: dict[tuple[int, int], float] = {}

    clock = pg.time.Clock()
    running = True
    while running:
        clock.tick(60)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

            elif event.type == pg.JOYBUTTONDOWN:
                print(f"joy={event.joy}  BUTTON DOWN  btn={event.button}")

            elif event.type == pg.JOYBUTTONUP:
                print(f"joy={event.joy}  BUTTON UP    btn={event.button}")

        # poll axes (events alone miss gradual movement)
        for joy in joysticks:
            jid = joy.get_id()
            for ax in range(joy.get_numaxes()):
                val = joy.get_axis(ax)
                key = (jid, ax)
                prev = axis_states.get(key, 0.0)
                if abs(val - prev) > AXIS_THRESHOLD:
                    print(f"joy={jid}  AXIS  ax={ax}  val={val:+.3f}")
                    axis_states[key] = val

    pg.quit()


if __name__ == "__main__":
    main()