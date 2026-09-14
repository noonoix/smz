from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEP = ROOT / "ams-shell/src/Ams.UI/Models/StepDefinitions.cs"
TPL = ROOT / "tools/PlanExporter.cs.tpl"

step_text = STEP.read_text(encoding="utf-8")
step_marker = '        ["waitForLight"] = new StepDefinition\n'
step_def = '''        ["liveLightStateLoop"] = new StepDefinition
        {
            Label = "Live Light State Loop (BH1750)", ColorResourceKey = "StepFindImageBrush", DefaultDelay = 0,
            Fields = new FieldDef[]
            {
                new("pollMs", "Sensor poll interval (ms)", FieldKind.Int, "250"),
                new("stableMs", "State stability/debounce (ms)", FieldKind.Int, "750"),
                new("hysteresisLux", "Hysteresis (lux)", FieldKind.Int, "20"),
                new("timeoutMs", "Sensor timeout (ms)", FieldKind.Int, "1500"),
                new("fallback", "Unsafe fallback", FieldKind.Combo, "STOP", new[] { "STOP", "FIRST" }),
                new("routes", "Routes: id:low:high:file.txt, one or more separated by commas", FieldKind.Multiline, "dark:0:100:dark.plan.txt,bright:160:400:bright.plan.txt"),
            },
            Summarize = s => "Live Light State Loop · " + PropEx.GetString(s.Props, "routes", "").Trim(),
            Commands = s => new[]
            {
                "STATELOOP|poll=" + Math.Max(25, PropEx.GetInt(s.Props, "pollMs", 250))
                + "|stable=" + Math.Max(0, PropEx.GetInt(s.Props, "stableMs", 750))
                + "|hysteresis=" + Math.Max(0, PropEx.GetInt(s.Props, "hysteresisLux", 20))
                + "|timeout=" + Math.Max(25, PropEx.GetInt(s.Props, "timeoutMs", 1500))
                + "|fallback=" + PropEx.GetString(s.Props, "fallback", "STOP").ToUpperInvariant()
                + "|routes=" + PropEx.GetString(s.Props, "routes", "").Replace("\\r", "").Replace("\\n", ""),
            },
        },
'''
if "[\"liveLightStateLoop\"]" not in step_text:
    if step_marker not in step_text:
        raise SystemExit("StepDefinitions: waitForLight marker not found")
    step_text = step_text.replace(step_marker, step_def + step_marker, 1)
    STEP.write_text(step_text, encoding="utf-8", newline="\n")

tpl = TPL.read_text(encoding="utf-8")
case_marker = '                case "waitForLight":EmitWaitForLight(n);return;\n'
case_line = '                case "liveLightStateLoop":EmitLiveLightStateLoop(n);return;\n'
if case_line not in tpl:
    if case_marker not in tpl:
        raise SystemExit("PlanExporter template: waitForLight switch marker not found")
    tpl = tpl.replace(case_marker, case_line + case_marker, 1)

method_marker = '        private void EmitWaitForLight(StepNode n)'
method = '''        private void EmitLiveLightStateLoop(StepNode n)
        {
            var p = n.Props;
            var routes = PropEx.GetString(p, "routes", "").Replace("\\r", "").Replace("\\n", "").Trim();
            if (routes.Length == 0 || routes.Contains("|") || routes.Contains("\\\\"))
            {
                Error(n, "live light routes are required and must be one-line id:low:high:file.txt entries");
                return;
            }
            foreach (var raw in routes.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
            {
                var bits = raw.Split(':');
                if (bits.Length != 4 || bits[0].Length == 0 || !bits[3].EndsWith(".txt", StringComparison.OrdinalIgnoreCase))
                {
                    Error(n, "bad live light route '" + raw + "' (use id:low:high:file.txt)");
                    return;
                }
                if (!int.TryParse(bits[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out _)
                    || !int.TryParse(bits[2], NumberStyles.Integer, CultureInfo.InvariantCulture, out _))
                {
                    Error(n, "bad lux range in live light route '" + raw + "'");
                    return;
                }
            }
            var fallback = PropEx.GetString(p, "fallback", "STOP").ToUpperInvariant();
            if (fallback is not ("STOP" or "FIRST"))
            {
                Error(n, "live light fallback must be STOP or FIRST");
                return;
            }
            var poll = Math.Max(25, PropEx.GetInt(p, "pollMs", 250));
            var stable = Math.Max(0, PropEx.GetInt(p, "stableMs", 750));
            var hysteresis = Math.Max(0, PropEx.GetInt(p, "hysteresisLux", 20));
            var timeout = Math.Max(poll, PropEx.GetInt(p, "timeoutMs", 1500));
            Emit(n, new[] { "STATELOOP|poll=" + poll + "|stable=" + stable + "|hysteresis=" + hysteresis
                + "|timeout=" + timeout + "|fallback=" + fallback + "|routes=" + routes }, "STATELOOP");
        }

'''
if "EmitLiveLightStateLoop" not in tpl:
    if method_marker not in tpl:
        raise SystemExit("PlanExporter template: EmitWaitForLight marker not found")
    tpl = tpl.replace(method_marker, method + method_marker, 1)

