# live_light_guard.py - portable BH1750 state guard (runtime v1)
# Pure state-selection logic. The plan engine supplies lux samples and owns
# the safe handoff at a command boundary; this module never guesses a state.


class LightStateGuard:
    """Debounced, hysteretic light-state selector."""

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
        low = int(state["lo"])
        high = int(state["hi"])
        if widened:
            low -= self.hysteresis
            high += self.hysteresis
        return low <= lux <= high

    def _eligible(self, lux):
        if lux is None:
            return []
        return [state for state in self.states if self._inside(state, lux, False)]

    def _active_still_valid(self, lux):
        if lux is None or self.active is None:
            return False
        return any(state["id"] == self.active and self._inside(state, lux, True)
                   for state in self.states)

    def update(self, lux, now_ms):
        """Return active id, or None when the sensor/state is unsafe."""
        now_ms = int(now_ms)
        self.last_sample_ms = now_ms if lux is not None else self.last_sample_ms

        if lux is None:
            if self.last_sample_ms is None:
                return None
            if now_ms - self.last_sample_ms > self.sensor_timeout_ms:
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

        # Keep the current route while a new candidate is being debounced.
        return self.active if self.active is not None else None

    def reset(self):
        self.active = None
        self.candidate = None
        self.candidate_since = None
        self.last_sample_ms = None


def state_spec(state_id, low, high, route):
    return {"id": str(state_id), "lo": int(low), "hi": int(high), "route": str(route)}
