# Etapa 4 — Flujos y feedback: lo que la app te dice mientras trabaja

Fecha: 2026-10-04
Etapa anterior: `docs/ETAPA-3-COMPONENTES.md`
Fase del plan: 4 de 6 (`docs/PLAN_MODERNIZACION_UI.md`)

---

## Qué se hizo

Hasta ahora se había modernize **cómo se ve** la aplicación. Esta etapa es la
otra mitad: **qué dice la app mientras hace algo**, y en particular cuando algo
falla.

El foco es la emisión de una factura, porque es el flujo que toca plata y
depende de un servicio externo. Todo lo que está acá se puede ver en esa
pantalla: cuánto tarda, en qué etapa está, qué pasó y qué hacer.

---

## 1. Los diálogos dejaron de ser todos iguales

### La trampa

`libs/Ventanas.py` tenía **una sola función**, `showAlert`, para las tres cosas
que se pueden necesitar:

| Se usaba para | Cómo se veía |
|---|---|
| "Factura grabada correctamente" | ícono de información, botón **Ok** |
| "Debe seleccionar un cliente" | ícono de información, botón **Ok** |
| "ERROR 1005: el certificado venció" | ícono de información, botón **Ok** |

Un rechazo de AFIP se veía **exactamente igual** que un éxito. No había forma
de distinguir uno de otro sin leer el texto, y el texto tampoco decía qué hacer.

Peor: `QMessageBox.question` con **"Sí" como botón por defecto** significaba
que, con el foco en la pantalla, apretar Enter sin querer creaba el cliente que
uno todavía no había decidido crear.

### La solución

Tres funciones con requisitos distintos, y una cuarta para operaciones largas:

```python
Ventanas.showAlert(titulo, mensaje)          # informar
Ventanas.showError(titulo, mensaje,          # Algo falló
                  que_hacer=..., detalle=...)
Ventanas.showConfirmation(titulo, mensaje)   # Preguntar → devuelve bool
Ventanas.Progreso(titulo, etapas)            # Operación larga, con etapas
```

Tres decisiones que importan:

1. **`showConfirmation` devuelve `bool` y el botón por defecto es cancelar.**
   Enter no puede autorizar una factura.
2. **`showError` tiene una parte de "qué hacer".** El código 1005 de ARCA no le
   sirve a nadie; "el certificado venció, regenerelo desde Configuración >
   Certificados" sí.
3. **El detalle técnico va escondido y con botón de copiar.** A nadie le sirve
   leer 40 líneas de traceback de entrada, pero a soporte le sirve recibirlas.

### Un bug que salió de Rewritear esto

`QMessageBox` sin `QApplication` no tira un error de Python: **tira
`0xC0000409` y se lleva el proceso entero**, sin traceback. Los tests morían en
silencio a mitad de la suite y no se veía por qué.

Ahora `Ventanas.hay_interfaz()` lo pregunta antes, y sin interfaz:

- `showAlert` / `showError` escriben a la consola en vez de desaparecer;
- `showConfirmation` devuelve **False** — sin ventana no se puede preguntar, y
  sin respuesta **no se autoriza**;
- `Progreso` no dibuja nada pero sigue anotando las etapas, así se puede
  verificar.

Esto no es solo para tests: `tools/armar_sandbox.py` y `tools/render_ui.py`
son herramientas de línea de comandos y arrastraban el mismo problema.

---

## 2. Emitir una factura: las etapas que de verdad pasa

### La trampa

Emitir contra ARCA tarda: hay que autenticarse, conectarse, mandar la factura
y pedir el CAE. Durante todo eso la ventana estaba **muerta, sin explicación**.
En una pantalla con 4 botones, un cliente razonable piensa que se colgó y
aprieta Emitir otra vez — lo que en un sistema fiscal es un problema real.

### La solución

Siete etapas **reales**, no una animación:

```
Comprobando los datos
Preparando el número de comprobante
Autenticando en ARCA
Conectando al servicio de facturación
Enviando la factura
Obteniendo el CAE
Guardando la factura
```

Cada una se anuncia desde el punto del código donde ocurre, así que si se cuelga
en alguna, el usuario puede decir exactamente dónde.

**El botón se deshabilita mientras corre**, y vuelve a habilitarse siempre
(está en un `finally`), para que no quede deshabilitado para el resto de la
sesión si algo sale mal.

