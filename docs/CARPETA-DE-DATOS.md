# Carpeta de datos: por que el sistema no podia guardarse en `Program Files`

Fecha: 2026-10-05 (el bug) y 2026-10-08 (la instalacion pasa a ser por usuario)
Windows 10 64 bits, instalador Inno Setup, ejecutable PyInstaller de una pieza.

## Que se vio

En una instalacion nueva, el usuario completa el asistente de primer arranque y,
al guardar, el programa muere:

```
Unhandled exception in script
Failed to execute script 'main' due to unhandled exception:
[Errno 13] Permission denied: 'C:\Program Files\Asiento\sistema.ini'

File "main.py", line 212, in <module>
File "main.py", line 185, in inicio
File "main.py", line 43, in _configurar_instalacion_nueva
File "libs\instalacion.py", line 220, in guardar_config_inicial
File "libs\instalacion.py", line 213, in <lambda>
File "libs\Utiles.py", line 195, in GrabarIni
PermissionError: [Errno 13] Permission denied
```

Se reproduce siempre, en cualquier instalacion nueva, y no depende de los datos
que se carguen.

## Por que pasaba

Son tres cosas que se juntaron.

**1. El instalador corre como administrador; la app, no.**
`installer/Asiento.iss` instala en `{autopf}\{#AppName}` (`C:\Program Files\Asiento`)
con `PrivilegesRequired=admin`. Eso le permite al instalador escribir los
archivos. Pero el acceso directo que crea abre el `.exe` tal cual, sin
elevar: en Windows, un proceso normal no puede crear archivos dentro de
`Program Files`.

> Los dos puntos siguientes quedaron sin efecto el 2026-10-08: la instalacion
> ya no es en `Program Files` ni pide administrador. Ver la seccion de mas
> abajo. Se los deja como estan porque explican como se llego a este bug.

**2. La app elegia la carpeta donde estaba instalado para escribir.**
`main.py::_asegurar_carpeta_de_trabajo` hace `os.chdir()` a la carpeta del
programa, y `Utiles.GrabarIni` resolvia el `sistema.ini` con `os.getcwd()`
(`libs/Utiles.py:195`, `open(join(carpeta, archivoini), 'w')`). Con el cwd en
`Program Files`, toda escritura iba ahi.

**3. Por que no pasaba antes y si ahora: el ejecutable es de 64 bits.**
Windows redireccionaba en silencio las escrituras de los procesos de 32 bits
a `%LOCALAPPDATA%\VirtualStore\...` (virtualizacion de archivos de UAC). En un
ejecutable de **64 bits esa virtualizacion esta desactivada**, y la escritura
falla de verdad, con `PermissionError`. `compila.bat` no pasa `--arch`, asi que
el `.exe` sale de la architectura del Python de la maquina donde se compila:
al compilar con un Python de 64 bits desaparecio la red de seguridad que
venia ocultando el problema.

## Que se cambio

La regla nueva: **la carpeta de instalacion guarda lo que se lee; lo que se
escribe va a una carpeta del usuario.**

| Que | Donde queda |
| --- | --- |
| `.exe`, `imagenes/`, `plantillas/`, `conf/`, `data/`, `temas/` | Carpeta de instalacion (solo lectura) |
| `sistema.ini` | Carpeta de datos, si la de instalacion no se puede escribir |
| `sistema.db` (SQLite) | Carpeta de datos |
| `error.log`, `debug.log` | Carpeta de datos |
| `iniciosistema` (de donde salen los recursos) | Carpeta de instalacion |

La carpeta de datos se decide en el orden siguiente (`libs/rutas.py`, nuevo):

1. `PYFE_CARPETA_DATOS`, si esta definida. La usan los tests y las
   instalaciones portables.
2. El directorio de trabajo actual, **si se puede escribir**. Esto mantiene
   exactamente el comportamiento de siempre en desarrollo, en los tests (que
   hacen `monkeypatch.chdir`), en las portables y en los scripts de `tools/`.
3. `%LOCALAPPDATA%\Asiento`, creada si falta. Mismo criterio que ya usaba
   `libs/changelog.py` para el estado de las novedades.

### Archivos tocados

- **`libs/rutas.py` (nuevo)**: `carpeta_instalacion`, `puede_escribir`,
  `carpeta_datos`, `ruta_ini`, `ruta_base`, `migrar_desde_instalacion`.
  La sonda de escritura **crea y borra un archivo de verdad** en vez de usar
  `os.access(carpeta, os.W_OK)`: `os.access` da `True` en carpetas en las que
  despues no se puede crear nada, que es justo el caso que rompe a los usuarios.
