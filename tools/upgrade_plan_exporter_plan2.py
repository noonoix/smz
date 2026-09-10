#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
p = root / 'tools' / 'PlanExporter.cs.tpl'
s = p.read_text(encoding='utf-8')

def method_span(src, signature):
    a = src.index(signature)
    b = src.index('{', a)
    depth = 0
    for i in range(b, len(src)):
        if src[i] == '{': depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0: return a, i + 1
    raise RuntimeError('unbalanced method: ' + signature)

def replace_method(src, signature, body):
    a,b = method_span(src, signature)
    return src[:a] + body.rstrip() + src[b:]

s = s.replace('using System.Text;\n', 'using System.Text;\n')
s = s.replace('private readonly Dictionary<StepNode, string> _numbering = new();',
'''private readonly Dictionary<StepNode, string> _numbering = new();
        private readonly HashSet<string> _labels = new(StringComparer.Ordinal);
        private readonly string _sourcePath;''')
s = s.replace('public Gen(AppSettings settings) => _settings = settings;',
'''public Gen(AppSettings settings, string sourcePath)
        {
            _settings = settings;
            _sourcePath = sourcePath;
        }''')
s = s.replace('var gen = new Gen(settings);', 'var gen = new Gen(settings, sourceName);')

emit_if = r'''        private int EmitIf(IList<StepNode> nodes, int i)
        {
            var n = nodes[i];
            StepNode? elseNode = null, endifNode = null;
            int j = i + 1;
            if (j < nodes.Count && IsMarker(nodes[j], "else")) { elseNode = nodes[j]; j++; }
            if (j < nodes.Count && IsMarker(nodes[j], "endif")) { endifNode = nodes[j]; j++; }
            if (endifNode is null)
                Error(n, "insertIfElse is on but the matching 'End If' marker is missing");
            if (n.Type == "findImage")
            {
                Error(n, "findImage needs machine vision - it cannot run on the Pico");
                CollectBlockers(n);
                foreach (var sub in new[] { elseNode, endifNode }) if (sub is not null) CollectBlockers(sub);
                return j;
            }
            var p = n.Props;
            if (n.Type == "waitForSound")
            {
                Lines.Add("IFSND|" + PropEx.GetInt(p, "threshold", 90) + "," + PropEx.GetInt(p, "minDurationMs", 60) + "," + PropEx.GetInt(p, "timeoutMs", 20000));
                Count("IFSND");
            }
            else
            {
                var (lo, hi, stable, timeout, mode) = LuxArgs(p);
                Lines.Add("IFLUX|" + lo + "," + hi + "," + stable + "," + timeout + "," + mode);
                Count("IFLUX");
            }
            Walk(n.Children);
            if (elseNode is not null) { Lines.Add("ELSE"); Markers++; Walk(elseNode.Children); }
            if (endifNode is not null) { Lines.Add("ENDIF"); Markers++; }
            EmitDelay(n);
            return j;
        }'''
s = replace_method(s, '        private int EmitIf(', emit_if)

emit_step = r'''        private void EmitStep(StepNode n)
        {
            switch (n.Type)
            {
                case "comment": EmitComment(n); return;
                case "delay": EmitDelayStep(n); return;
                case "randomMousePosition": EmitRandomMouse(n); return;
                case "mouseMove": EmitMouseMove(n); return;
                case "mouseClick": EmitMouseClick(n); return;
                case "mouseScroll": EmitMouseScroll(n); return;
                case "keystroke": EmitKeystroke(n); return;
                case "keyDown": EmitKeyState(n, true); return;
                case "keyUp": EmitKeyState(n, false); return;
                case "typeText": EmitTypeText(n); return;
                case "forLoop": EmitForLoop(n); return;
                case "waitForSound": EmitWaitForSound(n); return;
                case "waitForLight": EmitWaitForLight(n); return;
                case "label": EmitLabel(n); return;
                case "gotoLabel": EmitGoto(n); return;
                case "rawCommand": EmitRaw(n); return;
                case "randomPackage": EmitRandomPackage(n); return;
                case "parallelGroup": EmitParallelGroup(n); return;
                case "runExe": EmitLaunch(n, false); return;
                case "openFile": EmitLaunch(n, true); return;
                case "playAudio": EmitAudio(n); return;
                case "playScript": EmitInclude(n); return;
                case "findImage":
                    Error(n, "findImage needs machine vision - it cannot run on the Pico");
                    CollectBlockers(n); return;
                default:
                    Error(n, "unknown step type '" + n.Type + "' - this exporter does not know it (supported: the 23 app actions)"); return;
            }
        }'''
