import supervisor

_MARKER = "/.guard_verified_v3"


def _verified():
    try:
        with open(_MARKER, "r") as fh:
            return fh.read(1) == "1"
    except Exception:
        return False


if _verified():
    # The expensive validator and its temporary hash dictionaries are gone after
    # the first interpreter lifetime. The second lifetime loads only the runner.
    import guard_main  # noqa: F401 - guard_main owns the long-running loop
else:
    import guard_validate
    guard_validate.run()
    with open(_MARKER, "w") as fh:
        fh.write("1")
    supervisor.reload()