- **`libs/Utiles.py`**: `LeerIni` y `GrabarIni` resuelven la carpeta con
  `rutas.carpeta_datos()` en vez de `os.getcwd()`. El `-i/--inicio` explicito
  sigue mandando. `GrabarIni` ahora convierte un error de escritura en
  `ErrorEscrituraConfig` (subclase de `OSError`) con un mensaje que dice que
  archivo es y que hacer, en vez de dejar escapar un `PermissionError` pelado.
- **`libs/instalacion.py`**: `ruta_config()` usa el mismo resolvedor (estaba
  duplicado, y por eso un modulo podia mirar un archivo y `GrabarIni` otro).
  `normalizar_cuit_emisor` no corta el arranque si no puede guardar la
  correccion: avisa y sigue.
- **`modelos/ModeloBase.py`**: el archivo de SQLite se crea en la carpeta de
  datos. Antes era relativo al directorio de trabajo, o sea que en
  `Program Files` tampoco se hubiera podido crear (fallo siguiente del mismo
  bug).
- **`main.py`**: el cambio de directorio de trabajo va **antes** de tocar la
  configuracion, porque la decision de carpeta de datos depende de el. Los logs
  van a la carpeta de datos. Si el asistente no puede guardar, se muestra un
  `showError` con que hacer, no un traceback.

### Instalaciones que ya tenian datos

`migrar_desde_instalacion()` copia `sistema.ini` y `sistema.db` de la carpeta
del programa a la carpeta de datos, una sola vez, y solo si el archivo no esta
ya en el destino. El original no se borra.

Sin esto, un cliente que ya venia usando el sistema habria visto el asistente
de nuevo y la base **vacia**, que es peor que el `PermissionError`.

## Como verificarlo a mano

En la maquina donde pasa el bug, con un usuario normal (no administrador):

```
icacls "%TEMP%\prueba" /deny <usuario>:(OI)(CI)W
cd /d "%TEMP%\prueba"
set LOCALAPPDATA=%TEMP%\datos
python tools\validar_instalacion.py
icacls "%TEMP%\prueba" /remove:d <usuario>
```

Lo que hay que ver: `sistema.ini` creado en `%LOCALAPPDATA%\Asiento`, y nada
escrito en la carpeta del programa.

En la maquina de desarrollo esto **no se puede reproducir de la misma forma**:
las cuentas que compilan suelen ser administradoras y escriben en cualquier
carpeta. Los tests miden la decision ("a que carpeta va el archivo"), no el
permiso del sistema, que es cosa de cada maquina. EstaDecisionado en
`tests/test_carpeta_datos.py`.

## La instalacion pasa a ser por usuario (2026-10-08)

Arreglar la carpeta de datos fue necesario pero no alcanzo: los sintomas que
reportaron los clientes seguian.

### Que se reportaba

- El acceso directo caia en el menu de programas del **administrador**, no en
  el del usuario. Con `PrivilegesRequired=admin`, `{group}` es el menu de
  "todos los usuarios", que es el perfil del admin con el que se elevo. Un
  usuario normal no lo veia.
