#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
p=root/'tools'/'plan_exporter_test_step.cs.inc'
s=p.read_text(encoding='utf-8')
if 'PLAN2_PARITY_TESTS' in s:
 print('PLAN2 parity tests already applied');raise SystemExit(0)
s=s.replace('// ── Step 59:', '// PLAN2_PARITY_TESTS\n        // ── Step 59:',1)
s=s.replace('Assert(pexMove.Text.Contains("RMOUSE|region=700,400,1,1|before=60,220|after=80,280|curve=20,40|mid=6:80,250|over=12|idle=1,1:0,0\\n"),\n                "v0.9.65: mouseMove compiles to the deterministic 1x1 region with idle explicitly off");', 'Assert(pexMove.Text.Contains("MOVETO|x=700|y=400|before=60,220|after=80,280|curve=20,40|mid=6:80,250|over=12|idle=1,1:0,0\\n"),\n                "v0.9.66: mouseMove emits native PLAN|2 MOVETO");')
s=s.replace('Assert(pexNoHuman.Flags.Any(f => f.Contains("instant (non-human) move")),\n                "v0.9.65: human=false is flagged, never silent");','Assert(pexNoHuman.Text.Contains("MOVETO|x=5|y=6|human=0\\n"),\n                "v0.9.66: human=false emits native non-human MOVETO");')
a=s.index('            // the 23-action x port matrix:')
b=s.index('            // typing blockers',a)
block=r'''            // PLAN|2 parity matrix: all portable actions emit; only explicit hardware/clipboard blockers remain.
            var pexParity = new List<StepNode>
            {
                PexStep("waitForSound", new Dictionary<string, object?> { ["threshold"] = 91, ["minDurationMs"] = 70, ["timeoutMs"] = 8000 }),
                PexStep("keystroke", new Dictionary<string, object?> { ["modCtrl"] = true, ["key"] = "A" }),
                PexStep("keyDown", new Dictionary<string, object?> { ["key"] = "SHIFT" }),
                PexStep("keyUp", new Dictionary<string, object?> { ["key"] = "SHIFT" }),
                PexStep("mouseScroll", new Dictionary<string, object?> { ["delta"] = -3 }),
                PexStep("label", new Dictionary<string, object?> { ["label"] = "again" }),
                PexStep("gotoLabel", new Dictionary<string, object?> { ["label"] = "again" }),
                PexStep("rawCommand", new Dictionary<string, object?> { ["cmd"] = "PING" }),
                PexStep("runExe", new Dictionary<string, object?> { ["path"] = "C:\\Tools\\demo.exe" }),
                PexStep("openFile", new Dictionary<string, object?> { ["path"] = "C:\\Data\\readme.txt" }),
                PexStep("playAudio", new Dictionary<string, object?> { ["path"] = "C:\\Data\\tone.wav", ["mode"] = "playerMacro" }),
            };
            var pexPkg=PexStep("randomPackage",new Dictionary<string,object?>{{"mode","shuffleAll"}});
            pexPkg.Children.Add(PexStep("delay",new Dictionary<string,object?>{{"minMs",1},{"maxMs",1}}));
            pexPkg.Children.Add(PexStep("mouseClick")); pexParity.Add(pexPkg);
            var pexPar=PexStep("parallelGroup"); pexPar.Children.Add(PexStep("mouseClick"));
            pexPar.Children.Add(PexStep("mouseScroll",new Dictionary<string,object?>{{"delta",1}})); pexParity.Add(pexPar);
            var pexParityText=PlanExporter.Compile(pexParity,pexSettings,1920,1080,"f","T").Text;
            foreach(var op in new[]{"WSND|91,70,8000","KEY|combo=162+65","KDOWN|160","KUP|160","WHEEL|-3","LABEL|again","GOTO|again","RAW|PING","RPKG|all,1,2","PKGITEM","ENDPKG","PGROUP","PARITEM","ENDPAR"})
                Assert(pexParityText.Contains(op),"v0.9.66: C# parity emits "+op);
            Assert(pexParityText.Split('\n').Count(x=>x=="KEY|combo=91+82|hold=40,90")==3,
                "v0.9.66: runExe/openFile/playAudio emit Win+R macros");

            // findImage remains an explicit blocking error.
            try { PlanExporter.Compile(new List<StepNode>{PexStep("findImage")},pexSettings,1920,1080,"f","T"); Assert(false,"v0.9.66: findImage must block"); }
            catch(PlanExporter.PlanBlockedException bx){Assert(bx.Errors.Any(e=>e.Contains("machine vision")),"v0.9.66: findImage blocks explicitly");}

'''
s=s[:a]+block+s[b:]
a=s.index('            // If/Else heads:')
b=s.index('            // nested blockers',a)
ifblock=r'''            // If/Else heads now emit native PLAN|2 IFLUX/IFSND + ELSE/ENDIF.
            var pexIf=PexStep("waitForLight",new Dictionary<string,object?>{{"insertIfElse",true},{"luxCenter",100},{"luxTolerance",10}});
            pexIf.Children.Add(PexStep("delay",new Dictionary<string,object?>{{"minMs",5},{"maxMs",5}}));
            var pexElse=PexStep("comment",new Dictionary<string,object?>{{"text","Else"}});
            pexElse.Children.Add(PexStep("mouseClick"));
            var pexIfText=PlanExporter.Compile(new List<StepNode>{pexIf,pexElse,PexStep("comment",new Dictionary<string,object?>{{"text","End If"}})},pexSettings,1920,1080,"f","T").Text;
            Assert(pexIfText.Contains("IFLUX|90,110,2000,20000,0\n")&&pexIfText.Contains("\nELSE\n")&&pexIfText.Contains("\nENDIF\n"),
                "v0.9.66: waitForLight If/Else emits IFLUX/ELSE/ENDIF");
            var pexSndIf=PexStep("waitForSound",new Dictionary<string,object?>{{"insertIfElse",true},{"threshold",92}});
            var pexSndText=PlanExporter.Compile(new List<StepNode>{pexSndIf,PexStep("comment",new Dictionary<string,object?>{{"text","End If"}})},pexSettings,1920,1080,"f","T").Text;
            Assert(pexSndText.Contains("IFSND|92,60,20000\n")&&pexSndText.Contains("\nENDIF\n"),"v0.9.66: waitForSound If emits IFSND/ENDIF");
'''
s=s[:a]+ifblock+s[b:]
p.write_text(s,encoding='utf-8',newline='\n')
print('PLAN2 parity tests applied')
