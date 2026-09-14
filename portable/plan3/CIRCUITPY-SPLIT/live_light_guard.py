# live_light_guard.py - portable BH1750 state guard (runtime v1)

class LightStateGuard:
    """Debounced and hysteretic light-state selector for the Pico runtime."""

    def __init__(self, states, stable_ms=750, hysteresis=0, sensor_timeout_ms=1500):
        self.states = tuple(states or ())
        self.stable_ms = max(0, int(stable_ms))
        self.hysteresis = max(0, int(hysteresis))
        self.sensor_timeout_ms = max(0, int(sensor_timeout_ms))
        self.active = None
        self.candidate = None
        self.candidate_since = None
        self.last_sample_ms = None

    def _inside(self, state, lux, widened=False):
        low, high = int(state["lo"]), int(state["hi"])
        if widened:
            low -= self.hysteresis
            high += self.hysteresis
        return low <= lux <= high

    def _eligible(self, lux):
        return [] if lux is None else [s for s in self.states if self._inside(s, lux)]

    def _active_still_valid(self, lux):
        if lux is None or self.active is None:
            return False
        return any(s["id"] == self.active and self._inside(s, lux, True) for s in self.states)

    def update(self, lux, now_ms):
        now_ms = int(now_ms)
        self.last_sample_ms = now_ms if lux is not None else self.last_sample_ms
        if lux is None:
            if self.last_sample_ms is None or now_ms - self.last_sample_ms > self.sensor_timeout_ms:
                return None
            return self.active
        if self.active is not None and self._active_still_valid(lux):
            eligible = self._eligible(lux)
            if len(eligible) == 1 and eligible[0]["id"] == self.active:
                self.candidate = None
                self.candidate_since = None
                return self.active
        eligible = self._eligible(lux)
        if len(eligible) != 1:
            self.candidate = None
            self.candidate_since = None
            return self.active if self.active is not None and self._active_still_valid(lux) else None
        state_id = eligible[0]["id"]
        if state_id != self.candidate:
            self.candidate = state_id
            self.candidate_since = now_ms
        if self.candidate_since is not None and now_ms - self.candidate_since >= self.stable_ms:
            self.active = state_id
            self.candidate = None
            self.candidate_since = None
            return self.active
        return self.active if self.active is not None else None

    def reset(self):
        self.active = None
        self.candidate = None
        self.candidate_since = None
        self.last_sample_ms = None


def state_spec(state_id, low, high, route):
    return {"id": str(state_id), "lo": int(low), "hi": int(high), "route": str(route)}
