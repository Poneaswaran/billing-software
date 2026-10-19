; ==============================================================================
; ToyPop POS & Billing - Inno Setup Script
; Generates a professional Windows Installation Wizard with:
; - Instant Open Background Service configuration
; - Windows Startup integration
; - Desktop & Start Menu shortcuts
; - Automatic background instance detection & clean shutdown during upgrade
; ==============================================================================

#define MyAppName "ToyPop POS & Billing"
#define MyAppVersion "1.0.5"
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
UsePreviousAppDir=yes
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
CloseApplications=force
CloseApplicationsFilter={#MyAppExeName}
RestartApplications=no
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
; Never ship or replace customer databases, including SQLite recovery sidecars.
Source: "..\dist\ToyPopBilling\*"; DestDir: "{app}"; Excludes: "\data\*,\_internal\data\*,*.db,*.db-*,*.sqlite,*.sqlite-*,*.sqlite3,*.sqlite3-*"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\data"; Flags: uninsneveruninstall

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Configure Windows Startup Run key if 'startwithwindows' task is checked
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ToyPopBilling"; ValueData: """{app}\{#MyAppExeName}"" --background"; Flags: uninsdeletevalue; Tasks: startwithwindows

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
const
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{9C1D0487-21B0-4A0F-99F5-62DB02B0F153}_is1';

var
  PreviousInstallDir: String;
  PreviousVersion: String;
  UpgradeConfirmed: Boolean;
  DatabaseBackedUp: Boolean;

function ReadPreviousInstall(RootKey: Integer): Boolean;
begin
  Result := RegQueryStringValue(RootKey, UninstallKey,
    'Inno Setup: App Path', PreviousInstallDir);
  if Result then
    RegQueryStringValue(RootKey, UninstallKey, 'DisplayVersion', PreviousVersion);
end;

function ConfirmUpdate(): Boolean;
var
  VersionLabel: String;
begin
  Result := False;
  // An update must be explicitly accepted; unattended updates cannot consent.
  if WizardSilent then
  begin
    Log('Existing installation found. Run setup interactively to confirm the update.');
    Exit;
  end;
  VersionLabel := '';
  if PreviousVersion <> '' then
    VersionLabel := ' (version ' + PreviousVersion + ')';
  Result := MsgBox('ToyPop POS & Billing is already installed' + VersionLabel +
    '.' + #13#10#13#10 + 'Update it to version {#MyAppVersion}?' + #13#10#13#10 +
    'Your local database, bills, products, customers and settings will be kept.' + #13#10 +
    'A database backup will be created before updating.',
    mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
  UpgradeConfirmed := Result;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not ReadPreviousInstall(HKCU32) then
    if not ReadPreviousInstall(HKLM32) then
      if IsWin64 then
        if not ReadPreviousInstall(HKCU64) then
          ReadPreviousInstall(HKLM64);
  if PreviousInstallDir = '' then
    if FileExists(ExpandConstant('{localappdata}\Programs\ToyPopBilling\{#MyAppExeName}')) then
      PreviousInstallDir := ExpandConstant('{localappdata}\Programs\ToyPopBilling');
  if PreviousInstallDir <> '' then
    Result := ConfirmUpdate();
end;

procedure InitializeWizard();
begin
  if PreviousInstallDir <> '' then
  begin
    // Keep the application pointed at its existing local data directory.
    WizardForm.DirEdit.Text := PreviousInstallDir;
    WizardForm.DirEdit.Enabled := False;
    WizardForm.DirBrowseButton.Enabled := False;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  // Also catch an unregistered/portable installation in a custom directory.
  if (CurPageID = wpReady) and (not UpgradeConfirmed) then
    if FileExists(AddBackslash(WizardDirValue) + '{#MyAppExeName}') then
    begin
      PreviousInstallDir := WizardDirValue;
      Result := ConfirmUpdate();
    end;
end;

function BackupDatabase(DataDir: String): Boolean;
var
  BackupDir, BaseBackupDir, SourceFile: String;
  Suffixes: array[0..3] of String;
  Index, Attempt: Integer;
begin
  Result := True;
  if not FileExists(AddBackslash(DataDir) + 'thangam.db') then Exit;
  BaseBackupDir := AddBackslash(DataDir) + 'backups\before-update-{#MyAppVersion}-' +
    GetDateTimeString('yyyymmdd-hhnnss', '-', ':');
  BackupDir := BaseBackupDir;
  Attempt := 0;
  while DirExists(BackupDir) do
  begin
    Attempt := Attempt + 1;
    BackupDir := BaseBackupDir + '-' + IntToStr(Attempt);
  end;
  if not ForceDirectories(BackupDir) then
  begin
    Result := False;
    Exit;
  end;
  Suffixes[0] := '';
  Suffixes[1] := '-wal';
  Suffixes[2] := '-shm';
  Suffixes[3] := '-journal';
  for Index := 0 to 3 do
  begin
    SourceFile := AddBackslash(DataDir) + 'thangam.db' + Suffixes[Index];
    if FileExists(SourceFile) then
      if not CopyFile(SourceFile, AddBackslash(BackupDir) +
        'thangam.db' + Suffixes[Index], True) then
      begin
        Result := False;
        Exit;
      end;
  end;
  Log('Database backup saved to ' + BackupDir);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ErrorCode: Integer;
begin
  Result := '';
  if (not UpgradeConfirmed) and FileExists(ExpandConstant('{app}\{#MyAppExeName}')) then
    if not ConfirmUpdate() then
    begin
      Result := 'Update cancelled. Your existing installation and database have not been changed.';
      Exit;
    end;
  // Only close the running application after the user accepted the update.
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode);
  Sleep(400);
  if CheckForMutexes('{#MyAppMutex}') then
  begin
    Result := 'Please exit ToyPop Billing completely, then retry the update.';
    Exit;
  end;
  if not DatabaseBackedUp then
  begin
    if (not BackupDatabase(ExpandConstant('{app}\data'))) or
       (not BackupDatabase(ExpandConstant('{app}\_internal\data'))) or
       (not BackupDatabase(ExpandConstant('{localappdata}\ToyPopBilling\data'))) then
    begin
      Result := 'The local database could not be backed up. Setup has stopped to protect your data. Check disk space and folder permissions, then retry.';
      Exit;
    end;
    DatabaseBackedUp := True;
  end;
end;

// Helper function to verify clean exit during uninstallation
function InitializeUninstall(): Boolean;
var
  ErrorCode: Integer;
begin
  Result := True;
  Exec('taskkill.exe', '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode);
  Sleep(400);
end;