s = replace_method(s, '        private void EmitStep(', emit_step)

extra = r'''
        private int Vk(StepNode n, string name, string what)
        {
            if (KeyMap.VK.TryGetValue(name, out var vk) || VkAliases.TryGetValue(name, out vk)) return vk;
            Error(n, "unknown key name '" + name + "' for " + what); return 0;
        }

        private void KeyboardFlag(StepNode n)
        {
            if (PropEx.GetString(n.Props, "keyboardBoard", "default") == "promicro")
                Flag(n, "keyboard executor 'promicro' is bridge-mode only; on the portable plan the Pico types it");
        }

        private void EmitMouseScroll(StepNode n)
            => Emit(n, new[] { "WHEEL|" + PropEx.GetInt(n.Props, "delta", -1) }, "WHEEL");

        private void EmitKeystroke(StepNode n)
        {
            var p = n.Props; var keys = new List<int>();
            if (PropEx.GetBool(p, "modCtrl")) keys.Add(162);
            if (PropEx.GetBool(p, "modShift")) keys.Add(160);
            if (PropEx.GetBool(p, "modAlt")) keys.Add(164);
            if (PropEx.GetBool(p, "modWin")) keys.Add(91);
            var vk = Vk(n, PropEx.GetString(p, "key", "F4"), "keystroke"); if (vk == 0) return;
            keys.Add(vk); var (h0,h1)=Pair(PropEx.GetInt(p,"holdMin",0),PropEx.GetInt(p,"holdMax",0));
            var line="KEY|combo="+string.Join("+",keys); if(h1>0) line+="|hold="+h0+","+h1;
            KeyboardFlag(n); Emit(n,new[]{line},"KEY");
        }

        private void EmitKeyState(StepNode n, bool down)
        {
            var vk=Vk(n,PropEx.GetString(n.Props,"key","SHIFT"),down?"keyDown":"keyUp"); if(vk==0)return;
            KeyboardFlag(n); Emit(n,new[]{(down?"KDOWN|":"KUP|")+vk},down?"KDOWN":"KUP");
        }

        private void EmitWaitForSound(StepNode n)
        {
            var p=n.Props; int t=PropEx.GetInt(p,"threshold",90), m=PropEx.GetInt(p,"minDurationMs",60), to=PropEx.GetInt(p,"timeoutMs",20000);
            if(PropEx.GetBool(p,"armed"))
            {
                int act=PropEx.GetString(p,"act","left") switch {"right"=>2,"middle"=>3,_=>1};
                var(r0,r1)=Pair(PropEx.GetInt(p,"reactMin",80),PropEx.GetInt(p,"reactMax",180));
                var(h0,h1)=Pair(PropEx.GetInt(p,"holdMin",30),PropEx.GetInt(p,"holdMax",90));
                Emit(n,new[]{"TRGSND|"+t+","+m+","+to+","+act+","+r0+","+r1+","+h0+","+h1},"TRGSND");
            }
            else Emit(n,new[]{"WSND|"+t+","+m+","+to},"WSND");
        }

        private (int lo,int hi,int stable,int timeout,int mode) LuxArgs(Dictionary<string, object?> p)
        {
            int c=PropEx.GetInt(p,"luxCenter",1250), tol=Math.Max(1,PropEx.GetInt(p,"luxTolerance",50));
            return (Math.Max(0,c-tol),c+tol,Math.Max(0,(int)Math.Round(PropEx.GetDouble(p,"stableSec",2)*1000)),PropEx.GetInt(p,"timeoutMs",20000),PropEx.GetString(p,"sampleMode","hires")=="lowres"?1:0);
        }

        private void EmitLabel(StepNode n)
        {
            var name=PropEx.GetString(n.Props,"label","label1").Trim();
            if(name.Length==0||name.Contains('=')||name.Contains('|')) { Error(n,"bad label name '"+name+"'"); return; }
            if(!_labels.Add(name)) { Error(n,"duplicate label '"+name+"' - the engine rejects duplicates"); return; }
            Emit(n,new[]{"LABEL|"+name},"LABEL");
        }
        private void EmitGoto(StepNode n)
        {
            var name=PropEx.GetString(n.Props,"label").Trim(); if(name.Length==0){Error(n,"Go To Label with no label chosen");return;}
            Emit(n,new[]{"GOTO|"+name},"GOTO");
        }
        private void EmitRaw(StepNode n)
        {
            var cmd=PropEx.GetString(n.Props,"cmd","PING").Trim();
            if(cmd.Length==0||cmd.Contains('\n')||cmd.Contains('\r')){Error(n,"raw command must be one non-empty line");return;}
            Emit(n,new[]{"RAW|"+cmd},"RAW");
        }

        private void EmitRandomPackage(StepNode n)
        {
            var kids=n.Children.Where(c=>!c.IsDisabled&&!IsMarker(c)).ToList();
            if(kids.Count==0){Error(n,"random package has no enabled children");return;}
            if(kids.Any(c=>Conditional.Contains(c.Type)&&PropEx.GetBool(c.Props,"insertIfElse"))){Error(n,"an If/Else structure cannot live inside a Random Package");return;}
            var mode=PropEx.GetString(n.Props,"mode","shuffleAll"); int mn=1,mx=kids.Count; string em="all";
            if(mode=="randomSubset") { em="pick"; mn=Math.Max(0,PropEx.GetInt(n.Props,"minCount",1)); mx=Math.Min(kids.Count,PropEx.GetInt(n.Props,"maxCount",10)); if(mn>mx)(mn,mx)=(mx,mn); }
            else if(mode!="shuffleAll"){Error(n,"unknown random package mode '"+mode+"'");return;}
            Lines.Add("RPKG|"+em+","+mn+","+mx); Count("RPKG");
            for(int i=0;i<kids.Count;i++){if(i>0)Lines.Add("PKGITEM"); Walk(new List<StepNode>{kids[i]});}
            Lines.Add("ENDPKG"); EmitDelay(n);
        }

        private static readonly HashSet<string> ParallelOk = new(){"mouseMove","mouseClick","mouseScroll","keystroke","keyDown","keyUp","typeText","delay","rawCommand","comment"};
        private void EmitParallelGroup(StepNode n)
        {
            var kids=n.Children.Where(c=>!c.IsDisabled&&!IsMarker(c)).ToList();
            if(kids.Count<2){Error(n,"a Parallel Group needs at least two enabled branches");return;}
            foreach(var c in kids) if(!ParallelOk.Contains(c.Type)) Error(c,"'"+c.Type+"' cannot live inside a Parallel Group on the Pico");
            if(Errors.Count>0)return;
            Lines.Add("PGROUP");Count("PGROUP");for(int i=0;i<kids.Count;i++){if(i>0)Lines.Add("PARITEM");Walk(new List<StepNode>{kids[i]});}Lines.Add("ENDPAR");EmitDelay(n);
        }

        private static string QuoteRun(string value)=>value.Contains(' ')?"\""+value+"\"":value;
        private void EmitRunMacro(StepNode n,string command,string kind)
        {
            string enc;try{enc=PctType(command);}catch(FormatException ex){Error(n,ex.Message);return;}
            Emit(n,new[]{"# "+kind,"KEY|combo=91+82|hold=40,90","DELAY|350,650","TYPE|text="+enc,"DELAY|140,260","KEY|combo=13|hold=40,90","DELAY|600,1200"},kind);
        }
        private void EmitLaunch(StepNode n,bool shellOpen)
        {
            var p=n.Props;var path=PropEx.GetString(p,"path").Trim();if(path.Length==0){Error(n,"no path set");return;}
            var args=PropEx.GetString(p,"args");var state=PropEx.GetString(p,"windowState","normal");
            string cmd;if(state=="minimized")cmd="cmd /c start /min \"\" "+QuoteRun(path)+(args.Length>0?" "+args:"");
            else {if(state=="maximized")Flag(n,"'maximized' cannot be expressed through the Run box - launching visible/normal");cmd=QuoteRun(path)+(args.Length>0?" "+args:"");}
            EmitRunMacro(n,cmd,shellOpen?"openFile":"runExe");
        }
        private void EmitAudio(StepNode n)
        {
            var p=n.Props;var path=PropEx.GetString(p,"path").Trim();if(path.Length==0){Error(n,"no audio path set");return;}
            if(PropEx.GetString(p,"mode","playerMacro")!="playerMacro"){Error(n,"playAudio mode is PC-only; use playerMacro on the Pico");return;}
            var esc=path.Replace("'","''");var cmd=path.EndsWith(".wav",StringComparison.OrdinalIgnoreCase)?"powershell -w hidden -c \"(New-Object Media.SoundPlayer '"+esc+"').PlaySync()\"":"powershell -w hidden -c \"Add-Type -AssemblyName presentationCore;$p=New-Object System.Windows.Media.MediaPlayer;$p.Open([uri]'"+esc+"');$p.Play()\"";
            EmitRunMacro(n,cmd,"playAudio");
        }
        private void EmitInclude(StepNode n)
        {
            var raw=PropEx.GetString(n.Props,"path").Trim();if(raw.Length==0){Error(n,"no .amsj path set");return;}
            var full=Path.IsPathRooted(raw)?raw:Path.GetFullPath(Path.Combine(Path.GetDirectoryName(Path.GetFullPath(_sourcePath))??".",raw));
            if(!File.Exists(full)){Error(n,"playScript child not found: "+raw);return;}
            var baseName=Path.GetFileNameWithoutExtension(full);if(baseName.Any(ch=>ch<32||ch>126||"/\\:|%".Contains(ch))){Error(n,"playScript file name cannot live on the Pico drive");return;}
            Emit(n,new[]{"INCLUDE|file="+baseName+".txt"},"INCLUDE");
        }
'''
anchor = '        private void EmitForLoop(StepNode n)'
s = s.replace(anchor, extra + '\n' + anchor)

