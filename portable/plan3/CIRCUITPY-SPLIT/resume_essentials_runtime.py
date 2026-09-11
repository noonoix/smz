"""Memory-small Resume Essentials executor for the Pico root cycle."""
import random
import time


class EssentialAbort(Exception):
    pass


def _pair(value, what):
    parts = value.split(",")
    if len(parts) != 2:
        raise ValueError(what + " needs min,max")
    lo, hi = int(parts[0]), int(parts[1])
    if hi < lo:
        lo, hi = hi, lo
    if lo < 0:
        raise ValueError(what + " cannot be negative")
    return lo, hi


def parse(text):
    items = []
    header = False
    for line_no, raw in enumerate(text.split("\n"), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("|")
        if not header:
            if fields != ["ESSENTIALS", "1"]:
                raise ValueError("line %d: expected ESSENTIALS|1" % line_no)
            header = True
            continue
        if fields[0] != "ITEM":
            raise ValueError("line %d: unknown essentials op" % line_no)
        values = {}
        for field in fields[1:]:
            key, sep, value = field.partition("=")
            if not sep or key in values:
                raise ValueError("line %d: bad/duplicate ITEM field" % line_no)
            values[key] = value
        required = ("vk", "interval", "hold", "before", "after", "priority", "resume")
        if any(key not in values for key in required):
            raise ValueError("line %d: incomplete ITEM" % line_no)
        item = {
            "vk": int(values["vk"]),
            "interval": _pair(values["interval"], "interval"),
            "hold": _pair(values["hold"], "hold"),
            "before": _pair(values["before"], "before"),
            "after": _pair(values["after"], "after"),
            "priority": int(values["priority"]),
            "resume": values["resume"] == "1",
            "next": None,
        }
        if not 0 < item["vk"] < 256 or item["interval"][0] <= 0:
            raise ValueError("line %d: invalid key/interval" % line_no)
        items.append(item)
    if not header:
        raise ValueError("missing ESSENTIALS|1")
    return items


class Manager:
    def __init__(self, items, now=None, rng=None, resume_pending=False):
        self.items = items
        self.now = now or time.monotonic
        self.rng = rng or random
        self.resume_pending = bool(resume_pending)
        self.running = False
        self.initialized = False

    @classmethod
    def from_file(cls, path="/resume_essentials.txt", **kwargs):
        try:
            with open(path, "r") as fh:
                text = fh.read()
        except OSError:
            return cls([], **kwargs)
        return cls(parse(text), **kwargs)

    def _draw(self, pair):
        return pair[0] if pair[1] <= pair[0] else self.rng.randint(pair[0], pair[1])

    def _schedule(self, item):
        item["next"] = float(self.now()) + self._draw(item["interval"])

    def arm_initial(self):
        if self.initialized:
            return
        for item in self.items:
            self._schedule(item)
        self.initialized = True

    def _sleep(self, ctx, pair):
        if not ctx.sleep_ms(self._draw(pair)):
            raise EssentialAbort()

    def _perform(self, ctx, item):
        self._sleep(ctx, item["before"])
        ctx.kdown(item["vk"])
        try:
            self._sleep(ctx, item["hold"])
        finally:
            ctx.kup(item["vk"])
        self._sleep(ctx, item["after"])
        self._schedule(item)  # interval starts only after the complete successful item

    def run_resume(self, ctx):
        if not self.resume_pending or self.running:
            self.arm_initial()
            return 0
        chosen = [item for item in self.items if item["resume"]]
        self.rng.shuffle(chosen)  # mandatory Shuffle All
        self.running = True
        completed = 0
        try:
            for item in chosen:
                self._perform(ctx, item)
                completed += 1
            for item in self.items:
                if item not in chosen:
                    self._schedule(item)
            self.resume_pending = False
            self.initialized = True
            return completed
        finally:
            self.running = False

    def run_due(self, ctx):
        if self.running:
            return 0
        self.arm_initial()
        now = float(self.now())
        due = sorted((item for item in self.items
                      if item["next"] is not None and now >= item["next"]),
                     key=lambda item: (item["priority"], item["next"], item["vk"]))
        self.running = True
        completed = 0
        try:
            for item in due:
                self._perform(ctx, item)
                completed += 1
            return completed
        finally:
            self.running = False
