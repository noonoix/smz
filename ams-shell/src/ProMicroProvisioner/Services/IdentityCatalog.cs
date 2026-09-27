using System.Security.Cryptography; using ProMicroProvisioner.Models;
namespace ProMicroProvisioner.Services;
public static class IdentityCatalog {
 static readonly string[] Schools={"Northbridge University","Westlake Institute","Eastwood College","Southfield Academy","Cedar Valley University","Maple Grove College","Horizon Technical Institute","Pioneer Science Academy","Riverside Polytechnic","Summit Research University"};
 static readonly string[] Units={"Computer Lab","Engineering Center","Science Faculty","Robotics Club","Digital Library","Research Office","Electronics Lab","Student Workshop","Learning Center","Campus Services"};
 static readonly string[] Products={"USB Serial Console","Research Data Bridge","Laboratory Control Port","Academic Device Link","Campus Service Terminal","Student Project Adapter","Robotics Debug Console","Sensor Data Gateway","Engineering Interface","Classroom USB Device"};
 public static IReadOnlyList<IdentityProfile> All {get;}=Build();
 static IReadOnlyList<IdentityProfile> Build(){var list=new List<IdentityProfile>();for(int i=0;i<100;i++){int vid=0x1000+((i*7919+0x2345)%0xEFFE);int boot=0x1000+((i*3571+0x4321)%0xEFFE);if(boot==0xFFFE)boot--;list.Add(new($"{Schools[i/10]} {Units[i%10]}",Schools[i/10]+" "+Units[i%10],Products[(i*3)%10]+$" {i+1:000}",$"EDU{i+1:000}",vid,boot,boot+1));}return list;}
 public static IdentityProfile Random()=>All[RandomNumberGenerator.GetInt32(All.Count)];
}
