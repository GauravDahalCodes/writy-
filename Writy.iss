#define AppName "Writy"
#define AppVersion "1.0.0"

[Setup]
AppId={{88A9F691-0A4C-44F5-A47A-547135968C42}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Writy
DefaultDirName={localappdata}\Programs\Writy
DefaultGroupName=Writy
UninstallDisplayIcon={app}\Writy.exe
SetupIconFile=writy.ico
OutputDir=dist
OutputBaseFilename=WritySetup
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "build\release-dist\Writy.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "writy.svg"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Writy"; Filename: "{app}\Writy.exe"; WorkingDir: "{app}"; IconFilename: "{app}\Writy.exe"
Name: "{autodesktop}\Writy"; Filename: "{app}\Writy.exe"; WorkingDir: "{app}"; IconFilename: "{app}\Writy.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Writy.exe"; Description: "Launch Writy"; Flags: postinstall nowait skipifsilent
