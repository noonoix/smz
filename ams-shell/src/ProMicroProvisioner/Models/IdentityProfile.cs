namespace ProMicroProvisioner.Models;
public sealed record IdentityProfile(string Name,string Manufacturer,string Product,string SerialPrefix,int BootVid,int BootPid,int AppPid)
{
 public string BootId=>$"{BootVid:X4}:{BootPid:X4}"; public string AppId=>$"{BootVid:X4}:{AppPid:X4}";
}