# PLAN|2 mouseMove has a native MOVETO op.
old_move = method_span(s, '        private void EmitMouseMove(')
new_move = r'''        private void EmitMouseMove(StepNode n)
        {
            int x=PropEx.GetInt(n.Props,"x",600),y=PropEx.GetInt(n.Props,"y",497);
            if(!PropEx.GetBool(n.Props,"human",true)){Emit(n,new[]{"MOVETO|x="+x+"|y="+y+"|human=0"},"MOVETO");return;}
            Emit(n,new[]{"MOVETO|x="+x+"|y="+y+Tuning(n,(1,1,0,0))},"MOVETO");
        }'''
s = s[:old_move[0]] + new_move + s[old_move[1]:]

# Share the same lux argument routine.
start,end=method_span(s,'        private void EmitWaitForLight(')
new_light=r'''        private void EmitWaitForLight(StepNode n)
        {
            var p=n.Props;var(lo,hi,stable,to,mode)=LuxArgs(p);var head="WLIGHT|"+lo+","+hi+","+stable+","+to+","+mode;
            if(PropEx.GetBool(p,"armed")){var vk=Vk(n,PropEx.GetString(p,"key","E"),"waitForLight armed key");if(vk==0)return;var(h0,h1)=Pair(PropEx.GetInt(p,"holdMin",30),PropEx.GetInt(p,"holdMax",90));var(r0,r1)=Pair(PropEx.GetInt(p,"reactMin",80),PropEx.GetInt(p,"reactMax",180));head+="|key="+vk+","+h0+","+h1+"|react="+r0+","+r1;}
            Emit(n,new[]{head},"WLIGHT");
        }'''
