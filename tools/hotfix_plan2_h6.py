#!/usr/bin/env python3
"""Apply PLAN2 h6 lifecycle and interruptible-typing fixes."""
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
FW = ROOT / "ams-shell" / "src" / "Ams.UI" / "Services" / "PicoFirmwareExporter.cs"
MARKER = "PLAN2_H6_CONTROL_FIX"


def once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{label}: anchor count {n}, expected 1")
    return text.replace(old, new, 1)


s = FW.read_text(encoding="utf-8")
if MARKER not in s:
    s = once(s, "        def handle_keyboard(line, head):\n", "        def handle_keyboard(line, head, plan_mode=False):\n", "keyboard signature")

    s = once(
        s,
        '''                for ch in txt:
                    pump_arm()               # v0.9.60e - the arm is drained even mid-typing
                    if serial is not None and serial.in_waiting:   # v0.9.60e - no USB RX overflow
                        buffer.extend(serial.read(serial.in_waiting))   #   during a long chunk
                    kc, sh = _ascii_key(ch)''',
        '''                for ch in txt:
                    pump_arm()               # v0.9.60e - the arm is drained even mid-typing
                    if plan_mode:
                        # PLAN2_H6_CONTROL_FIX: service GP4 between every character. A Stop
                        # edge aborts portable typing through the canonical PlanAbort path.
                        poll_keypad()
                        if not engine_on:
                            return "ABORT|KTEXT"
                    if serial is not None and serial.in_waiting:   # v0.9.60e - no USB RX overflow
                        buffer.extend(serial.read(serial.in_waiting))   #   during a long chunk
                    kc, sh = _ascii_key(ch)''',
        "typing keypad poll",
    )

    s = once(
        s,
        '''                    if hmax > 0:
                        time.sleep((hmin + random.random() * (hmax - hmin if hmax > hmin else 0)) / 1000)
                return "OK|KTEXT"''',
        '''                    if hmax > 0:
                        _type_delay = hmin + random.random() * (hmax - hmin if hmax > hmin else 0)
                        if plan_mode:
                            if not _plan_sleep_ms(_type_delay):
                                return "ABORT|KTEXT"
                        else:
                            time.sleep(_type_delay / 1000)
                return "OK|KTEXT"''',
        "interruptible typing delay",
    )

    s = once(
        s,
        '''            def ktext(self, hmin, hmax, text):
                handle_keyboard("KTEXT|%d,%d,%s" % (hmin, hmax, text), "KTEXT")''',
        '''            def ktext(self, hmin, hmax, text):
                _typed = handle_keyboard("KTEXT|%d,%d,%s" % (hmin, hmax, text), "KTEXT", True)
                if _typed == "ABORT|KTEXT":
                    raise _pe.PlanAbort()''',
        "plan typing abort bridge",
    )

    s = once(
        s,
        '''            try:
                _pe.run_plan(_plan_cache, _PlanCtx())
            except _pe.PlanAbort:
                release_all_buttons(force=True)   # v0.9.64b - full shield on the abort path
            except Exception as exc:
                # v0.9.62 - ALWAYS reported (was PLAN_DEBUG-only: a swallowed error read as a
                # silent death). 3 LED flashes = run fault, visible with no PC attached.
                print("plan: run error:", exc)
                led_fault(3)
                release_all_buttons(force=True)   # v0.9.64b - full shield on the error path
            return True''',
        '''            try:
                _pe.run_plan(_plan_cache, _PlanCtx())
                return "done"                     # PLAN2_H6_CONTROL_FIX: finite plan completed
            except _pe.PlanAbort:
                release_all_buttons(force=True)   # v0.9.64b - full shield on the abort path
                return "abort"
            except Exception as exc:
                # v0.9.62 - ALWAYS reported (was PLAN_DEBUG-only: a swallowed error read as a
                # silent death). 3 LED flashes = run fault, visible with no PC attached.
                print("plan: run error:", exc)
                led_fault(3)
                release_all_buttons(force=True)   # v0.9.64b - full shield on the error path
                return "error"''',
        "plan completion result",
    )

    s = once(
        s,
        '''                    if engine_on and not engine_paused and host_quiet and loop_due():
                        _completed_pass = False
                        if plan_pass():            # v0.9.61 - a portable plan takes precedence
                            passes += 1
                            _completed_pass = True
                        elif states:
                            standalone_pass()
                            passes += 1
                            _completed_pass = True
                        if _completed_pass and not loop_due():
                            # PLAN2_H5_CONTROL_FIX: natural once/times/timed completion is a
                            # real Stop. Turn the engine and pause state off and mirror it via
                            # Num Lock, so the next GP4 edge starts with one press.
                            engine_on = False
                            engine_paused = False
                            release_all_buttons()
                            tap_key(Keycode.KEYPAD_NUMLOCK)
                    time.sleep(0.02)''',
        '''                    if engine_on and not engine_paused and host_quiet and loop_due():
                        _plan_result = plan_pass()  # v0.9.61 - a portable plan takes precedence
                        if _plan_result:
                            passes += 1
                            if _plan_result == "done":
                                # PLAN2_H6_CONTROL_FIX: a finite portable plan owns its loop
                                # policy internally. Its return is a real natural Stop even when
                                # the legacy light-state LOOP_MODE is "forever".
                                engine_on = False
                                engine_paused = False
                                release_all_buttons()
                                tap_key(Keycode.KEYPAD_NUMLOCK)
                        elif states:
                            standalone_pass()
                            passes += 1
                            if not loop_due():
                                engine_on = False
                                engine_paused = False
                                release_all_buttons()
                                tap_key(Keycode.KEYPAD_NUMLOCK)
                    time.sleep(0.02)''',
        "portable natural completion",
    )

    FW.write_text(s, encoding="utf-8", newline="\n")
    print("h6: finite-plan completion and interruptible typing applied")
else:
    print("h6: fixes already applied")

out = FW.read_text(encoding="utf-8")
for required in (
    'def handle_keyboard(line, head, plan_mode=False):',
    'return "ABORT|KTEXT"',
    'raise _pe.PlanAbort()',
    'return "done"',
    '_plan_result == "done"',
):
    assert required in out, required
print("PLAN2 h6 hotfix OK")
