"""Bounded recovery-call wrapper driven by the surrounding IFLUX checkpoint."""

ATTEMPT_DELAYS_SECONDS = (5, 10, 20, 40, 80)
RECOVERY_FILES = ("launch_recovery.txt", "main_recovery.txt")


def _body(text):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for index, raw in enumerate(lines):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line != "PLAN|2":
            raise ValueError("recovery file must start with PLAN|2")
        return "\n".join(lines[index + 1:])
    raise ValueError("empty recovery file")


def wrap(text, light_args, file_name, delays=ATTEMPT_DELAYS_SECONDS):
    """Inline one recovery tab as five attempts and re-check the parent's DC lux range.

    IFLUX true means the disconnect screen is still present. IFLUX false jumps to the
    success label and returns to the caller. Final failure is non-fatal and safely
    returns; hardware GP6/BEEP signalling remains an optional follow-up until every
    supported runtime context provides a buzzer handler.
    """
    if file_name not in RECOVERY_FILES:
        return text
    if light_args is None or len(light_args) != 5:
        raise ValueError("Run/Call DC Recovery must be inside a Wait For Light If branch")
    body = _body(text)
    tag = "LAUNCH" if file_name.startswith("launch_") else "MAIN"
    done = "__%s_DC_RECOVERY_OK" % tag
    out = ["PLAN|2", "# bounded %s DC recovery" % tag]
    lux = ",".join(str(int(v)) for v in light_args)
    for attempt, delay in enumerate(delays, 1):
        out.append("# recovery attempt %d/%d" % (attempt, len(delays)))
        out.append("DELAY|%d000" % int(delay))
        if body.strip():
            out.append(body)
        out.append("IFLUX|" + lux)
        out.append("# disconnect remains")
        out.append("ELSE")
        out.append("GOTO|" + done)
        out.append("ENDIF")
    out.append("# final failure: no-crash continuation; optional GP6 buzzer is a follow-up")
    out.append("LABEL|" + done)
    return "\n".join(out) + "\n"
