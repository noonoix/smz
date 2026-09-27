using System.Diagnostics; using System.Text; using System.IO;
namespace ProMicroProvisioner.Services;
public static class ArduinoCliService {
 public static async Task<string> CompileAsync(string keyPath, Models.IdentityProfile id, Action<string> log, CancellationToken ct){
  if(!File.Exists(keyPath))throw new FileNotFoundException("ams_key.h پیدا نشد",keyPath);
  var root=Path.Combine(Path.GetTempPath(),"promicro-"+Guid.NewGuid().ToString("N"));var sketch=Path.Combine(root,"ams_board28");Directory.CreateDirectory(sketch);
  foreach(var f in Directory.GetFiles(Path.Combine(AppContext.BaseDirectory,"firmware","arm28")))File.Copy(f,Path.Combine(sketch,Path.GetFileName(f)),true);File.Copy(keyPath,Path.Combine(sketch,"ams_key.h"),true);
  var cliRoot=Path.Combine(AppContext.BaseDirectory,"tools","arduino-cli");var cli=Path.Combine(cliRoot,"arduino-cli.exe");if(!File.Exists(cli))throw new FileNotFoundException("arduino-cli.exe در بسته برنامه نیست",cli);
  var config=Path.Combine(root,"arduino-cli.yaml");File.WriteAllText(config,$"directories:\n  data: '{Path.Combine(cliRoot,"data").Replace("\\","/")}'\n  downloads: '{Path.Combine(cliRoot,"downloads").Replace("\\","/")}'\n  user: '{Path.Combine(cliRoot,"user").Replace("\\","/")}'\n");
  var outDir=Path.Combine(root,"out");Directory.CreateDirectory(outDir);var args=new[]{"compile","--config-file",config,"--fqbn","arduino:avr:leonardo","--output-dir",outDir,"--build-property",$"build.vid=0x{id.BootVid:X4}","--build-property",$"build.pid=0x{id.AppPid:X4}","--build-property",$"build.usb_product=\"{id.Product}\"","--build-property",$"build.usb_manufacturer=\"{id.Manufacturer}\"",sketch};
  var p=new Process{StartInfo=new(){FileName=cli,UseShellExecute=false,RedirectStandardOutput=true,RedirectStandardError=true,CreateNoWindow=true}};foreach(var a in args)p.StartInfo.ArgumentList.Add(a);p.Start();var so=p.StandardOutput.ReadToEndAsync(ct);var se=p.StandardError.ReadToEndAsync(ct);await p.WaitForExitAsync(ct);foreach(var l in ((await so)+"\n"+(await se)).Split('\n',StringSplitOptions.RemoveEmptyEntries))log(l.Trim());if(p.ExitCode!=0)throw new InvalidOperationException($"Arduino build failed ({p.ExitCode})");return Directory.GetFiles(outDir,"*.hex").First(x=>!x.Contains("with_bootloader",StringComparison.OrdinalIgnoreCase));
 }
}
