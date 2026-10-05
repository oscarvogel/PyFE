# Actualización automática de Asiento desde vogel-releases

Fecha: 2026-10-05
Rama: `codex/vogel-gestion-simple-mvp`
Estado: núcleo commiteado (`94cc98d`); el enganche en 4 archivos quedó
pendiente porque se mezclaba con trabajo de otra sesión. **La publicación
está bloqueada** porque la suite del repo está en rojo por trabajo ajeno a
este. Pendiente el E2E en una PC real.

## Qué hace

Al abrir Asiento, la app consulta el manifiesto público de su producto en
`oscarvogel/vogel-releases` y, si hay una versión más nueva:

1. muestra las novedades de todo lo que el usuario se salteó, o solo el aviso
   de actualización si ya está al día;
2. pregunta si se descarga;
3. descarga el instalador a `%TEMP%` **calculando el SHA256 durante la
   descarga** y comparándolo con el del manifiesto;
4. solo si coincide, ejecuta el instalador y cierra la app.

Si algo falla en cualquier paso —no hay internet, el manifiesto está raro, el
hash no da, el usuario cancela— la app abre igual y sigue funcionando. Ninguna
excepción del actualizador llega al arranque.

## De dónde salió

No es un diseño nuevo: es el mismo mecanismo que ya está en producción en
`oscarvogel/femag_desktop` (que es desktop y publica con SHA256, el caso más
parecido) y en `oscarvogel/fgpy` / `oscarvogel/forestal` (que además tienen el
historial de novedades acumulable). Copia de esos:

| Pieza | femag_desktop | fgpy / forestal | **Asiento** |
|---|---|---|---|
| Manifiesto | `apps/femag/latest.json` | `apps/<id>/latest.json` | `apps/asiento/latest.json` |
| Asset | `FEMAG_Desktop_Produccion_Setup.exe` | `FGPY_Produccion_Setup.exe` | `Asiento_Produccion_Setup.exe` |
| Identidad del build | `app/build_info.py` | `utiles/build_info.py` | `libs/build_info.py` |
| Cliente | `app/services/update_service.py` | `servicios/actualizaciones.py` | `libs/actualizaciones.py` |
| Historial | no tiene | `servicios/changelog.py` | `libs/changelog.py` |
| Publicación | workflow en Actions | workflow + script local | `release.ps1` (local) |
| TLS | `truststore` | urllib directo | urllib directo |

Se usa `libs/` y no `utiles/`+`servicios/` porque esas carpetas no existen en
este repo: la estructura real es `libs/`, `controladores/`, `modelos/`,
`vistas/`.

### Una diferencia deliberada: sin `truststore`

femag mete la dependencia `truststore` para el TLS. PyFE **no** la lleva.
`truststore` existe para que el almacén de confianza del sistema operativo
funcione en Linux y macOS cuando hay un `certifi` de por medio. PyFE es solo
Windows, y ahí urllib ya valida contra el almacén de confianza del SO sin
ayuda. Agregarla sería una dependencia nueva para resolver un problema que en
esta plataforma no existe.

Si alguna vez Asiento corre en otra plataforma, esto hay que revisarlo.

## Archivos

| Archivo | Qué es |
|---|---|
| `libs/build_info.py` | `APP_ID` y `BUILD_VERSION`. Versionado con valores **inertes** de desarrollo. |
| `libs/actualizaciones.py` | Consulta del manifiesto y descarga verificada. Sin Qt. |
| `libs/changelog.py` | Historial de novedades y qué falta mostrar. Sin Qt. |
| `controladores/Actualizador.py` | Los diálogos, la barra de progreso y el cierre. Todo el Qt. |
| `tools/generar_build_info.py` | Escribe `build_info.py` y `version.txt` con el timestamp del build; y los restaura. |
| `release.ps1` | El ciclo entero de publicación. |
| `tests/test_actualizaciones.py` | 16 tests del cliente. |
| `tests/test_changelog.py` | 10 tests del historial. |
| `tests/test_build_info_release.py` | 8 tests del contrato de build. |
| `tests/test_actualizador_controlador.py` | 7 tests del controlador. |

## El contrato (no romper)

