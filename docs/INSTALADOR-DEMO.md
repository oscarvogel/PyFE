# El instalador DEMO

Fecha: 2026-10-08
Windows 10 64 bits, Inno Setup 6, ejecutable PyInstaller de una pieza.

## Que es

El mismo programa que el de produccion, compilado con otra identidad de build.
Se distribuye aparte, como asset suelto del release `latest` de
`oscarvogel/vogel-releases`, y **no** por el canal de actualizaciones
automaticas.

| | Produccion | Demo |
| --- | --- | --- |
| `app_id` del build | `asiento` | `asiento-demo` |
| Carpeta del programa | `%LOCALAPPDATA%\Programs\Asiento` | `%LOCALAPPDATA%\Programs\Asiento DEMO` |
| Carpeta de datos | `%LOCALAPPDATA%\Asiento` | `%LOCALAPPDATA%\Asiento DEMO` |
| `AppId` del instalador | GUID de produccion | GUID propio |
| Asset | `Asiento_Produccion_Setup.exe` | `Asiento_Demo_Setup.exe` |
| Manifiesto | `apps/asiento/latest.json` | **ninguno** |
| Se actualiza solo | si | **no** |
| Al reinstalar | conserva la base | borra la base |

Archivos: `installer/Asiento_Demo.iss`, `release-demo.ps1`, `tests/test_demo.py`.

## Las tres cosas que lo hacen seguro

Son riesgos que no dan error: dan "funciona" mientras hacen algo que no tiene
que pasar. Por eso cada una tiene su test en `tests/test_demo.py`.

### 1. No abre la base de produccion

El demo se puede instalar en la maquina de un cliente que ya tiene Asiento de
produccion. Si los dos usaran `%LOCALAPPDATA%\Asiento`, el que abre el demo
veria los comprobantes del cliente, y cualquier factura de prueba quedaria
metida en el sistema de verdad.

Por eso el nombre de la carpeta de datos sale del `app_id` del build
(`nombre_carpeta_datos()` en `libs/build_info.py`), no de una constante. Los
dos pueden convivir en la misma maquina sin verse.

Ojo con el detalle: con la instalacion por usuario (ver
`CARPETA-DE-DATOS.md`), la carpeta del programa se puede escribir y los datos
caen adentro de cada una, asi que ya estan separadas. La tabla de `app_id` es
la red que cubre el caso de una maquina que todavia tiene la instalacion vieja
en `Program Files`, que es justamente donde los datos caen siempre en
`%LOCALAPPDATA%`.

### 2. No se actualiza solo, y jamas baja el instalador de produccion

`libs/actualizaciones.py::habilitado` era:

```python
return es_build_productivo() or self.app_id != "development"
```

Con esa condicion, el build del demo (`asiento-demo`) **encendia el chequeo**:
`app_id != "development"` da True. Como el demo no tiene manifiesto, el chequeo
no encontraba nada que comparar y quedaba en un limbo. Y el riesgo real es el de
al revés: que un build de demo termine bajando el instalador de PRODUCCION y
ejecutandolo sobre una base de pruebas.

Ahora la condicion es "este producto tiene un manifiesto contra el cual
compararse":

```python
if self.manifest_url is None:
    return False
return es_build_productivo() or self.app_id != "development"
```

`es_build_productivo()` alcanza para produccion. Este `manifest_url` agrega la
garantia de que, si manana aparece una app mas, pueda actualizarse recien
cuando tenga su manifiesto.

`test_el_demo_no_tiene_actualizador` falla con `assert True is False` si se saca
la guarda: no es un test decorativo.

### 3. No escribe manifiesto

Por eso `asiento-demo` **no** esta en `_MANIFESTOS` de `libs/build_info.py` y no
hay `apps/asiento-demo/latest.json` en el repo de releases. Nada apunta al
demo, asi que no hay forma de que una app "se actualice" hacia el.

`release-demo.ps1` sube el `.exe` y nada mas.

## Como se publica

```
.\release-demo.ps1 -SinPublicar     # compila y arma el .exe, no sube
.\release-demo.ps1                  # sube Asiento_Demo_Setup.exe a `latest`
```

El ciclo es el de `release.ps1`: tests primero (con el arbol en desarrollo),
despues la identidad del build, el build con PyInstaller, la verificacion de la
distribucion, el instalador, el SHA256 y la subida. El estado del repo se
restaura en un `finally`.

Al final verifica el `digest` que devuelve GitHub contra el SHA256 local. Si
no coinciden, el script falla.

### Lo que el script nunca toca

- `Asiento_Produccion_Setup.exe`: es el asset que baja el actualizador de los
  clientes de `apps/asiento/latest.json`. El demo se sube con otro nombre.
