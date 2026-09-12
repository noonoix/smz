"""Root-scoped PLAN auto-cycle export contract for v0.9.67.

The compiler/exporters use this module before the Pico parser/runtime is wired.
Child INCLUDE plans never receive these directives: one root owns one deadline.
"""

from runtime_policy import RuntimeOptions

RUNFOR_OP = "RUNFOR"
AUTORESUME_OP = "AUTORESUME"
POSTLAUNCH_OP = "POSTLAUNCH"


class CycleExportPolicy:
    def __init__(self, settings=None):
        self.options = RuntimeOptions.from_settings(settings or {})

    def root_plan_lines(self):
        """Return deterministic ranges; random values are drawn later by the runtime once."""
        o = self.options
        return [
            "%s|%d,%d" % (RUNFOR_OP, o.restart_min_seconds, o.restart_max_seconds),
            "%s|%d,%d,%d" % (
                AUTORESUME_OP,
                1 if o.auto_resume else 0,
                o.resume_min_seconds,
                o.resume_max_seconds,
            ),
            "%s|%d,%d,%d,%d,%d,%d" % (
                POSTLAUNCH_OP,
                1 if o.post_launch_enabled else 0,
                o.post_launch_slot,
                o.launch_before_seconds[0],
                o.launch_before_seconds[1],
                o.launch_after_seconds[0],
                o.launch_after_seconds[1],
            ),
        ]

    def include_plan_lines(self):
        """INCLUDEs share the root deadline and must not create independent cycles."""
        return []

    def as_report(self):
        o = self.options
        return {
            "restartSeconds": [o.restart_min_seconds, o.restart_max_seconds],
            "autoResumeEnabled": o.auto_resume,
            "resumeSeconds": [o.resume_min_seconds, o.resume_max_seconds],
            "postRestartLaunchEnabled": o.post_launch_enabled,
            "postRestartTaskbarSlot": o.post_launch_slot,
            "postRestartLaunchBeforeSeconds": list(o.launch_before_seconds),
            "postRestartLaunchAfterSeconds": list(o.launch_after_seconds),
            "buzzerPin": o.buzzer_pin,
        }


def cycle_lines(settings=None, root=True):
    policy = CycleExportPolicy(settings)
    return policy.root_plan_lines() if root else policy.include_plan_lines()