1. **Nada se ejecuta sin SHA256 verificado.** El hash se calcula en la misma
   pasada que la descarga, no con una lectura aparte: así no hay ventana en la
   que el `.part` pueda cambiar entre las dos cosas. Si no coincide, el `.part`
   se borra y no se ejecuta nada.

2. **Una falla de red nunca impide abrir la app.** `check()` propaga la
   excepción y el llamador la loguea. No devuelve "no hay actualización" ante
   un error, porque el usuario se quedaría sin actualizaciones sin entender
   por qué.

3. **El estado no se escribe en `sistema.ini`.** La marca de "ya vi las
   novedades" vive en `%LOCALAPPDATA%\asiento\update-state.json`. El `ini` lo
   escribe la app, lo crea el asistente de primer arranque y guarda los datos
   de facturación. Además **fuera de `{app}`** a propósito: el instalador
   reemplaza entera la carpeta de programa en cada actualización, y un estado
   guardado adentro se perdería con cada versión.

4. **El historial es acumulable.** Cada publicación *agrega* una entrada y
   nunca trunca. Si el usuario salta de la 10:00 a la 13:00, ve juntas las
   novedades de las 11:00, 12:00 y 13:00.

5. **Aislamiento por producto.** El `app_id` del manifiesto tiene que coincidir
   con el del build compilado. Sin esto, un manifiesto de FEMAG copiado al de
   Asiento haría que Asiento ofrezca el instalador equivocado.

6. **En desarrollo el actualizador queda deshabilitado.** El archivo
   versionado tiene `APP_ID = "development"`, así que correr la app desde el
   repo no baja el instalador de producción encima de una base de pruebas.

7. **El manifiesto se sube antes que el asset.** Al revés, si la subida del
   `.exe` fallara, el manifesto quedaría describiendo una versión cuyo
   instalador todavía no se puede bajar.

8. **`sistema.ini` no puede entrar en `dist/`.** `release.ps1` lo verifica
   antes de armar el instalador. Si llegara a `dist`, InnoSetup lo instalaría
   en `{app}` y en la siguiente actualización lo trataría como archivo suyo y
   lo pisaría.

## Publicar una versión

```powershell
# Probar el build sin subir nada
.\release.ps1 -SinPublicar

# Publicar
.\release.ps1 -Notas "Manejo de stock; Pantalla de emision rediseñada"

# Con notas tomadas de los commits desde la ultima version
.\release.ps1
```

El script marca la identidad del build, corre los tests, compila con
`compila.bat`, verifica `dist/`, arma el Inno Setup, calcula el SHA256, sube
el asset con nombre estable, escribe `latest.json`, **agrega** la entrada al
`changelog.json` y deja `build_info.py` y `version.txt` como estaban (en un
`try/finally`, para que una publicación fallida a mitad no deje el repo
marcado como una versión que nunca se publicó).

El token de GitHub se pasa con `-Token` o usa la sesión de `gh` que haya. Las
PC de los usuarios no guardan ningún token.

### Formato de versión

`yyyy.MM.dd.HH.mm.ss` en **UTC**, el mismo que usan femag, fgpy y forestal. La
versión real del build es `BUILD_VERSION` en `libs/build_info.py`, igual que en
femag: no se saca del nombre del `.exe` ni de `version.txt`.

Lo que sí se hace, además, es escribir el timestamp también en `version.txt`,
para que Windows muestre la versión real en Propiedades del archivo y el
soporte no tenga que adivinarla. `version.txt` lo lee PyInstaller con `eval()`
y tiene que ser **una** expresión de Python: por eso el generador hace
reemplazos sobre el archivo en vez de reescribirlo.

## Bugs encontrados y cómo se detectaron

Anotados porque son el tipo de cosa que vuelve si nadie lo escribe.

1. **`UpdateService()` sin argumentos reventaba en desarrollo.** El
   constructor llamaba a `manifest_url_for(app_id)`, y con `app_id="development"`
   esa función lanza `ValueError`. Es decir: el guardián que debía evitar que
   el actualizador corra en desarrollo era lo primero que tiraba abajo. Lo
   detectó `test_el_chequeo_se_habilita_solo_en_build_productivo`. Ahora el
   constructor no valida y la falta de manifiesto se reporta al usar la URL.

