#!/usr/bin/env python3
import sys, tempfile
from pathlib import Path
base=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(base/'CIRCUITPY'))
from cycle_runtime import ResumeArmStore, RootCycle

with tempfile.TemporaryDirectory() as td:
    store=ResumeArmStore(str(Path(td)/'armed'))
    releases=[]
    for expected in range(1,6):
        cycle=RootCycle(lambda: 0,None,store)
        cycle.auto_resume_enabled=True
        cycle.expired_naturally=True
        assert cycle.arm_natural_restart(lambda: releases.append('release'))
        assert store.restart_count()==expected
        assert store.is_armed()
        assert store.consume()
    blocked=RootCycle(lambda: 0,None,store)
    blocked.auto_resume_enabled=True
    blocked.expired_naturally=True
    assert not blocked.arm_natural_restart(lambda: releases.append('release'))
    assert blocked.restart_limit_reached and blocked.stopped
    assert store.restart_count()==5 and not store.is_armed()
    assert len(releases)==6
    blocked.reset_restart_session()
    assert store.restart_count()==0
    fresh=RootCycle(lambda: 0,None,store)
    fresh.auto_resume_enabled=True
    fresh.expired_naturally=True
    assert fresh.arm_natural_restart(lambda: releases.append('release'))
    assert store.restart_count()==1

assert (base/'CIRCUITPY/cycle_runtime.py').read_bytes()==(base/'CIRCUITPY-SPLIT/cycle_runtime.py').read_bytes()
assert (base/'CIRCUITPY/cycle_runtime.py').read_bytes()==(base/'tools/cycle_runtime.py').read_bytes()
print('persistent restart limit: 22 passed, 0 failed')