- El manifiesto de produccion: `apps/asiento/latest.json` y su `changelog.json`
  no se escriben.

## Instalarlo al lado de produccion

Se pueden tener los dos. Son `AppId` distintos, asi que cada uno se instala y se
desinstala sin tocar al otro, y las carpetas de datos son distintas.

Lo que **no** se debe hacer es cambiar de uno al otro creyendo que es lo mismo:
son dos bases separadas. Si el demo se quiere probar con datos, se reinstala
(el `[InstallDelete]` borra el sqlite) y se completa el asistente de primer
arranque otra vez.

## El nombre que ve el operador

El nombre del build (`nombre_build()` en `libs/build_info.py`) se usa para las
dos cosas que lo identifican: la carpeta de datos y **el titulo de las
ventanas**.

Lo que ahora dice "Asiento DEMO" en vez del nombre fijo:

| Lugar | Donde |
| --- | --- |
| Titulo de la ventana principal | `vistas/Main.py` (`setWindowTitle`) |
| Saludo y titulo de la pantalla de inicio | `vistas/Main.py` |
| Acerca de | `vistas/Main.py` |
| Titulo del asistente de primer arranque | `vistas/PrimerArranque.py` |
| Campo "Nombre del sistema", prellenado | `vistas/PrimerArranque.py` |
| `param.nombre_sistema` que escribe el asistente | `libs/instalacion.py` |

Lo que queda con `NOMBRE_PRODUCTO` es solo el **respaldo** cuando la razon
social esta vacia (`libs/Utiles.py`, dialogo Acerca de), que no es el nombre del
producto sino un dato de la empresa.

Los tests construyen la ventana real (`MainView()` + `initUi()`, igual que
`tests/test_acerca_de.py`) y miran `windowTitle()`. No grepean el codigo: un
test que busca "no aparece NOMBRE_PRODUCTO" pasa igual con la logica del titulo
rota.

## Los certificados del demo

Decidido el 2026-10-08: **opcion B, demo "listo para emitir"**, con el
certificado de homologacion de Vogel apretado en el instalador y publicado en
el release publico. Los riesgos quedan escritos abajo porque se aceptaron a
conciencia, no por defecto.

### Que certificado viaja

| | |
| --- | --- |
| Origen | `C:\Programacion\sistema\certificados\homo.crt` + `homo.key` |
| CN | `oscarhomologacion` |
| CUIT | 20-23347203-5 (Vogel) |
| Vence | **2027-02-11** |
| Ambito | **Solo homologacion.** El par de produccion no esta en el repo |

El CUIT sale del certificado: `leer_cuit_del_certificado()` lo lee del `.crt`,
no al reves. El `sistema.ini` precargado trae ese mismo CUIT, y por eso
`controladores/FE.py` encuentra el certificado sin que nadie lo configure.

La clave privada **no entra al repositorio**: `tools/preparar_certificado_demo.py`
la copia a `installer/demo-certificados/` (carpeta en `.gitignore`) solo para
compilar, y `release-demo.ps1` la borra en el `finally`. Verificado con
`git check-ignore`.

### Que se acepto al publicarlo

Publicar el `.exe` en un release publico deja la clave privada de homologacion
descargable por cualquiera hasta el 11/02/2027. Los tres puntos:

1. **No hay efecto fiscal.** El certificado es de homologacion: los
   comprobantes se descartan y no llegan a un registro real. Tampoco sirve
   contra los servicios de produccion.
2. **Todos los demos comparten CUIT y punto de venta 1.** El par (tipo de
   comprobante, punto de venta, numero) es unico por CUIT, asi que dos demos
   que TAKE el mismo numero se rechazan entre si. **No se pudo verificar con una
   fuente si ARCA admite dos emisiones concurrentes con el mismo CUIT y punto de
   venta en homologacion**: no se da por comprobado. Si aparece, la salida es
   que cada uno use su `pto_vta`.
3. **El CUIT de Vogel queda impreso en todos los comprobantes de la demo.**
   Para una demo mostrada a un cliente es una garantia de que no es real; si
   molesta, se cambia el CUIT del certificado y se rehace el paquete.

### Que pasa cuando vence (11/02/2027)

El certificado deja de servir y el demo abre pero no emite, sin avisar. El
script **aborta** si el certificado esta vencido, asi que no se publica un
instalador nuevo roto:

```
python tools\preparar_certificado_demo.py --verificar     # informa sin copiar
python tools\preparar_certificado_demo.py                 # valida y copia
```

