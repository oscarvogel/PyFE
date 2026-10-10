; ==============================================================
;  Asiento DEMO - instalador Inno Setup
; ==============================================================
;  Es el mismo programa que el de produccion (installer\Asiento.iss),
;  compilado con otro `app_id` de build. Las diferencias son todas de
;  identidad, no de comportamiento:
;
;  1. Carpeta de programa propia: `%LOCALAPPDATA%\Programs\Asiento DEMO`.
;  2. Carpeta de DATOS propia: `%LOCALAPPDATA%\Asiento DEMO`. Esta es la
;     que importa. El demo se puede instalar en la maquina de un cliente que
;     ya tiene Asiento de produccion, y si los dos escribieran en la misma
;     base, el que abre el demo veria los comprobantes del cliente y las
;     facturas de prueba quedarian metidas en el sistema de verdad. El nombre de
;     esa carpeta sale del `app_id` del build (ver `nombre_carpeta_datos` en
;     `libs/build_info.py`).
;  3. `AppId` propio, asi que se instala y se desinstala sin tocar el de
;     produccion. Se pueden tener los dos en la misma maquina.
;  4. Sin actualizaciones automaticas: el demo no esta en el manifiesto de
;     `apps/asiento/latest.json`, asi que `es_build_productivo()` da False y
;     el actualizador queda apagado. Un build de demo NUNCA se baja el
;     instalador de produccion.
;  5. Base limpia en cada instalacion: se borra el sqlite para que un demo
;     reinstalado arranque de cero. Es lo mismo que hace RND DEMO.
;
;  El ejecutable se compila con:
;      python tools\generar_build_info.py --version <timestamp> --app-id asiento-demo
;  y despues se deja el arbol en desarrollo con `--restaurar`.
;  Todo el ciclo (tests, build, instalador, SHA y subida) esta en
;  `release-demo.ps1`.
;
;  Generar el .exe primero:  compila.bat
;  Compilar el instalador:    iscc Asiento_Demo.iss
; ==============================================================

#define AppName "Asiento DEMO"
; AppVersion llega por linea de comandos: `iscc /DAppVersion=2026.10.08.10.30.00`
; (lo hace release-demo.ps1). El valor de abajo es solo el de desarrollo, para
; que `iscc Asiento_Demo.iss` a pelo siga compilando.
#ifndef AppVersion
  #define AppVersion "0.9.0"
#endif
#define AppPublisher "Vogel Consultoria"
#define AppExeName "main.exe"
#define AppMutex "AsientoDemoInstallerMutex"

