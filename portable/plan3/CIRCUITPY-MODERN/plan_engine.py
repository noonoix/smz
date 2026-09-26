# Compatibility facade for the memory-split experimental bundle.
# Parsing is needed before execution, but importing the human/parallel/exec
# modules at the same time creates the highest transient heap peak on RP2040.
# Keep parse_plan/PlanAbort eager and defer the executor until the route source
# has been parsed, deleted, and collected by code.py.
import gc
from plan_engine_parse import (PlanAbort, _below, parse_plan)
gc.collect()

def run_plan(plan, ctx):
    gc.collect()
    import plan_engine_exec as executor
    # Random Package shuffle uses the shared C#-compatible helper.
    executor._below = _below
    return executor.run_plan(plan, ctx)