### Lo que NO se hizo, y por qué

**No se movió la emisión a un hilo.** Sería lo correcto —la UI no debería
congelarse nunca— pero toca el camino fiscal, el más riesgoso del sistema, y
peewee **no es thread-safe**. Queda anotado como trabajo futuro, no como algo
que esté hecho a medias.

---

## 3. Un error ya no aparece dos veces

### La trampa

`CreaFE` está envuelto en el decorador `inicializar_y_capturar_excepciones`, que
**ya muestra su propio `showAlert("Error", ...)`** y después devuelve `None`.
Con el nuevo mensaje accionable, el usuario veía:

1. "Se ha producido un error TypeError: ..." (genérico, del decorador)
2. "No se pudo emitir la factura" + qué hacer + detalle (accionable)

**El mismo problema, dos veces, con dos formatos distintos.** Y el modal del
decorador se abría encima de la barra de progreso.

### La solución

Se agregó `SilenciarError` al decorador. `GrabaFactura` lo activa mientras corre
la emisión, porque es quien tiene el contexto y va a mostrar el error bien. El
detalle queda guardado en `self.Excepcion` / `self.Traceback` y se muestra
después, una sola vez, con el formato correcto.

Lo mismo con el rechazo de ARCA: antes `CreaFE` abría un `showAlert` con el
motivo del rechazo en el medio de la emisión. Ahora lo guarda en
`self._error_afip` y el mensaje final lo incluye.

---

## 4. Diagnóstico ARCA: dice qué hacer, no solo qué pasó

Antes el diagnóstico devolvía un texto plano con los pasos y sus estados. Bien
para soporte, inútil para el usuario que tiene la app abierta y una factura por
emitir.

Ahora cada paso que falla trae su consejo:

| Paso | Qué le dice al usuario |
|---|---|
| Configuración | Qué clave falta y que los certificados se generan desde Configuración > Certificados |
| WSAA | Casi siempre es el certificado: puede estar vencido o no ser del CUIT cargado |
| WSFE conexión | Salida a internet, proxy, firewall hacia `servicios1.afip.gov.ar` |
| WSFE Dummy | Suele ser transitorio: reintentar en unos minutos |

El resultado se abre con `showError` si algo falló (con el consejo) y con
`showAlert` si todo está bien (con el informe). Antes siempre salía igual.

`ejecutar()` ahora acepta `al_avanzar`, que se llama **antes** de cada paso,
así que la barra de progreso dice la verdad: si se cuelga, se ve en cuál.

---

## 5. Venta rápida: atajos y no perder el trabajo tipeado

### Atajos

| Atajo | Qué hace |
|---|---|
| `Ctrl+Return` | Agregar el producto |
| `Ctrl+E` | Emitir la factura |
| `Ctrl+B` / `Delete` | Borrar el renglón |
| `F2` | Ir al campo de producto |
| `Esc` | Cerrar |

Cada botón muestra su atajo en el tooltip, así que no hay que acordarse.

**Al agregar un producto el foco vuelve al campo de producto.** Cargar una venta
es agregar línea por línea; si hay que ir al mouse entre renglones, los atajos
no sirven de nada.

### El bug que aparecería al agregar `Esc`

`Cerrar()` cierra y listo: sin preguntar. Con `Esc` al final, una venta con
cinco renglones cargados se perdía sin avisar.

Ahora cerrar pregunta **solo si hay renglones**: con la venta vacía no hay nada
que perder y no se molesta al usuario; con productos cargados, avisa. El botón
de cerrar hace lo mismo, por coherencia.

---

## 6. Acerca de, con el dominio

El dominio `vogelconsultoria.com.ar` no aparecía en ningún lado de la app. Ahora
está en **Acerca de**, al pie de la barra lateral — fuera del scroll, para que no
se pierda de vista en listas largas.

Va con versión, empresa, web, WhatsApp, y una instrucción concreta: ante una
falla de conexión con ARCA, copiar el detalle del error y enviarlo.

### Tres cosas que aparecieron al hacerlo

1. **El botón decía "Close".** `QDialogButtonBox` toma el texto del idioma del
   sistema; en una pantalla toda en castellano, en inglés. Reemplazado por un
   `QPushButton("Cerrar")`.