; Datos del certificado de homologacion que viaja en el demo.
;
; El CUIT es de Vogel y el par .crt/.key lo deja release-demo.ps1 en
; `demo-certificados\` antes de compilar (esa carpeta esta en .gitignore: la
; clave privada no va al repositorio). El certificado es DE HOMOLOGACION:
; el demo emite contra los servicios de prueba de ARCA, nunca contra los de
; produccion, y por eso queda fijo `homo = S` abajo.
;
; Ojo con la fecha: el certificado vence. Si vencio, el demo abre pero no
; emite, y el error aparece recien al autorizar, no al instalar.
#ifndef CuitDemo
  #define CuitDemo "20-23347203-5"
#endif
; La carpeta de DATOS del demo. Tiene que ser EXACTAMENTE lo que devuelve
; `nombre_build("asiento-demo")` de libs/build_info.py. Si el nombre cambia
; alla y no aca, el instalador escribe el sistema.ini en una carpeta que la app
; no mira: el demo abre como recien instalado y vuelve el asistente.
; `tests/test_demo.py` compara las dos cosas.
#define CarpetaDatos "{localappdata}\Asiento DEMO"

[Setup]
; GUID PROPIO, distinto del de produccion. Es lo que hace que los dos
; instaladores puedan convivir: comparten nombre de archivo (main.exe) pero no
; identidad, asi que el desinstalador de uno no borra el otro.
AppId={{9FE5E60D-3A96-4F19-A1E9-F6E5D6D7EB27}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\instaladores\demo
OutputBaseFilename=Asiento_Demo-{#AppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\imagenes\marca\logo-vogel.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
SetupMutex={#AppMutex}
; Sin permisos de administrador, por lo mismo que el de produccion: la
; carpeta del programa es del usuario y se puede escribir. Ver el encabezado
; de installer\Asiento.iss para el detalle.
PrivilegesRequired=lowest
UsePreviousAppDir=no
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Default.isl"

; El demo se instala siempre sobre una base limpia. Es lo que lo hace
; reinstalable sin que queden comprobantes de una vuelta anterior.
[InstallDelete]
Type: files; Name: "{app}\sistema.db"
Type: files; Name: "{app}\sistema.db-wal"
Type: files; Name: "{app}\sistema.db-shm"
Type: files; Name: "{app}\sistema.db-journal"
; Y el sqlite con el nombre de `basedatos` (ver `_archivos_a_migrar`).
Type: filesandordirs; Name: "{app}\*.db"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; La plantilla va en {app} pero la app no la lee de ahi: la copia de
; configuracion real la crea [INI] mas abajo, en la carpeta de datos.
Source: "..\sistema.ini.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\conf\*"; DestDir: "{app}\conf"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; Certificado de homologacion del demo. Los nombres son los que la app ya
; espera en sistema.ini (ver GeneraCertificados.NOMBRE_CERT_HOMOLOGACION),
; asi que no hay que renombrar nada.
;
; `onlyifdoesntexist`: al reinstalar no se pisa un certificado que el operador
; haya cambiado por el suyo. `skipifsourcedoesntexist`: si se compila sin el
; par de archivos, el instalador igual sale -- pero el demo NO va a poder
; emitir. release-demo.ps1 no deja llegar ahi: aborta si falta el certificado.
Source: "demo-certificados\certificado_homologacion.crt"; \
  DestDir: "{app}\certificados"; Flags: onlyifdoesntexist skipifsourcedoesntexist
Source: "demo-certificados\clave_privada_homo.key"; \
  DestDir: "{app}\certificados"; Flags: onlyifdoesntexist skipifsourcedoesntexist

[Dirs]
Name: "{app}\certificados"
Name: "{app}\conf"
Name: "{app}\excel"
; La carpeta de datos del demo. Tiene que existir antes de que corra [INI]:
; es donde se precarga la configuracion y donde la app va a leer.
Name: "{#CarpetaDatos}"

; La configuracion del demo, escrita de una.
;
; Va en la CARPETA DE DATOS, no en {app}, y con `configurado = S` para que
; es_primer_arranque() de libs/instalacion.py de False: el asistente no
; aparece y la app abre directo en homologacion con el certificado puesto.
;
; Las claves y los nombres de seccion son los mismos que escribe
; guardar_config_inicial(). Si ese cambia, esto tiene que cambiar con el: un
; sistema.ini a medio escribir deja la app con una configuracion que no
; coincide con la que la app cree, y eso no da error, se ve en la proxima
; emision.
;
; Con `PrivilegesRequired=lowest` escribir en {localappdata} no pide nada.
; Reinstalar el demo vuelve a poner estos valores: si el operador habia
; cargado su propio certificado, se pierde. Es lo que se quiere en una demo.
[INI]
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "param"; Key: "configurado"; String: "S"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "param"; Key: "base"; String: "sqlite"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "param"; Key: "basedatos"; String: "pyfe"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "param"; Key: "host"; String: "localhost"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "param"; Key: "usuario"; String: ""
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "param"; Key: "homo"; String: "S"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "param"; Key: "nombre_sistema"; String: "{#AppName}"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "FACTURA"; Key: "empresa"; String: "Cliente Demo"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "FACTURA"; Key: "membrete1"; String: ""
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "FACTURA"; Key: "membrete2"; String: ""
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "FACTURA"; Key: "cuit"; String: "{#CuitDemo}"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "FACTURA"; Key: "iibb"; String: ""
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "FACTURA"; Key: "inicio"; String: "01/01/2000"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "FACTURA"; Key: "num_copias"; String: "1"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "FACTURA"; Key: "venta"; String: "grilla"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "WSFEv1"; Key: "cat_iva"; String: "6"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "WSFEv1"; Key: "pto_vta"; String: "1"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "WSFEv1"; Key: "url_prod"; String: "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "WSFEv1"; Key: "url_homo"; String: "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "WSFEv1"; Key: "cacert"; String: "conf/afip_ca_info.crt"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "WSAA"; Key: "cert_homo"; String: "certificados/certificado_homologacion.crt"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "WSAA"; Key: "cert_prod"; String: "certificados/certificado_produccion.crt"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "WSAA"; Key: "privatekey_homo"; String: "certificados/clave_privada_homo.key"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "WSAA"; Key: "privatekey_prod"; String: "certificados/clave_privada_produccion.key"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "WSAA"; Key: "url_prod"; String: "https://wsaa.afip.gov.ar/ws/services/LoginCms"
Filename: "{#CarpetaDatos}\sistema.ini"; Section: "WSAA"; Key: "url_homo"; String: "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autoprograms}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Iniciar {#AppName}"; \
  WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\error.log"
Type: filesandordirs; Name: "{app}\all.log"
