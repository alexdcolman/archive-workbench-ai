#define MyAppVersion GetEnv("AWAI_VERSION")
#define MyAppBinary GetEnv("AWAI_BINARY")
#define MyOutputDir GetEnv("AWAI_OUTPUT_DIR")

[Setup]
AppId={{51B0B69F-464B-4D8D-9B1F-CA8D7C26E8F2}
AppName=Archive Workbench AI
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\Archive Workbench AI
DefaultGroupName=Archive Workbench AI
PrivilegesRequired=lowest
OutputDir={#MyOutputDir}
OutputBaseFilename=Archive-Workbench-AI-{#MyAppVersion}-Windows-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\aw-ai.exe

[Files]
Source: "{#MyAppBinary}"; DestDir: "{app}"; DestName: "aw-ai.exe"; Flags: ignoreversion
Source: "packaging\windows\setup.vbs"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Archive Workbench AI Setup"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\setup.vbs"""; WorkingDir: "{app}"
Name: "{userdesktop}\Archive Workbench AI Setup"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\setup.vbs"""; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; Flags: unchecked

[Run]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\setup.vbs"""; Description: "Abrir Archive Workbench AI Setup"; Flags: postinstall nowait skipifsilent