2. **La versión nunca se mostró, nunca.** `MainView._version()` buscaba una
   clave `versionName` en `version.txt` que **el archivo no tenía** — y nada en
   el proyecto la escribía. La barra de estado y Acerca de salían vacíos desde
   siempre, sin error. Se agregó la clave y el parser ahora cae a `filevers` o
   `ProductVersion` si alguien regenera el archivo.
3. **`version.txt` todavía decía "Servin LGSM" y "Sistema".** La Etapa 1
   renombró el producto y el archivo quedó atrás. Ahora dice Asiento / Vogel
   Consultoria.

También: el botón se estiló con los colores de un panel **oscuro** y el sidebar
es **claro** (`#EEF2F8`). Quedó en 2.3:1 de contraste, ilegible. Corregido
contra el fondo real —se vio en el render, no en el código—.

---

## 7. El bug más grave: instalando el .exe, la base quedaba vacía

Este no lo pedía la fase. Salió de **correr el ejecutable de verdad**, y es el
que más cambia todo lo que había antes.

### La trampa

`MigracionBaseDatos.cargar_csv()` abre los datos maestros con **ruta relativa**
—`data/tipoiva.csv`, `data/formapago.csv`— y `compila.bat` **nunca copiaba la
carpeta `data/` a `dist/`**.

Peor: el `open(archivo)` no estaba protegido. El primer archivo faltante cortaba
**toda** la siembra y la excepción subía. En el log del `.exe`:

```
FileNotFoundError: [Errno 2] No such file or directory: 'data/tipodoc.csv'
```

### Qué pasaba en una máquina nueva

La app arrancaba, se veía perfecto, y **no había forma de emitir nada**:

| Maestro | Filas |
|---|---|
| Alícuotas de IVA | 0 |
| Tipos de documento | 0 |
| Tipos de comprobante | 0 |
| Formas de pago | 0 |
| Provincias y localidades | 0 |

En "Venta rápida", el combo de **Forma de pago** se veía vacío. Y como
`GrabaFE` hace `Formapago.get_by_id(...)`, la factura no se podía guardar.

Todo esto pasaba **solo en el ejecutable**. En desarrollo andaba perfecto,
porque ahí `data/` está en la raíz. Por eso ningún test lo había visto.

### La solución

Tres capas, porque una sola no alcanza:

1. **`compila.bat` copia `data\*.csv` a `dist\data\`.** Solo los CSV: la carpeta
   trae también `pablo.db`, que es una base de pruebas ajena al producto y no
   tiene que viajar en el instalador.
2. **`cargar_csv` no corta la siembra.** Cada faltante se anota en el log y se
   sigue con el resto. Que falte un maestro no puede impedir cargar los otros.
3. **`installer/verificar_dist.py` exige `data/`** con los 11 maestros
   imprescindibles, igual que exige `temas/pyfe.css`.

### Verificado

Instalación limpia de verdad (`_prueba_exe` con solo `dist/`), ejecutando el
`.exe`, pasando el asistente:

```
tipoiva              3      (IVA 21 / 10.5 / no gravados)
tipodoc              6
tiporesp             4
formapago            2      (EFECTIVO / CUENTA CORRIENTE)
provincias          15
localidades          3
cajero               1
```

El combo de Forma de pago muestra **EFECTIVO**. Las únicas tablas vacías son
las de movimientos (facturas, remitos, correos), que es lo correcto en una
instalación nueva.

### Por qué importa más allá de esta etapa

Es el criterio de "probar el ejecutable" haciendo trabajo. Dos veces en una
sola etapa —la versión y los datos maestros— la app estaba bien en los renders
y en los tests, y mal en el `.exe`. **Un test que corre contra el código no
verifica el empaquetado.**

---

## Archivos tocados

| Archivo | Qué cambió |
|---|---|
| `libs/Ventanas.py` | Reescrito: showAlert / showError / showConfirmation / Progreso, y seguro sin interfaz |
| `libs/Utiles.py` | El decorador respeta `SilenciarError` (apaga el diálogo, no el reporte) |
| `controladores/Facturas.py` | Confirmación, etapas, error único y accionable |
| `controladores/VentaSimple.py` | Atajos, foco, descarte de venta con confirmación |
| `controladores/DiagnosticoAfip.py` | Consejo por paso, etapas reales, `que_hacer` / `titulo` |
| `controladores/Main.py` | Diagnóstico con progreso y error accionable |
| `controladores/MigracionBaseDatos.py` | Un CSV faltante ya no corta toda la siembra |
| `vistas/Main.py` | Pie con Acerca de; versión leída de la estructura real |
| `temas/pyfe.css` | Estilos del pie y del diálogo |
| `version.txt` | Marca actualizada (Asiento / Vogel Consultoria) |
| `compila.bat` | Copia `version.txt` y `data\*.csv` a `dist\` |
| `installer/verificar_dist.py` | Exige `version.txt` y `data\` con los maestros |
| `tools/render_ui.py` | Soporte para renderizar un método fábrica (el diálogo de Acerca de) |

## Tests

**241 en verde.** Los nuevos:

| Archivo | Qué cubre |
|---|---|
| `tests/test_ventanas.py` | Diálogos sin interfaz; el error no pierde el "qué hacer"; `SilenciarError` apaga el diálogo pero no el reporte |
| `tests/test_acerca_de.py` | Versión presente y con fallback; `version.txt` parseable por PyInstaller; dominio; botón en castellano |
| `tests/test_venta_simple_atajos.py` | Los 6 atajos registrados, foco, descarte de venta |
| `tests/test_datos_maestros.py` | Los maestros están, `dist/data` viaja, un faltante no corta la siembra |
| `tests/test_facturas_condicion_iva.py` | Cancelar no emite; etapas; error único |

### Tres cosas que los tests aprendieron

**Un atajo que no se registra no da error.** `QShortcut` se crea, se conecta y
se garbage-collectea: la pantalla anda perfecto y el atajo no hace nada. El
test compara `QKeySequence` y no strings, porque Qt normaliza —la que se
escribe `Delete` se reporta como `Del`— y comparar strings daba un falso
negativo que tapaba justo el bug que se buscaba.

**`hasFocus()` es `False` para todo con la ventana inactiva**, que es lo que hay
en offscreen. El test usa `focusWidget()`, que sí distingue.

**`version.txt` lo lee PyInstaller con `eval()`.** Al agregar la clave
`versionName` para que la app pudiera leerla, **rompí la compilación entera** con
`Failed to deserialize VSVersionInfo`. El archivo tiene que ser *una sola
expresión* de Python. Hay un test que lo parsea para que no vuelva a pasar, y
la versión se lee de `ProductVersion` / `FileVersion`, que ya estaban ahí.

## Verificación

- `python -m pytest tests\` → **241 en verde**
- `python tools/render_ui.py` → **8/8**, incluido el nuevo `AcercaDe`
- `python installer\verificar_dist.py` → distribución completa
- **Ejecutable compilado, instalación limpia**: asistente → pantalla principal →
  venta rápida → Acerca de, todo verificado a pantalla. La versión aparece en la
  barra de estado, el dominio en Acerca de, y las formas de pago cargadas.

---

## Pendiente

- **Mover la emisión a `QThread`.** Es lo correcto; queda fuera de esta etapa
  por tocar el camino fiscal con peewee, que no es thread-safe.
- **El PDF no se pudo renderizar para probar el pie de factura.** Bloqueado por
  el conflicto de `fpdf`: el entorno tiene `fpdf2` y `pypdf` instalados a la vez
  sobre el mismo espacio de nombres, y `pyafipws` usa la API de `fpdf 1.7.2`.
  **Sigue sin confirmarse si esto también pasa en la máquina donde se factura**,
  que es lo que decide si es un problema de esta máquina o del producto.
- **Issue #32** (qué pantalla es la de emitir) sigue esperando una decisión de
  producto.
- ~~**`installer/PyFE.iss`** conserva el nombre de archivo.~~ **Resuelto el
  2026-10-08:** ahora es `installer/Asiento.iss`, igual que `RND.iss` y
  `FEMAG_Desktop.iss` en los otros productos. El `AppId` es un GUID, asi que el
  rename no cambia la identidad del producto en "Agregar y quitar programas":
  las instalaciones existentes se reconocen igual y el desinstalador sigue
  desinstalando la misma app.
- **El reporte automático de errores** sigue yendo a `fe@servinlgsm.com.ar` con
  el nombre del desarrollador anterior. No se tocó: cambiar a dónde llegan los
  avisos de producción es una decisión, no un cleanup.
