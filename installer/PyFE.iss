; ==============================================================
;  PyFE - instalador Inno Setup
; ==============================================================
;  El instalador hace lo minimo y NO escribe ningun secreto:
;   - copia el ejecutable y las carpetas de datos
;   - crea sistema.ini desde la plantilla, con la ruta real de
;     instalacion y en modo homologacion
;   - deja la conexion y los datos fiscales para el asistente de
;     primer arranque, que corre dentro de la app
;
;  Por que NO preguntar los datos aca: los certificados los emite AFIP
;  por CUIT y no se pueden pedir en un instalador. Y pedir la clave de
;  la base desde un dialogo de instalador es justo el escenario donde
;  se pierde. Ademas la app ya tiene la pantalla de Configuracion.
;
;  Generar el .exe primero:  compila.bat
;  Compilar el instalador:    iscc PyFE.iss
; ==============================================================

#define AppName "PyFE"
#define AppVersion "0.8.10"
#define AppPublisher "Servin LGSM"
#define AppExeName "main.exe"
#define AppMutex "PyFEInstallerMutex"

[Setup]
AppId={{7C2E9A41-5B3D-4F18-9E62-1A8D4C7B0F13}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\instaladores
OutputBaseFilename=PyFE-{#AppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
SetupMutex={#AppMutex}
; PyInstaller y la app necesitan permisos de escritura en la carpeta de
; instalacion (sistema.ini, certificados, logs y la base sqlite).
PrivilegesRequired=admin
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked
Name: "startmenuicon"; Description: "Crear acceso directo en el menu Inicio"; GroupDescription: "Accesos directos:"; Flags: checked

[Files]
; El ejecutable y lo que genera compila.bat en dist\
Source: "..\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; La plantilla de configuracion. El instalador la copia, no la inventa.
Source: "..\sistema.ini.example"; DestDir: "{app}"; Flags: ignoreversion
; Confianza de la app
Source: "..\conf\*"; DestDir: "{app}\conf"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Dirs]
; Los certificados se cargan aca; los emite AFIP por CUIT
Name: "{app}\certificados"
Name: "{app}\conf"
Name: "{app}\excel"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Iniciar {#AppName}"; \
  WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent runascurrentuser

[UninstallDelete]
; Los datos del usuario no se borran al desinstalar: la base, los
; certificados y la configuracion se quedan. Es lo que se espera de
; una app con datos fiscales.
Type: filesandordirs; Name: "{app}\error.log"
Type: filesandordirs; Name: "{app}\all.log"

[Code]
{ ------------------------------------------------------------------------
  Prepara el sistema.ini: parte de la plantilla y le pone la ruta real de
  instalacion. No escribe ningun secreto, y deja el modo en homologacion
  a proposito: instalar en produccion por error es el peor default.
  ------------------------------------------------------------------------ }
procedure CurStepChanged(CurStep: TSetupStep);
var
  DestIni: String;
  Template: String;
  Contenido: String;
  partie, ligne: String;
  F: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    DestIni := ExpandConstant('{app}\sistema.ini');
    Template := ExpandConstant('{app}\sistema.ini.example');

    if FileExists(DestIni) then
    begin
      { Upgrade: no se pisa una configuracion que ya existe. }
      Log('sistema.ini ya existe, se respeta');
    end
    else if FileExists(Template) then
    begin
      F := FileOpen(Template, fmOpenRead);
      try
        Contenido := '';
        while not FileEOF(F) do
        begin
          ReadLn(F, ligne);
          Contenido := Contenido + ligne + LineEnding;
        end;
      finally
        FileClose(F);
      end;

      { reemplazo del valor que si depende de la maquina }
      StringChangeEx(Contenido, 'iniciosistema = /PyFE/',
        'iniciosistema = ' + AddBackslash(ExpandConstant('{app}')), True);
      { homo = S ya viene en homologacion en la plantilla y no se toca:
        instalar en produccion por error es el peor default posible }

      F := FileOpen(DestIni, fmCreate);
      try
        FileWrite(F, Contenido);
      finally
        FileClose(F);
      end;
      Log('sistema.ini creado desde la plantilla');
    end
    else
      Log('no se encontro sistema.ini.example');

    { aviso en el log de la instalacion, no al usuario: el asistente
      aparece solo en el primer arranque }
    Log('La conexion y los datos fiscales los pide el asistente del primer arranque');
  end;
end;
