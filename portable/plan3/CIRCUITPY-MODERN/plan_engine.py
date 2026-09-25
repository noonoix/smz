# Compatibility facade for the memory-split experimental bundle.
# Public plan_engine.parse_plan/run_plan names remain unchanged.
from plan_engine_parse import (PlanAbort, _below, parse_plan)
from plan_engine_human import (PausePlanner, plan_move, plan_typing, windmouse)
import plan_engine_exec as _exec

# The executor's Random Package shuffle uses the shared C#-compatible helper.
# Bind it explicitly at the split-module boundary so facade consumers cannot
# hit a late NameError when the first shuffled package starts.
_exec._below = _below
run_plan = _exec.run_plan
