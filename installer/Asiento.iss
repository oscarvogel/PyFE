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
;  Instalacion POR USUARIO (2026-10-08)
;  ------------------------------------
;  Antes iba a `{autopf}\{#AppName}` con `PrivilegesRequired=admin`, y eso
;  daba tres sintomas que se reportaron en maquinas de clientes:
;
;  1. El acceso directo caia en el menu de programas del ADMINISTRADOR, no en
;     el del usuario. Con `PrivilegesRequired=admin`, `{group}` es el menu
;     "todos los usuarios", que es el perfil del admin con el que se elevo. Un
;     usuario normal no lo veia, y el proceso de la app queda colgado del
;     instalador sin ventana.
;  2. El programa no abria. La carpeta de instalacion es de solo lectura y el
;     ejecutable corre sin permisos: en la version de 64 bits no hay
;     virtualizacion de UAC que lo esconda, asi que la escritura falla de
;     verdad (ver `libs/rutas.py` y `docs/CARPETA-DE-DATOS.md`).
;  3. El certificado y la clave no tenian donde estar. Las rutas de [WSAA] son
;     relativas (`certificados/...`) y `controladores/FE.py` las resuelve con
;     abspath() contra la carpeta del programa, asi que el `.crt` que devuelve
;     ARCA tiene que quedar DENTRO de la carpeta de instalacion. Con admin era
;     un rodeo; sin admin, no se podia. Tambien las carpetas relativas
;     (`tmp`, `excel`).
;
;  Ahora va a `%LOCALAPPDATA%\Programs\Asiento` sin pedir permisos, como los
;  instaladores de RND y de FEMAG Desktop. La carpeta es del usuario y se
;  puede escribir, asi que la app abre, guarda y genera certificados sin
;  depender de que la maquina tenga permisos de administrador.
;
;  La carpeta de DATOS (configuracion, base y logs) NO cambia: sigue en
;  `%LOCALAPPDATA%\Asiento`, que es donde la app los guarda desde el arreglo
;  del 2026-10-05. Asi el cliente que ya uso el sistema no ve el asistente de
;  nuevo ni la base vacia. Ver la regla nueva en `libs/rutas.py`.
;
;  Generar el .exe primero:  compila.bat
;  Compilar el instalador:    iscc Asiento.iss
; ==============================================================

#define AppName "Asiento"
; AppVersion llega por linea de comandos: `iscc /DAppVersion=2026.10.05.08.37.00`
; (lo hace release.ps1). El valor de abajo es solo el de desarrollo, para que
; `iscc Asiento.iss` a pelo siga compilando.
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
; Carpeta del PROGRAMA: por usuario, escribible y sin pedir permisos.
; Es el mismo criterio que usan los instaladores de RND y de FEMAG Desktop.
DefaultDirName={localappdata}\Programs\{#AppName}
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
; Instalar POR USUARIO y sin pedir permisos de administrador.
;
; El motivo concreto esta en el encabezado. En corto: la app escribe en su
; propia carpeta (la base, los logs, el certificado y la clave que usan las
; rutas relativas de [WSAA], las salidas como `tmp`), y dentro de Program Files
; eso es imposible para un proceso que no corre elevado. Con la carpeta del
; usuario, la app abre y guarda siempre, y el instalador no depende de que la
; maquina tenga permisos ni de que el usuario sea administrador.
PrivilegesRequired=lowest
; Forzar DefaultDirName aunque la maquina ya tenga una instalacion registrada.
; Sin esto Inno Setup reutiliza la carpeta que grabo la version anterior
; (C:\Program Files\Asiento) y el cambio de carpeta no le llega justamente a
; quien ya lo instalo. Queda la carpeta vieja ahi, pero SOLO con los archivos
; del programa: los datos del cliente nunca estuvieron ahi (ver
; docs\CARPETA-DE-DATOS.md), asi que se puede borrar sin perder nada.
UsePreviousAppDir=no
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
; `{autoprograms}`, no `{group}`. Con `PrivilegesRequired=lowest` los dos
; apuntan al menu del usuario, pero `{autoprograms}` lo dice sin depender de
; como se interprete el modo de privilegios: el acceso directo tiene que caer
; en el menu de quien instalo, no en el de "todos los usuarios".
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autoprograms}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; Sin `runascurrentuser`: esa opcion existia para abrir la app sin privilegios
; cuando el instalador corria elevado. Ahora el instalador no pide permisos, asi
; que el proceso ya es del usuario y la opcion no aporta nada.
Filename: "{app}\{#AppExeName}"; Description: "Iniciar {#AppName}"; \
  WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

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