2. **Las novedades se marcaban como vistas aunque el diálogo no se mostrara.**
   El `mark_seen()` estaba dentro de un `try/finally`. Con `finally`, si el
   diálogo fallaba al abrir, el changelog quedaba marcado como visto y el
   usuario no volvía a ver esas novedades nunca más. Lo detectó
   `test_las_novedades_se_marcan_solo_si_se_mostraron`. Ahora va después del
   `exec_()`, sin `finally`.

3. **Un carácter de reemplazo (U+FFFD) en un docstring.** Rompió
   `test_no_hay_caracteres_de_reemplazo_en_el_codigo`, que ya existía en el
   repo. Por suerte ese test existe.

4. **`tools/validar_manifiesto_vogel.py` no sirve para validar un manifiesto
   nuevo.** Lee los manifiestos con `gh api` desde GitHub, así que valida lo ya
   publicado y no el archivo que uno acaba de escribir: daría verde con un
   manifiesto roto. `release.ps1` valida el archivo **local** contra el mismo
   schema en `Test-ManifestValido`.

5. **Un detalle del schema que casi rompe la publicación.** El schema de
   `vogel-releases` declara `additionalProperties: false`, y femag y fgpy
   escriben un campo `channel` que el schema prohíbe. Si Asiento lo hubiera
   copiado, el próximo que valide los manifiestos del repo va a ver fallar
   todo junto. Por eso `latest.json` de Asiento **no** lleva `channel` y
   `release.ps1` lo chequea explícitamente.

6. **`version.txt` con timestamp: verificado, no supuesto.** El encabezado del
   archivo advierte que agregarle una línea suelta rompe la compilación con
   "Failed to deserialize VSVersionInfo". Como la versión pasó de `0.9.0` a
   un timestamp de 6 componentes, se hizo que **PyInstaller 6.19 instalado en
   esta máquina** lo parsee y lo serialice
   (`load_version_info_from_text_file` + `toRaw()`, 928 bytes de recurso).
   `test_el_version_txt_generado_lo_parsea_pyinstaller` lo hace en cada
   corrida. Ojo: el bloque `ffi` de `VSVersionInfo` es de 4 DWORD fijos, así
   que del timestamp de 6 componentes solo entran los primeros cuatro; eso
   está chequeado aparte.

7. **ISCC no está en el PATH de esta máquina.** Inno Setup 6 está instalado
   por usuario, en `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`, que no es
   ninguna de las rutas donde se lo busca por defecto. `release.ps1` prueba las
   tres. Esto no lo introdujo el actualizador: `compila.bat` termina con
   `iscc PyFE.iss` y tampoco lo encontraba, así que hoy no se puede armar un
   instalador en esta máquina sin esa ruta.

8. **`version.txt` quedó sin tocar.** Sigue con `0.9.0`, que es lo que quiere
   el árbol en desarrollo. El timestamp lo escribe `release.ps1` en el
   momento del build y lo saca en el `finally`. No hace falta dejar el
   timestamp commiteado: cambiaría en cada publicación y ensuciaría el
   historial del repo con una línea que no dice nada.

9. **El generador reescribía `libs/build_info.py` entero y le borraba las
   funciones.** Este es el más grave, y solo apareció al publicar de verdad.
   `tools/generar_build_info.py` regeneraba el archivo desde una plantilla de
   dos líneas, con lo cual `manifest_url_for`, `es_build_productivo` y
   `changelog_url_for` desaparecían: **la app compilada no podía consultar
   actualizaciones**. Los 718 tests pasaban en verde porque corren contra el
   archivo versionado, nunca contra el generado. Lo atrapó el propio
   `release.ps1`, en los tests, antes de compilar.

   Ahora el generador **reemplaza solo las dos líneas** y después relee el
   archivo para comprobar que quedaron bien (`_verificar`). Cubierto por
   `test_el_build_info_generado_sigue_siendo_un_modulo_que_funciona`, que
   importa el archivo generado y llama las funciones. Ese test se verificó
   contra el código roto a propósito: falla con
   `no attribute 'es_build_productivo'`.

10. **El chequeo estaba en `Main.__init__` y colgaba la suite.** Con el build
    en estado de producción, cualquier test que armara el controlador
    (`test_componentes.py` construye el `Main` real para leer sus `DESTINOS`)
    lanzaba una descarga de verdad y se quedaba esperando el hilo: la suite
    se clavaba en el 75%. El chequeo de versión es del arranque de la
    aplicación, no de construir sus piezas, así que ahora lo llama
    `main.py::_chequear_actualizaciones`, después de que la ventana está en
    pantalla. Cubierto por
    `test_construir_el_controlador_no_dispara_la_red`.

