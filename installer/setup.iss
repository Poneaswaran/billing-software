; ==============================================================================
; ToyPop POS & Billing - Inno Setup Script
; Generates a professional Windows Installation Wizard with:
; - Instant Open Background Service configuration
; - Windows Startup integration
; - Desktop & Start Menu shortcuts
; - Automatic background instance detection & clean shutdown during upgrade
; ==============================================================================

#define MyAppName "ToyPop POS & Billing"
#define MyAppVersion "1.0.2"
#define MyAppPublisher "ToyPop Retail Systems"
#define MyAppURL "https://toypop.in"
#define MyAppExeName "ToyPopBilling.exe"
#define MyAppMutex "ToyPopBilling_App_Mutex_2026"

[Setup]
AppId={{9C1D0487-21B0-4A0F-99F5-62DB02B0F153}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\ToyPopBilling
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=ToyPopBilling_Setup_v{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
AppMutex={#MyAppMutex}
CloseApplications=yes
CloseApplicationsFilter={#MyAppExeName}
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
ShowLanguageDialog=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startwithwindows"; Description: "Start ToyPop Billing automatically with Windows (Instant Launch mode - Recommended)"; GroupDescription: "Performance & Startup Options:"

[Files]
Source: "..\dist\ToyPopBilling\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Configure Windows Startup Run key if 'startwithwindows' task is checked
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ToyPopBilling"; ValueData: """{app}\{#MyAppExeName}"" --background"; Flags: uninsdeletevalue; Tasks: startwithwindows

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Helper function to verify clean exit during uninstallation
function InitializeUninstall(): Boolean;
var
  ErrorCode: Integer;
begin
  Result := True;
  // If running, taskkill gracefully or let Inno Setup CloseApplications handle it
  Exec('taskkill.exe', '/F /IM ' + '{#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode);
end;