Pedir uno nuevo: se genera el CSR en la pantalla Certificados, se sube a
ManageARCA y se baja el `.crt`. Ojo: el instalador viejo ya publicado **sigue
siendo descargable** y quedara sirviendo sin poder emitir. Conviene borrarlo del
release cuando se rehaga.

### La opcion que se descarto

Que cada cliente genere su propio certificado. No tiene ninguna de las tres
consecuencias de arriba, pero cuesta 15-20 minutos la primera vez y para una
demo en vivo hay que hacerlo antes. Queda disponible: si el certificado vence
y no se quiere pedir otro, sacar el par del `.iss` y el demo vuelve a ese
circuito.

### La mecanica

`installer/Asiento_Demo.iss` copia el `.crt` y la `.key` a
`{app}\certificados\` y precarga el `sistema.ini` en la carpeta de datos del
demo con la seccion `[INI]`, usando las mismas claves y nombres de seccion que
escribe `guardar_config_inicial()`.

Funciona justamente por la regla que se agrego el mismo dia: como la carpeta de
datos del demo tiene un `sistema.ini`, la app la usa y no cae en la carpeta del
programa. Con `configurado = S`, `es_primer_arranque()` da False y el asistente
no aparece: la app abre directo en homologacion con el certificado puesto.

Tres trampas, y las tres tienen test:

- **El `=` del `#define` es opcional en ISPP.** `#define CarpetaDatos "..."`
  compila igual que `#define CarpetaDatos = "..."`. El peligro no es que falle,
  es que al editar la linea quede a medias.
- **El nombre de la carpeta de datos vive en dos lugares**: en el codigo
  (`nombre_build("asiento-demo")`) y en el `.iss`. Si se cambia uno y no el
  otro, el instalador escribe el `sistema.ini` en una carpeta que la app no
  mira: el demo abre como recien instalado y vuelve el asistente. No da error.
  `test_la_carpeta_de_datos_del_instalador_es_la_que_mira_la_app` compara las dos.
- **En Inno Setup 6.3 el `[INI]` cambio de sintaxis**: ahora cada linea pide
  `Section:`, `Key:` y `String:` (no `Value:`), y un `Filename` sin esas tres es
  un error de compilacion. Por eso los tests parsean las entradas en vez de
  buscar texto: el formato ya cambio una vez, y un `assert "configurado=S" in
  demo` se rompe sin avisar que el dato seguia ahi.

Ojo tambien: el certificado tiene que vivir en `installer\`, **nunca en
`dist\`**, porque de ahi saca los archivos la build de PRODUCCION.
`installer/verificar_dist.py` permite archivos en `certificados/` ("vacia esta
bien"), asi que nada lo impide por si solo.

### Reinstalar el demo

`[InstallDelete]` borra el sqlite y `[INI]` vuelve a escribir los valores: al
reinstalar el demo queda como recien instalado, listo para emitir. Si el
operador habia cargado su propio certificado, se pierde. Es lo que se quiere
en una demo, pero conviene saberlo antes de que se queje.

El certificado y la clave se copian con `onlyifdoesntexist`, asi que una
reinstalacion no pisa un certificado que el operador haya cambiado.

## Pendiente

1. ~~**El demo arranca con el asistente de primer arranque.**~~ **Resuelto el
   2026-10-08:** el `[INI]` del instalador precarga la configuracion con
   `configurado = S`, asi que el asistente no aparece. El `sistema.ini` que
   escribe es exactamente el mismo que dejaria el asistente.
2. **Datos de la demo.** Hoy la base arranca vacia: no hay clientes de ejemplo,
   ni productos, ni alicuotas sembradas. Traerla sembrada hace la demo mucho
   mas rapida de mostrar (no hay que cargar nada antes de facturar), pero
   obliga a una semilla versionada y a un camino para regenerarla.
   `tools/sembrar_stock.py` siembra stock; falta lo demas.
3. ~~**El nombre en pantalla.**~~ **Resuelto el 2026-10-08:** el nombre sale de
   `nombre_build()`, que el `[INI]` escribe como `nombre_sistema` y que usan la
   ventana principal, el saludo, Acerca de y el asistente. Ver la seccion "El
   nombre que ve el operador".
4. **Vencimiento del certificado (11/02/2027).** El script aborta si esta
   vencido, asi que no se publica un demo roto. Pero el instalador viejo ya
   publicado sigue descargable y quedara sin poder emitir sin avisar.
   Conviene recordarlo antes de esa fecha.
5. **Colisiones de numeracion.** Todos los demos comparten CUIT y punto de
   venta 1. Si dos demos emiten a la vez, pueden pedir el mismo numero. No se
   pudo verificar si ARCA lo admite; si aparece, cada uno usa su `pto_vta`.