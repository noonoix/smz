"""Humanized Windows 11 restart sequence for the Pico keyboard HID.

Sequence: Win+X -> Up -> Up -> Enter -> Up -> Enter.
Each press hold and each inter-key gap is freshly drawn from a range.
"""
import random

WIN = 91
X = 88
UP = 38
ENTER = 13

_MENU_STEPS = (
    (UP, (45, 100), (110, 240)),
    (UP, (45, 100), (180, 360)),
    (ENTER, (55, 120), (280, 520)),
    (UP, (45, 100), (350, 700)),
    (ENTER, (55, 120), None),
)


def _wait(ctx, rng, bounds):
    if bounds is None:
        return
    ms = rng.randint(bounds[0], bounds[1])
    if not ctx.sleep_ms(ms):
        raise RuntimeError("restart sequence aborted")


def _tap(ctx, rng, vk, hold, after):
    ctx.kdown(vk)
    _wait(ctx, rng, hold)
    ctx.kup(vk)
    _wait(ctx, rng, after)


def perform(ctx, rng=None):
    """Execute the power-menu restart after the caller has released all held inputs."""
    rng = rng or random

    # Win must remain held while X is tapped; releasing Win first would type a plain X.
    ctx.kdown(WIN)
    _wait(ctx, rng, (25, 60))
    ctx.kdown(X)
    _wait(ctx, rng, (45, 95))
    ctx.kup(X)
    _wait(ctx, rng, (25, 60))
    ctx.kup(WIN)
    _wait(ctx, rng, (450, 850))

    for vk, hold, after in _MENU_STEPS:
        _tap(ctx, rng, vk, hold, after)
