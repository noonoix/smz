from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "portable/plan3/CIRCUITPY-SPLIT/plan_engine.py"
text = ENGINE.read_text(encoding="utf-8")

# Keep the memory-fit split runtime's parser contract aligned with canonical.
if "'ENDLOOP', 'WLIGHT', 'STATELOOP', 'MOVETO'" not in text:
    old = "'ENDLOOP', 'WLIGHT', 'MOVETO'"
    if old not in text:
        raise SystemExit("split engine: _OPS anchor not found")
    text = text.replace(old, "'ENDLOOP', 'WLIGHT', 'STATELOOP', 'MOVETO'", 1)

parser_branch = '''        elif op == 'STATELOOP':
            vals = {}
            for kv in fields[1:]:
                if '=' not in kv:
                    raise ValueError('line %d: STATELOOP wants key=value' % line_no)
                k, v = kv.split('=', 1)
                vals[k.strip().lower()] = v.strip()
            try:
                prm['poll'] = max(25, int(vals.get('poll', '250')))
                prm['stable'] = max(0, int(vals.get('stable', '750')))
                prm['hysteresis'] = max(0, int(vals.get('hysteresis', '0')))
                prm['timeout'] = max(prm['poll'], int(vals.get('timeout', '1500')))
            except Exception:
                raise ValueError('line %d: bad STATELOOP timing' % line_no)
            routes = []
            for raw_route in vals.get('routes', '').split(','):
                bits = raw_route.split(':')
                if len(bits) != 4 or not bits[0] or not bits[3].endswith('.txt'):
                    raise ValueError("line %d: bad STATELOOP route '%s'" % (line_no, raw_route))
                try:
                    lo, hi = int(bits[1]), int(bits[2])
                except Exception:
                    raise ValueError('line %d: bad STATELOOP lux range' % line_no)
                if hi < lo:
                    lo, hi = hi, lo
                routes.append({'id': bits[0], 'lo': lo, 'hi': hi, 'file': bits[3]})
            if not routes:
                raise ValueError('line %d: STATELOOP needs routes=' % line_no)
            prm['routes'] = routes
            prm['fallback'] = vals.get('fallback', 'STOP').upper()
            if prm['fallback'] not in ('STOP', 'FIRST'):
                raise ValueError('line %d: STATELOOP fallback must be STOP or FIRST' % line_no)
'''

if parser_branch not in text:
    parser_anchor = "        elif op == 'WLIGHT':\n            pos = fields[1].split(',') if len(fields) > 1 else []\n"
    if parser_anchor not in text:
        raise SystemExit("split engine: parser WLIGHT anchor not found")
    text = text.replace(parser_anchor, parser_branch + parser_anchor, 1)

helper = '''\n\nclass _LightStateChanged(Exception):
    def __init__(self, state_id):
        self.state_id = state_id


class _LiveLightSession:
    def __init__(self, prm, ctx):
        try:
            from live_light_guard import LightStateGuard, state_spec
        except ImportError as exc:
            raise ValueError('STATELOOP needs live_light_guard.py in the portable bundle') from exc
        self.ctx = ctx
        self.prm = prm
        self.routes = {r['id']: r for r in prm['routes']}
        specs = [state_spec(r['id'], r['lo'], r['hi'], r['file']) for r in prm['routes']]
        self.guard = LightStateGuard(specs, prm['stable'], prm['hysteresis'], prm['timeout'])
        self.current = None
        self.next_poll = -1

    def _lux(self):
        reader = getattr(self.ctx, 'read_lux', None) or getattr(self.ctx, 'light_lux', None)
        if reader is not None:
            try:
                value = reader()
                return None if value is None else float(value)
            except Exception:
                return None
        waiter = getattr(self.ctx, 'wait_light', None)
        if waiter is None:
            return None
        for route in self.prm['routes']:
            try:
                if waiter(route['lo'], route['hi'], 0, self.prm['poll'], 0):
                    return (route['lo'] + route['hi']) / 2.0
            except Exception:
                return None
        return None

    def poll(self, force=False):
        now = int(self.ctx.now() * 1000)
        if not force and self.next_poll > now:
            return
        self.next_poll = now + self.prm['poll']
        state_id = self.guard.update(self._lux(), now)
        if state_id is None:
            raise PlanAbort()
        if self.current is None:
            self.current = state_id
        elif state_id != self.current:
            self.current = state_id
            raise _LightStateChanged(state_id)


def _run_state_loop(prm, ctx, pos, pauses, inc):
    session = _LiveLightSession(prm, ctx)
    session.poll(True)
    while True:
        route = session.routes.get(session.current)
        if route is None:
            if prm['fallback'] == 'FIRST':
                route = prm['routes'][0]
                session.current = route['id']
            else:
                raise PlanAbort()
        try:
            sub = parse_plan(ctx.read_plan_file(route['file']))
        except Exception as exc:
            ctx.log('light route failed: ' + str(exc))
            raise PlanAbort()
        setattr(ctx, '_live_light_guard', session)
        try:
            run_plan(sub, ctx, _pos=pos, _pauses=pauses, _inc=inc + (route['file'],))
        except _LightStateChanged:
            continue
        finally:
            if getattr(ctx, '_live_light_guard', None) is session:
                delattr(ctx, '_live_light_guard')
        session.poll(True)
'''

if '_LiveLightSession' not in text:
    marker = "def run_plan(ops, ctx, _pos=None, _pauses=None, _inc=()):\n"
    if marker not in text:
        raise SystemExit("split engine: run_plan marker not found")
    text = text.replace(marker, helper + "\n" + marker, 1)

poll_hook = '''        _live_guard = getattr(ctx, '_live_light_guard', None)
        if _live_guard is not None:
            _live_guard.poll()
'''
if poll_hook not in text:
    gate = "        if _gate is not None and (not _gate()):\n            raise PlanAbort()\n"
    if gate not in text:
        raise SystemExit("split engine: gate hook not found")
    text = text.replace(gate, gate + poll_hook, 1)

executor_branch = '''        elif op == 'STATELOOP':
            _run_state_loop(prm, ctx, pos, pauses, inc)
'''
if executor_branch not in text:
    executor_anchor = "        elif op == 'WLIGHT':\n            ok = ctx.wait_light(prm['lo'], prm['hi'], prm['stable'], prm['to'], prm['mode'])\n"
    if executor_anchor not in text:
        raise SystemExit("split engine: executor WLIGHT anchor not found")
    text = text.replace(executor_anchor, executor_branch + executor_anchor, 1)

ENGINE.write_text(text, encoding='utf-8')
print('patched split STATELOOP runtime')
