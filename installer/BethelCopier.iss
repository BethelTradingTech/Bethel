#define MyAppName "Bethel Copier"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Bethel Trading Technologies"
#define MyAppExeName "BethelCopier.exe"

[Setup]
AppId={{A33AB849-06AA-4EF8-84C9-B631BC91E675}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\BethelCopier
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=BethelCopierSetup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Open Bethel Copier"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /F /TN ""Bethel Subscriber Copier"""; Flags: runhidden; RunOnceId: "RemoveCopierTask"