11. **Los tests corren antes de marcar la identidad del build.** Varios tests
    comprueban que el archivo versionado dice `app_id = "development"` (es lo
    que deshabilita el actualizador). Si la identidad se marcara antes de
    correrlos, verían un build de producción y fallarían, y el release no
    publicaría nunca. Además, así un test que falla no dejó ningún archivo del
    repo tocado.

## Notas de instalación

- Inno Setup 6 debe estar instalado para armar el instalador. En esta máquina
  está en `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`.
- `gh` debe estar autenticado con permiso de escritura en
  `oscarvogel/vogel-releases`, o hay que pasarle `-Token`.
- PyFE **no** tiene GitHub Actions: el build es local, con `compila.bat` y el
  Python de la máquina. El `release.ps1` corre los tests antes de compilar, así
  que una suite roja no llega a publicar nada.

## Qué falta

Nada de esto está verificado todavía:

0. **La primera publicación está bloqueada.** Cuando se intentó publicar
   (2026-10-05), la suite estaba en rojo por trabajo a medio terminar de otra
   sesión en el mismo repo: `test_migraciones_stock.py` y
   `test_password_mysql.py` fallaban por `modelos/ModeloBase.py` y
   `libs/Utiles.py` en movimiento. El `release.ps1` hizo lo correcto:{detuvo
   la publicación y restauró el estado de desarrollo. **No publicar con la
   suite en rojo**, aunque el rojo no sea de este trabajo: el build arrastra
   todo el código, no solo el actualizado.

1. **E2E en una PC real.** Es lo que falta y es obligatorio:
   1. instalar una versión A y confirmar que abre y factura;
   2. guardar el hash SHA256 de `sistema.ini` y de la base;
   3. publicar B con `release.ps1`;
   4. abrir A y confirmar el aviso;
   5. descargar, y confirmar que el hash del instalador da;
   6. instalar, confirmar que está B y que puede facturar;
   7. confirmar que `sistema.ini` quedó byte a byte igual;
   8. reabrir B y confirmar que no repite las novedades;
   9. publicar un manifiesto con `app_id` de otro producto y confirmar que
      Asiento lo rechaza sin romperse.

2. **La primera publicación real.** El manifiesto de `asiento` que ya está
   publicado dice `2026.10.05.08.37.00`, pero el instalador de ese momento se
   compiló con `version.txt` en `0.9.0`: **la versión del manifiesto y la del
   `.exe` instalado no coinciden**. Cualquier instalación de esa versión no
   puede compararse bien contra el manifiesto y no va a ver actualizaciones.
   Hay que republicar con `release.ps1` para que las dos cosas digan lo mismo.

3. **`apps/asiento/changelog.json` no existe todavía.** Lo crea la primera
   publicación. Hasta ese momento no hay historial de novedades, solo el
   `notes` del `latest.json`.

4. **El nombre del producto en algunos lugares.** `docs/ETAPA-2-NAVEGACION.md`
   señala que `PyFE.iss` decía `AppName "PyFE"` / `AppPublisher "Servin LGSM"`.
   Eso **ya está corregido** a Asiento / Vogel Consultoria. Lo que sigue
   pendiente es que `sistema.ini` de instalaciones viejas tiene
   `nombre_sistema = Servin - Sistema Factura Electronica`.

5. **Canal `candidate`.** fgpy y femag tienen un segundo canal para pilotos con
   un proceso de aprobación y promoción. Asiento va solo con `latest` a
   propósito: agregar el canal es agregar machinery que alguien tiene que
   mantener, y no hay un proceso de piloto que lo use hoy.

## Cómo saber si algo se rompió

```powershell
# El estado del build ahora mismo (productivo o desarrollo)
python tools\generar_build_info.py --verificar

# Los manifiestos del repo contra su schema (lee de GitHub)
python tools\validar_manifiesto_vogel.py --app asiento
```

Y el log: el actualizador loguea a `all.log` (el logger de la app). Los
errores de descarga y de consulta quedan ahí, con el traceback.
