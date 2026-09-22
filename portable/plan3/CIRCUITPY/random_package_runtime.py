# Low-memory Random Package executor.
# Imported only when a route actually contains RPKG or PGROUP; normal boot and
# mouse routes stay on the proven engine-free runner.
import random


def _op(raw):
    line = raw.strip()
    if not line or line.startswith("#"):
        return None, ""
    split = line.find("|")
    if split < 0:
        return line.upper(), ""
    if split < 1:
        raise ValueError("invalid package route line")
    return line[:split].upper(), line[split + 1:]


def _read_items(fh):
    items = [[]]
    depth = 0
    while True:
        raw = fh.readline()
        if not raw:
            raise ValueError("RPKG without ENDPKG")
        op, _ = _op(raw)
        if op in ("RPKG", "PGROUP"):
            depth += 1; items[-1].append(raw)
        elif op == "ENDPKG":
            if depth == 0: return items
            depth -= 1; items[-1].append(raw)
        elif op == "PKGITEM" and depth == 0:
            items.append([])
        else:
            items[-1].append(raw)


def _take_items(lines, start):
    items = [[]]
    depth = 0
    i = start
    while i < len(lines):
        op, _ = _op(lines[i])
        if op in ("RPKG", "PGROUP"):
            depth += 1; items[-1].append(lines[i])
        elif op == "ENDPKG":
            if depth == 0: return items, i + 1
            depth -= 1; items[-1].append(lines[i])
        elif op == "PKGITEM" and depth == 0:
            items.append([])
        else:
            items[-1].append(lines[i])
        i += 1
    raise ValueError("RPKG without ENDPKG")


def _package(args, items, owner, expected, action):
    fields = args.split(",")
    if len(fields) != 3:
        raise ValueError("RPKG needs mode,min,max")
    mode = fields[0].strip().lower()
    if mode in ("shuffleall", "all"):
        mode = "all"
    elif mode in ("randomsubset", "pick", "some"):
        mode = "pick"
    else:
        raise ValueError("unknown RPKG mode: " + fields[0])
    mn, mx = int(fields[1]), int(fields[2])
    if not items:
        raise ValueError("RPKG has no items")
    order = list(range(len(items)))
    for k in range(len(order) - 1, 0, -1):
        j = random.randrange(k + 1)
        order[k], order[j] = order[j], order[k]
    if mode == "pick":
        if mn < 0 or mx < mn:
            raise ValueError("RPKG counts out of range")
        mx = min(mx, len(items))
        if mn > mx:
            raise ValueError("RPKG minCount exceeds item count")
        count = mn if mn == mx else random.randint(mn, mx)
        order = order[:count]
    owner.emit("EVT|DEBUG|STEP/RPKG mode=%s selected=%d total=%d" %
               (mode, len(order), len(items)))
    for index in order:
        if not _lines(items[index], owner, expected, action):
            return False
    return True


def _lines(lines, owner, expected, action):
    i = 0
    while i < len(lines):
        op, args = _op(lines[i])
        if op is None:
            i += 1; continue
        if op == "RPKG":
            items, i = _take_items(lines, i + 1)
            if not _package(args, items, owner, expected, action): return False
            continue
        if op in ("PKGITEM", "ENDPKG", "PGROUP", "PARITEM", "ENDPAR", "LOOP", "LOOPTIME", "ENDLOOP"):
            raise ValueError("unsupported nested package command: " + op)
        if op in ("PLAN", "SCREEN", "SPEED"):
            i += 1; continue
        if not action(owner, op, args, expected): return False
        i += 1
    return True


def run_file_package(fh, args, owner, expected, action):
    return _package(args, _read_items(fh), owner, expected, action)


def _parallel_group(owner, fh, expected, action):
    branches = []
    branch_start = fh.tell()
    while True:
        boundary = fh.tell()
        raw = fh.readline()
        if not raw:
            raise ValueError("PGROUP without ENDPAR")
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        split = line.find("|")
        op = line.upper() if split < 0 else line[:split].upper()
        if op == "PARITEM":
            if fh.tell() <= branch_start:
                raise ValueError("empty Parallel Group branch")
            branches.append([branch_start, boundary, branch_start])
            branch_start = fh.tell()
        elif op == "ENDPAR":
            if fh.tell() <= branch_start:
                raise ValueError("empty Parallel Group branch")
            branches.append([branch_start, boundary, branch_start])
            after_group = fh.tell()
            break
    if len(branches) < 2:
        raise ValueError("Parallel Group needs at least two branches")
    owner.emit("EVT|DEBUG|STEP/PGROUP branches=%d" % len(branches))
    live = len(branches)
    while live:
        for branch in branches:
            cursor, end = branch[2], branch[1]
            if cursor >= end:
                continue
            fh.seek(cursor)
            raw = fh.readline()
            branch[2] = fh.tell()
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            split = line.find("|")
            if split < 1:
                raise ValueError("invalid Parallel Group command")
            op = line[:split].upper()
            args = line[split + 1:]
            if op == "PLAN":
                if args != "2":
                    raise ValueError("unsupported PLAN version in Parallel Group")
                continue
            if op not in ("DELAY", "KEY", "TYPE", "RMOUSE", "MOVETO", "KDOWN", "KUP", "BEEP"):
                raise ValueError("unsupported Parallel Group command: " + op)
            if not action(owner, op, args, expected):
                fh.seek(after_group)
                return False
        live = sum(1 for branch in branches if branch[2] < branch[1])
    fh.seek(after_group)
    return True


def run_parallel_group(fh, args, owner, expected, action):
    if args:
        raise ValueError("PGROUP takes no arguments")
    return _parallel_group(owner, fh, expected, action)


def run_route_special(op, fh, args, owner, expected, action, arm_send):
    if op == "RPKG":
        return run_file_package(fh, args, owner, expected, action)
    if op == "PGROUP":
        return run_parallel_group(fh, args, owner, expected, action)
    fields = args.split(",")
    if len(fields) != 3:
        raise ValueError("WSND needs threshold,min_ms,timeout_ms")
    threshold, minimum, timeout = (int(value) for value in fields)
    if threshold < 0 or minimum < 0 or timeout < 0:
        raise ValueError("WSND values must be non-negative")
    owner.emit("EVT|DEBUG|STEP/WSND %d,%d,%d" % (threshold, minimum, timeout))
    reply = arm_send(owner, "WSND|%d,%d,%d" % (threshold, minimum, timeout), timeout / 1000 + 3)
    if reply.startswith("ERR|"):
        raise RuntimeError("ARM WSND rejected: " + reply)
    owner.emit("EVT|DEBUG|STEP/WSND reply=" + reply)
    return True
