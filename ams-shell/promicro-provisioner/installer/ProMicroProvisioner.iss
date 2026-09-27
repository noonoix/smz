[Setup]
AppName=Pro Micro Provisioner
AppVersion=1.0.0
DefaultDirName={autopf}\Pro Micro Provisioner
DefaultGroupName=Pro Micro Provisioner
OutputBaseFilename=ProMicroProvisioner-Setup-x64
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
[Files]
Source: "..\publish\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
[Icons]
Name: "{group}\Pro Micro Provisioner"; Filename: "{app}\ProMicroProvisioner.exe"
Name: "{autodesktop}\Pro Micro Provisioner"; Filename: "{app}\ProMicroProvisioner.exe"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked
[Run]
Filename: "{app}\ProMicroProvisioner.exe"; Description: "Launch Pro Micro Provisioner"; Flags: nowait postinstall skipifsilent
