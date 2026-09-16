# live_light_guard.py - portable BH1750 state guard (runtime v2)
# Debounces light samples and, when the canonical Phase 7 profiles are present,
# applies the portable GuardTransition ordered-stage policy before a route changes.

try:
    from guard_transition import GuardTransition, PROFILE_TO_ROUTE
except ImportError:  # keep the generic legacy light guard usable by older bundles
    GuardTransition = None
    PROFILE_TO_ROUTE = {}


class LightStateGuard:
    """Debounced, hysteretic light-state selector with optional ordered routing."""

    def __init__(self, states, stable_ms=750, hysteresis=0, sensor_timeout_ms=1500):
        self.states = tuple(states or ())
        self.stable_ms = max(0, int(stable_ms))
        self.hysteresis = max(0, int(hysteresis))
        self.sensor_timeout_ms = max(0, int(sensor_timeout_ms))
        self.active = None
        self.candidate = None
        self.candidate_since = None
        self.last_sample_ms = None
        self.last_decision = None
        ids = {str(state.get("id")) for state in self.states}
        self.transition = (
            GuardTransition()
            if GuardTransition is not None and set(PROFILE_TO_ROUTE).issubset(ids)
            else None
        )

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

    def _policy_state(self, state_id):
        if self.transition is None:
            self.last_decision = None
            return True
        decision = self.transition.observe(state_id)
        self.last_decision = decision
        # A denied transition is unsafe. Targeted -> Game is intentionally a
        # non-executing decision with a valid route, so it remains accepted.
        return bool(decision.get("execute") or decision.get("route"))

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
            if self.active is not None and self._active_still_valid(lux):
                return self.active
            if self.transition is not None:
                self.transition.observe_unknown()
                self.last_decision = None
            self.active = None
            return None

        state_id = eligible[0]["id"]
        if state_id != self.candidate:
            self.candidate = state_id
            self.candidate_since = now_ms

        if self.candidate_since is not None and now_ms - self.candidate_since >= self.stable_ms:
            if not self._policy_state(state_id):
                self.active = None
                self.candidate = None
                self.candidate_since = None
                return None
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
        self.last_decision = None
        if self.transition is not None:
            self.transition.reset()


def state_spec(state_id, low, high, route):
    return {"id": str(state_id), "lo": int(low), "hi": int(high), "route": str(route)}