payload_marker = '        payloads.Add((readmePath, BuildReadme(bundle.Root, Path.GetFileName(sourceName), machine)));\n'
payload_line = '        payloads.Add((Path.Combine(dir, "live_light_guard.py"), BuildLightGuardPy()));\n'
if payload_line not in tpl:
    if payload_marker not in tpl:
        raise SystemExit("PlanExporter template: payload marker not found")
    tpl = tpl.replace(payload_marker, payload_marker + payload_line, 1)

known_old = '"INCLUDE","BEEP"};'
known_new = '"INCLUDE","BEEP","STATELOOP"};'
if known_new not in tpl:
    if known_old not in tpl:
        raise SystemExit("PlanExporter template: ValidatePlan op list marker not found")
    tpl = tpl.replace(known_old, known_new, 1)

build_marker = '    public static string BuildTypingPy() => TypingTemplate.Replace("\\r\\n", "\\n");\n'
build_line = '    public static string BuildLightGuardPy() => LightGuardTemplate.Replace("\\r\\n", "\\n");\n'
if build_line not in tpl:
    if build_marker not in tpl:
        raise SystemExit("PlanExporter template: BuildTypingPy marker not found")
    tpl = tpl.replace(build_marker, build_marker + build_line, 1)

light_guard = '''\n    private const string LightGuardTemplate = """"
# portable BH1750 state guard shared by canonical and memory-fit plan runtimes
class LightStateGuard:
    def __init__(self, states, stable_ms=750, hysteresis=0, sensor_timeout_ms=1500):
        self.states = tuple(states or ())
        self.stable_ms = max(0, int(stable_ms))
        self.hysteresis = max(0, int(hysteresis))
        self.sensor_timeout_ms = max(0, int(sensor_timeout_ms))
        self.active = None
        self.candidate = None
        self.candidate_since = None
        self.last_sample_ms = None

    def _inside(self, state, lux, widened=False):
        low, high = int(state["lo"]), int(state["hi"])
        if widened:
            low -= self.hysteresis
            high += self.hysteresis
        return low <= lux <= high

    def _eligible(self, lux):
        return [] if lux is None else [s for s in self.states if self._inside(s, lux)]

    def _active_still_valid(self, lux):
        if lux is None or self.active is None:
            return False
        return any(s["id"] == self.active and self._inside(s, lux, True) for s in self.states)

    def update(self, lux, now_ms):
        now_ms = int(now_ms)
        self.last_sample_ms = now_ms if lux is not None else self.last_sample_ms
        if lux is None:
            if self.last_sample_ms is None or now_ms - self.last_sample_ms > self.sensor_timeout_ms:
                return None
            return self.active
        if self.active is not None and self._active_still_valid(lux):
            eligible = self._eligible(lux)
            if len(eligible) == 1 and eligible[0]["id"] == self.active:
                self.candidate = None
                self.candidate_since = None
                return self.active
        eligible = self._eligible(lux)
        if len(eligible) != 1:
            self.candidate = None
            self.candidate_since = None
            return self.active if self.active is not None and self._active_still_valid(lux) else None
        state_id = eligible[0]["id"]
        if state_id != self.candidate:
            self.candidate = state_id
            self.candidate_since = now_ms
        if self.candidate_since is not None and now_ms - self.candidate_since >= self.stable_ms:
            self.active = state_id
            self.candidate = None
            self.candidate_since = None
            return self.active
        return self.active if self.active is not None else None

    def reset(self):
        self.active = None
        self.candidate = None
        self.candidate_since = None
        self.last_sample_ms = None


def state_spec(state_id, low, high, route):
    return {"id": str(state_id), "lo": int(low), "hi": int(high), "route": str(route)}

"""";
'''
if "private const string LightGuardTemplate" not in tpl:
    close_marker = '    private const string TypingTemplate = __ENGINE_TYPING_TEMPLATE__;\n'
    if close_marker not in tpl:
        raise SystemExit("PlanExporter template: template close marker not found")
    tpl = tpl.replace(close_marker, light_guard + close_marker, 1)

TPL.write_text(tpl, encoding="utf-8", newline="\n")
print("patched live light state exporter contract")
