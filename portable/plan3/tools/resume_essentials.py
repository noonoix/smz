"""Resume Essentials and recurring-maintenance scheduler for portable PLAN|2.

All due work is returned only at a caller-declared safe boundary. The scheduler never
interrupts a held key, KTEXT chunk, mouse drag, or another atomic action.
"""

import random


def _pair(mn, mx, name, allow_zero=False):
    lo, hi = int(mn), int(mx)
    if hi < lo:
        lo, hi = hi, lo
    floor = 0 if allow_zero else 1
    if lo < floor:
        raise ValueError(name + " range is invalid")
    return lo, hi


class EssentialItem:
    def __init__(self, name, vk, interval_min_seconds, interval_max_seconds,
                 hold_min_ms=45, hold_max_ms=105,
                 before_min_ms=120, before_max_ms=380,
                 after_min_ms=700, after_max_ms=1600,
                 priority=100, enabled=True, run_on_resume=True):
        self.name = str(name).strip()
        if not self.name:
            raise ValueError("essential name is required")
        self.vk = int(vk)
        if not 0 < self.vk < 256:
            raise ValueError("essential key must be a valid VK")
        self.interval = _pair(interval_min_seconds, interval_max_seconds, "interval")
        self.hold = _pair(hold_min_ms, hold_max_ms, "hold")
        self.before = _pair(before_min_ms, before_max_ms, "before", allow_zero=True)
        self.after = _pair(after_min_ms, after_max_ms, "after", allow_zero=True)
        self.priority = int(priority)
        self.enabled = bool(enabled)
        self.run_on_resume = bool(run_on_resume)
        self.next_due = None

    def plan_lines(self):
        """Ranged delays are sampled by the engine when the item actually runs."""
        return [
            "# essential: " + self.name,
            "DELAY|%d,%d" % self.before,
            "KDOWN|%d" % self.vk,
            "DELAY|%d,%d" % self.hold,
            "KUP|%d" % self.vk,
            "DELAY|%d,%d" % self.after,
        ]

    def mark_success(self, now, rng):
        self.next_due = float(now) + rng.randint(self.interval[0], self.interval[1])
        return self.next_due


class EssentialScheduler:
    """Run-scoped scheduler with a mandatory shuffled resume package."""

    def __init__(self, items, rng=None):
        names = set()
        self.items = []
        for item in items:
            if item.name in names:
                raise ValueError("duplicate essential name: " + item.name)
            names.add(item.name)
            self.items.append(item)
        self.rng = rng or random

    def resume_package(self):
        """Shuffle All: every enabled run-on-resume item appears exactly once."""
        chosen = [x for x in self.items if x.enabled and x.run_on_resume]
        self.rng.shuffle(chosen)
        return chosen

    def mark_resume_success(self, now, completed_items):
        """Each interval starts at that item's successful post-resume execution."""
        for item in completed_items:
            item.mark_success(now, self.rng)

    def due_at_safe_boundary(self, now):
        """Return all due items, priority first; caller runs them serially and marks success."""
        now = float(now)
        return sorted(
            (x for x in self.items if x.enabled and x.next_due is not None and now >= x.next_due),
            key=lambda x: (x.priority, x.next_due, x.name))

    def mark_success(self, item, now):
        if item not in self.items:
            raise ValueError("item does not belong to this scheduler")
        return item.mark_success(now, self.rng)


def package_plan_lines(items):
    """Flatten one already-shuffled Resume Essentials package into PLAN|2 lines."""
    lines = ["# Resume Essentials: Shuffle All"]
    for item in items:
        lines.extend(item.plan_lines())
    return lines