s=s[:start]+new_light+s[end:]

# Replace validator with full PLAN|2 structural validator.
validator=r'''    private static void ValidatePlan(string text)
    {
        int loops=0,ifs=0,packages=0,groups=0; bool first=true; var labels=new HashSet<string>(StringComparer.Ordinal);var gotos=new List<string>();
        var known=new HashSet<string>{"PLAN","SCREEN","SPEED","DELAY","LOOP","LOOPTIME","ENDLOOP","RMOUSE","MOVETO","CLICK","TYPE","WLIGHT","WSND","TRGSND","IFSND","IFLUX","ELSE","ENDIF","KEY","KDOWN","KUP","WHEEL","LABEL","GOTO","RAW","RPKG","PKGITEM","ENDPKG","PGROUP","PARITEM","ENDPAR","INCLUDE","BEEP"};
        var lines=text.Split('\n');
        for(int li=0;li<lines.Length;li++)
        {
            var line=lines[li].Trim();if(line.Length==0||line.StartsWith('#'))continue;var f=line.Split('|');var op=f[0];
            void Bad(string why)=>throw new PlanBlockedException(new[]{"PlanExporter BUG: line "+(li+1)+": "+why+" (please report)"});
            if(!known.Contains(op))Bad("unknown op '"+op+"'");
            if(first&&(op!="PLAN"||f.Length<2||f[1]!="2"))Bad("PLAN must be first with version 2");
            if(op=="PLAN"&&!first)Bad("duplicate/non-first PLAN");
            if(op is "LOOP" or "LOOPTIME")loops++; else if(op=="ENDLOOP"){if(--loops<0)Bad("ENDLOOP without LOOP");}
            if(op is "IFSND" or "IFLUX")ifs++; else if(op=="ELSE"){if(ifs<=0)Bad("ELSE without IF");} else if(op=="ENDIF"){if(--ifs<0)Bad("ENDIF without IF");}
            if(op=="RPKG")packages++;else if(op=="PKGITEM"&&packages<=0)Bad("PKGITEM outside RPKG");else if(op=="ENDPKG"){if(--packages<0)Bad("ENDPKG without RPKG");}
            if(op=="PGROUP")groups++;else if(op=="PARITEM"&&groups<=0)Bad("PARITEM outside PGROUP");else if(op=="ENDPAR"){if(--groups<0)Bad("ENDPAR without PGROUP");}
            if(op=="LABEL"){if(f.Length<2||f[1].Length==0||!labels.Add(f[1]))Bad("bad/duplicate LABEL");}
            if(op=="GOTO"){if(f.Length<2||f[1].Length==0)Bad("empty GOTO");gotos.Add(f[1]);}
            if(op=="INCLUDE"&&(!HasKv(f,"file",out var file)||file.Length==0||file.Any(ch=>ch<32||ch>126||"/\\:|%".Contains(ch))))Bad("unsafe INCLUDE filename");
            first=false;
        }
        if(loops!=0||ifs!=0||packages!=0||groups!=0)throw new PlanBlockedException(new[]{"PlanExporter BUG: unclosed PLAN|2 container (please report)"});
        foreach(var g in gotos)if(!labels.Contains(g))throw new PlanBlockedException(new[]{"PlanExporter BUG: GOTO target '"+g+"' is undefined (please report)"});
    }'''
s=replace_method(s,'    private static void ValidatePlan(',validator)

# Refresh stale contract prose without altering behavior.
for a,b in [('PLAN|1','PLAN|2'),('gen-1','PLAN|2'),('Gen-1','PLAN|2'),('0.9.64b','0.9.66'),('firmware/code64b/plan_engine.py','portable/plan3/CIRCUITPY/plan_engine.py')]: s=s.replace(a,b)
p.write_text(s,encoding='utf-8',newline='\n')
print('PLAN2 parity migration applied')
