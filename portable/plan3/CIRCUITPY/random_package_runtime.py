# Low-memory Random Package executor.
# Imported only when a route actually contains RPKG; normal boot and mouse routes
# stay on the proven engine-free runner.
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
