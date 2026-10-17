; Instalador con Inno Setup 6 (https://jrsoftware.org/isinfo.php)
; Compilar:  iscc installer.iss /DMyAppVersion=1.0.0              -> PUBLICO
;            iscc installer.iss /DMyAppVersion=1.0.0 /DPersonal   -> PERSONAL (build.bat ya lo hace)
;            (carpeta de datos del personal: /DDatosGabo="E:\otra")
; IMPORTANTE: no cambiar los AppId. Es lo que permite que una versión nueva
; actualice a la anterior en vez de instalarse al lado. Los dos son distintos
; a propósito para que el público y el personal puedan convivir.

#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#ifndef DatosGabo
  #define DatosGabo "D:\Docs2\Trade\Journal\Registro_operativa"
#endif
#define MyAppPublisher "gabomondo"
#define MyAppURL       "https://gabomondo.com"
#define MyAppExeName   "RegistroOperativa.exe"

#ifdef Personal
  #define MyAppName     "Registro de Operativa (Gabo)"
  #define MyAppId       "{{8BBE2585-E6F6-4258-A7AF-FBE95F0A3B3A}"
  #define MyOutputName  "RegistroOperativa-Gabo-Setup-"
  #define MyDirName     "RegistroOperativaGabo"
  #define MySource      "dist\gabo\RegistroOperativa\*"
#else
  #define MyAppName     "Registro de Operativa"
  #define MyAppId       "{{024ED0FB-B8DA-475F-AF22-220D28C82957}"
  #define MyOutputName  "RegistroOperativa-Setup-"
  #define MyDirName     "RegistroOperativa"
  #define MySource      "dist\RegistroOperativa\*"
#endif

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyDirName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; instala solo para el usuario actual: no pide permisos de administrador
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename={#MyOutputName}{#MyAppVersion}
SetupIconFile=assets\icono.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "{#MySource}"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
#ifdef Personal
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--datos ""{#DatosGabo}"" --perfil gabo"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--datos ""{#DatosGabo}"" --perfil gabo"; Tasks: desktopicon
#else
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
#endif

[Run]
#ifdef Personal
Filename: "{app}\{#MyAppExeName}"; Parameters: "--datos ""{#DatosGabo}"" --perfil gabo"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
#else
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
#endif

; Los datos del usuario (público) viven en %APPDATA%\gabomondo\RegistroOperativa; el personal usa
; la carpeta indicada en DatosGabo. El desinstalador NO toca ninguno de los dos: desinstalar no borra el journal.