- El programa no abria.
- La carpeta de instalacion seguia siendo de solo lectura, asi que habia cosas
  que no se podian escribir ni con administrador: las carpetas relativas
  (`tmp`, `excel`), y sobre todo el **certificado y la clave privada**. Las
  rutas de `[WSAA]` son relativas (`certificados/...`) y
  `controladores/FE.py:128` las resuelve con `abspath()` contra la carpeta del
  programa, asi que el `.crt` que devuelve ARCA tiene que quedar adentro de
  `C:\Program Files\Asiento\certificados\`. La pantalla Certificados si
  dejaba elegir donde guardar el CSR y la clave (por ahi si se podia generar),
  pero despues no había donde dejar el certificado.

### Que se cambio

`installer/Asiento.iss` pasa a instalar por usuario, sin pedir permisos:

| | Antes | Ahora |
| --- | --- | --- |
| Carpeta | `C:\Program Files\Asiento` | `%LOCALAPPDATA%\Programs\Asiento` |
| Privilegios | `PrivilegesRequired=admin` | `PrivilegesRequired=lowest` |
| Acceso directo | `{group}` | `{autoprograms}` |
| Lanzarlo al final | `runascurrentuser` | (nada: ya corre sin elevate) |
| Carpeta anterior | (por omision) | `UsePreviousAppDir=no` |

Es el mismo criterio que usan los instaladores de RND (`installer\RND_Demo.iss`)
y de FEMAG Desktop (`FEMAG_Desktop_Demo.iss`): `{localappdata}\Programs\<app>`,
`PrivilegesRequired=lowest` y `{autoprograms}`.

`UsePreviousAppDir=no` es lo que hace que el cambio llegue a quien ya lo tinha
instalado: sin esa linea Inno Setup reutiliza la carpeta que grabo la version
anterior (`C:\Program Files\Asiento`) y el arreglo se aplica solo a las
maquinas nuevas.

### Lo que hay que hacer en las maquinas que ya lo tienen instalado

La carpeta vieja queda ahi, con los archivos del programa. **Los datos del
cliente nunca estuvieron ahi** (iban a `%LOCALAPPDATA%\Asiento`, porque la
carpeta de `Program Files` no se puede escribir), asi que se puede borrar sin
perder nada:

```
rmdir /s /q "C:\Program Files\Asiento"
```

Se puede hacer antes o despues de instalar la version nueva.

### La regla que faltaba: los datos no se mudan con el programa

Con la carpeta nueva escribible, la regla de `libs/rutas.py` tal cual (usar el
directorio de trabajo cuando se puede escribir) mandaba sobre
`%LOCALAPPDATA%\Asiento`. Eso habria roto a todos los clientes que ya usaban
el sistema: la carpeta nueva viene vacia, el asistente de primer arranque
vuelve a aparecer y la base se ve **VACIA**.

Por eso se agrego la regla 2 de `carpeta_datos()`: **si la app es la
instalada y ya hay un `%LOCALAPPDATA%\Asiento\sistema.ini`, esa carpeta
manda**, aunque la carpeta del programa se pueda escribir.

El filtro de `sys.frozen` es lo que evita el efecto contrario: en desarrollo y
en `tools/` la regla no hace nada, asi que `python main.py` sigue leyendo el
`sistema.ini` de la carpeta de trabajo del repo. Sin ese filtro, en una
maquina con el sistema instalado la app leeria el archivo del cliente y
cambiar el del repo no haria nada.

Los tests de esto estan en `tests/test_carpeta_datos.py`, en la seccion
"Instalar en otro lado sin perder lo que ya estaba".

## Bugs que aparecieron en el camino

**La sonda de escritura contestaba False en toda carpeta.** La primera version
hacia `bool(probar(carpeta))` y la sonda no devolvia nada, asi que `bool(None)`
era `False`: el sistema iba siempre a `%LOCALAPPDATA%`, incluso en desarrollo
donde la carpeta se puede escribir. Lo cazaron los tests; queda el comentario en
`_sonda` para que no vuelva a pasar.

**El CUIT de ejemplo de los tests no era valido.** `30111111124` no cierra el
digito verificador, asi que `cuit_es_real()` lo rechazaba y `normalizar_cuit_emisor`
devolvia `'falta'`. El valido es `30111111126` (`30-11111112-6`).
Ojo: `tools/armar_sandbox.py` y `sistema.ini.example` usan `30111111124`, asi que
el sandbox tambien tiene un CUIT que la app no reconoce como real.

## Pendientes

1. ~~**`tmp/` y carpetas de salida relativas, en instalaciones dentro de
   `Program Files`.**~~ **Resuelto por el cambio de instalacion del 2026-10-08**:
   la carpeta del programa ahora es `%LOCALAPPDATA%\Programs\Asiento`, que es
   del usuario y se puede escribir, asi que `os.mkdir("tmp")` y los PDF que se
   arman ahi vuelven a funcionar. No se toco ningun controlador: si manana la
   app vuelve a instalarse en una carpeta de solo lectura, el problema vuelve y
   hay que pasarlos a `rutas.ruta_base()`.

2. ~~**Decidir si el instalador sigue pidiendo administrador.**~~ **Decidido el
   2026-10-08: no.** `PrivilegesRequired=lowest`. Ver la seccion de mas arriba.

3. **`%LOCALAPPDATA%` vs `%APPDATA%`.** Con `%LOCALAPPDATA%` los datos no
   viajan con el perfil de roaming. Para una base de facturas y certificados
   parece lo correcto, pero si se quiere que la configuracion siga al usuario
   entre equipos, `%APPDATA%` seria el lugar. Hoy no hay roaming en el producto.

4. **`tools/validar_instalacion.py`** (el paso de "Como verificarlo a mano") no
   existe: quedo como pasos manuales. Con la instalacion por usuario se puede
   escribir, porque alcanza con correr la app en una maquina normal.

5. **La carpeta vieja de `Program Files` no se borra sola.** `UsePreviousAppDir=no`
   instala en el lugar nuevo y deja la copia anterior. Con el desinstalador
   viejo todavia en la carpeta, se puede borrar desde
   "Agregar y quitar programas" o a mano. Ningun dato del cliente se pierde
   porque nunca estuvieron ahi, pero conviene dejarlo asentado antes de
   mandarles la version a los que ya la tienen.
