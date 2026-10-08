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

#define AppName "Asiento"
; AppVersion llega por linea de comandos: `iscc /DAppVersion=2026.10.05.08.37.00`
; (lo hace release.ps1). El valor de abajo es solo el de desarrollo, para que
; `iscc PyFE.iss` a pelo siga compilando.
#ifndef AppVersion
  #define AppVersion "0.9.0"
#endif
#define AppPublisher "Vogel Consultoria"
#define AppExeName "main.exe"
#define AppMutex "AsientoInstallerMutex"

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
OutputBaseFilename=Asiento-{#AppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
; Icono del instalador, del menu Inicio y del escritorio: el logo de la
; marca. El .ico sale de tools/generar_marca.py a partir del original.
SetupIconFile=..\imagenes\marca\logo-vogel.ico
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
; Solo el escritorio es opcional. El acceso del menu Inicio se crea
; siempre (ver [Icons]) y no como tarea: en Inno Setup 6.7.3 los flags
; 'checkedonly' y 'uncheckedonly' no existen y el script no compila
; (comprobado con ISCC), asi que no hay forma de marcar una tarea como
; seleccionada por defecto. El menu Inicio es obligatorio igual.
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

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

; Nota: el instalador NO escribe sistema.ini.
; La app lo crea sola en el primer arranque, con los datos que da el
; asistente, y se posiciona en la carpeta donde quedo instalada. Asi el
; instalador no tiene que escribir configuracion ni manipulating
; encodings, que es donde se pondrian complicados.
