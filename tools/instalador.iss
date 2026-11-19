; Instalador do EcoGuard (Inno Setup). Gere com tools\gerar_exe.ps1
; Instala só para o usuário atual: NÃO pede senha de administrador.
#define Nome "EcoGuard"
#define Versao "1.0"

[Setup]
AppId={{6F1B7C1E-3C55-4C0E-9B6E-EC0A6A9D0001}
AppName={#Nome}
AppVersion={#Versao}
AppPublisher=Cometa Charuri
DefaultDirName={autopf}\{#Nome}
DefaultGroupName={#Nome}
PrivilegesRequired=lowest
OutputDir=..\instalador
OutputBaseFilename=Instalar-EcoGuard
SetupIconFile=..\static\img\ecoguard.ico
UninstallDisplayIcon={app}\EcoGuard.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktop"; Description: "Criar um atalho na área de trabalho"; Flags: checkedonce

[Files]
Source: "..\dist\EcoGuard\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autodesktop}\{#Nome}"; Filename: "{app}\EcoGuard.exe"; Tasks: desktop
Name: "{group}\{#Nome}"; Filename: "{app}\EcoGuard.exe"

[Run]
Filename: "{app}\EcoGuard.exe"; Description: "Abrir o EcoGuard agora"; Flags: nowait postinstall skipifsilent
