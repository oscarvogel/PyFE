# El selector de producto no entra en el trabajo de cargar una venta

## Qué se reportó

Del reporte, tres cosas, sobre el mismo par de pantallas:

1. El diálogo **"Seleccionar producto"** tiene que ser **más ancho**.
2. La lista del selector tiene que mostrar el **precio al público**.
3. En la venta, el campo **Producto** tiene que poder buscar por **código de
   barra**.

Las dos capturas del reporte:

1. **"Seleccionar producto"** con `acc` escrito: 4 filas de access points,
   con nombres larguísimos y **sin ningún precio**. La ventana de la captura
   ocupa casi todo el ancho de la pantalla, o sea que el operador ya la había
   agrandado a mano para poder leer.
2. **"Nueva venta"** con `acc` en el campo Producto y la venta todavía vacía:
   el operador está escribiendo a ciegas, sin lista y sin precios.

## Los tres pedidos, y dónde está cada uno

| # | Pedido | Archivo | Línea |
|---|---|---|---|
| 1 | Selector más ancho | `vistas/VentaSimple.py` | `296` |
| 2 | Precio al público en la lista | `vistas/VentaSimple.py` | `369-374` (`_texto`) |
| 3 | Buscar por código de barra | `controladores/VentaSimple.py` | `534` |

---

## 1. El selector tiene que ser más ancho

Hoy: `self.resize(560, 420)` en `VentaSimpleSeleccionArticuloDialog.setupUi`.

La fila más larga de la captura es esta:

```
4 - ACCESS POINT EXTENSOR WIFI TP-LINK RE200 AC750 DUAL BAND 2.4GHZ 300MBPS / 5GHZ 450MBPS - 104872
```

Son ~110 caracteres. A 560 px de ancho, `QListWidget` entra ~60-65, o sea
que **la mitad del nombre no se ve**. Y como el nombre es lo único que
distingue un access point de otro, leerlo es el trabajo entero de esa
pantalla.

La captura es la prueba: mide ~950 px de ancho, y el código pide 560. Como
`resize()` corre en cada construcción, el operador **no puede estar
recordándolo**: hay que arrastrar la ventana cada vez que se abre. Eso es
justo lo que "tiene que ser más ancho" viene a decir.

### Cómo se decide el ancho (sin adivinar)

No alcanza con "ponerle 900": tiene que entrar el nombre real más largo del
catálogo, con el precio agregado del pedido 2.

- **`tools/medir_ventanas.py` no sirve para esto**, y conviene dejarlo escrito
  antes de que alguien lo intente: el `sizeHint()` que mide ese script mide
  lo que el **layout** pide, no el texto de los ítems de una lista. Un
  `QListWidget` que muestra nombres largos no crece: se corta. El propio
  docstring del script avisa que "lo que no mide" es justamente el recorte de
  contenido.
- Lo que sí mide es `QFontMetrics.horizontalAdvance()` sobre el texto de la
  fila, comparado con el ancho del viewport de `listaArticulos`. La fila más
  larga del catálogo, con el precio al público ya formateado, es el número
  que fija el ancho mínimo.

**Criterio de aceptación:** el nombre completo del artículo más largo se lee
sin puntos suspensivos ni scroll horizontal, con el precio al público visible
en la misma fila.

## 2. La lista tiene que mostrar el precio al público

Hoy `_texto()` arma la fila así:

```python
def _texto(self, articulo):
    codigo = str(articulo.codbarra or "").strip()
    if codigo:
        return "{} - {} - {}".format(articulo.idarticulo, articulo.nombre, codigo)
    return "{} - {}".format(articulo.idarticulo, articulo.nombre)
```

El precio no está. Y `preciopub` existe y anda: es el que ya se usa como
precio por defecto en `VentaSimpleCantidadPrecioDialog`
(`controladores/VentaSimple.py:438`).

El operador buscando `acc` está eligiendo entre 4 access points que se
diferencian por el modelo, y **no puede compararlos**: elige a ciegas y se
enter del precio cuando ya está en la pantalla de cantidad y precio, con el
renglón cargado. Con la lista mostrando precio, comparar es parte de elegir.

### Detalles que hay que decidir antes de escribir la línea

- **Formato del número.** Reusar `_formato_importe` de `libs.Grillas`, que ya
  está importado en `controladores/VentaSimple.py:16` y es el que usa la
  grilla de la venta. Importes con separador de miles y 2 decimales, no el
  `Decimal` crudo.
- **Precio sin cargar.** `preciopub` es `DecimalField(max_digits=12,
  decimal_places=4, default=1)` (`modelos/Articulos.py:21`): el default es 1,
  pero en una base vieja puede venir `NULL`. `Decimal(str(None))` revienta, así
  que la fila tiene que banker el `None` (punto, o vacío) en vez de dejar que
  la lista muera al buscar `poe`.
- **Dónde va.** Acá está la decisión de verdad, porque la fila hoy es un
  `QListWidget` con **un solo string por ítem** (`addItem(self._texto(articulo))`).
  Hay dos caminos y conviene elegir a propósito:
  - **A) Precio al final de la fila, en el mismo string.** Es el cambio más
    chico y no toca nada de la estructura. El precio queda pegado al código de
    barras y no alineado, así que comparar dos precios de la lista es de memoria.
  - **B) `QTreeWidget` con columnas** (Descripción / Código de barras / Precio).
    Los precios se alinean a la derecha y de verdad se comparan, pero cambia el
    tipo de widget, el `currentRow()` deja de ser el índice de `self.articulos`
    tal cual, y `accept()`/`_elegir_para_entrar()` hay que reworkear.

  B es la que corresponde si el pedido es "comparar precios"; A es la que
  corresponde si el pedido es "ver el precio". **Recomendación: B**, porque
  el pedido 2 sin alineación es medio cumple, y porque el ancho del pedido 1
  hace falta igual. Si se elige A, dejarlo escrito que el precio no alineado
  fue una decisión, no un olvido.

- **Cuidado con el orden de las columnas:** `idarticulo` primero es lo que hay
  hoy y no hay por qué sacarlo; el precio va al final.

## 3. El campo Producto tiene que buscar por código de barras

Acá hay un hallazgo que va más allá de lo que pidió el reporte.

### Lo que promete la pantalla

El `placeholderText` del campo del selector ya dice:

> "Buscar por nombre, código o código de barras"

`vistas/VentaSimple.py:302-303`. **Hoy eso es falso.**

### Lo que hace la consulta

`_coincidencias_articulo` (`controladores/VentaSimple.py:534`) busca **solo por
nombre**:

```python
consulta = Articulo.select().where(buscar_texto(Articulo.nombre, texto))
```

`buscar_texto` es `contiene` de `libs.busqueda`, y funciona igual sobre
cualquier columna, pero acá solo se le pasa `Articulo.nombre`.

El único camino donde el código de barras entra es el **exacto**:
`_articulo_exacto` (línea ~506) prueba `Articulo.codbarra == texto`, y por eso
un código de barras **completo** sí funciona hoy. Un código de barras
**parcial**, no.

### El daño real: el camino "no encontrado" crea artículos duplicados

Este es el motivo por el cual el punto 3 no es una comodidad. En
`agregar_articulo` (`controladores/VentaSimple.py:358-372`):

```python
if self._articulo_es_ambiguo(busqueda):        # 2 o mas -> abre el selector
    ...
articulo = self.buscar_articulo(busqueda)
if not articulo:
    if not self.confirmar_alta(
            "Venta", "Producto no encontrado. Desea agregarlo?",
            textoOk="Crear producto"):
        return
    articulo = self.solicitar_alta_articulo(busqueda)   # <-- alta de un duplicado
```

Con el barcode parcial, `_articulo_es_ambiguo` da `False` (0 coincidencias),
`buscar_articulo` devuelve `None`, y la pantalla ofrece **crear un producto
nuevo**. El operador con el lector de códigos en la mano teclea los primeros
6 dígitos de `104872` y el sistema le pregunta si quiere dar de alta un
artículo que **ya existe**, con otro código de barra, duplicándolo en el
catálogo.

O sea: el pedido 3, en el camino corto, es un problema de datos, no de
comodidad. Por eso el punto 3 no se puede "dejar para otro momento" aunque el
selector ahora muestra el código de barras en la fila.

### El arreglo es chico

`contiene` ya está importado como `buscar_texto` y no depende de la columna.
La consulta tiene que matchear nombre **o** código de barras, con el `|` de
peewee. `codbarra` es `CharField(max_length=20, column_name='codbarraart')`
(`modelos/Articulos.py:35`): es texto, así que el contains parcial funciona y
los ceros a la izquierda de un lector no se pierden.

Dos detalles al hacerlo:

- **Orden.** Con contains, `10487` matchea `104872` y también `1104872`. Hay
  que ordenar las coincidencias exactas primero, o el operador escanea y
  lo primero que ve es una lista de parciales.
- **Consistencia con la ambigüedad.** `_articulo_es_ambiguo` ya va a pasar a
  dispararse más seguido (dos artículos pueden compartir un prefijo de
  barcode), y en ese caso abre el selector. Eso es lo correcto según la regla
  de `docs/SELECCION-PRODUCTO.md` ("con dos o más no se elige nada"), así que
  **no hay que cambiarlo**: hay que dejarlo escrito que es lo esperado.

---

## Cómo se sabe que quedó bien

| # | Criterio |
|---|---|
| 1 | El nombre completo del artículo más largo se lee entero, con el precio al final, sin scroll horizontal |
| 2 | La lista muestra el precio al público formateado como importe, alineado, con miles y 2 decimales |
| 3 | Un artículo con `preciopub` NULL aparece con precio vacío y **no** rompe la búsqueda |
| 4 | Escribir el código de barras completo trae ese artículo |
| 5 | Escribir **un fragmento** del código de barras trae el artículo, y con un solo fragmento coincidente **no** ofrece "Crear producto" |
| 6 | Un fragmento que coincide con 2 o más artículos abre el selector acotado, sin elegir ninguno solo |
| 7 | Un texto que no es nombre ni código de barras **sigue** ofreciendo darlo de alta (ese camino no se toca) |

El punto 5 es el que importa: es el que hoy duplica artículos, así que un
test que solo verifique "el barcode exacto trae el artículo" pasa en verde
contra el código viejo y no verifica nada.

## Pruebas

Van en `tests/test_venta_seleccion_explicita.py` (el archivo que ya cubre la
regla de "no elegir solo"), extendiendo `tests/test_venta_simple_selector_articulo.py`
para lo del ancho y el precio.

Dos cosas que en este repo ya se Pagaron:

- **Los fixtures tienen que hacer todos los pasos del operador.** Los
  `exec_()` simulados que llaman `accept()` directo quedan colgados con el
  diálogo actual, que exige una fila marcada. El fixture tiene que marcar y
  después aceptar, como una persona.
- **Contra el código viejo tiene que fallar con el síntoma, no con un error.**
  Un test que muere en `AttributeError` por un método que todavía no existe
  no está verificando el pedido 3: está avisando que se escribió el test mal.
  El fallo esperado del punto 5 es el `assert` sobre la pregunta de "Crear
  producto", o el `assert` sobre las filas del selector.

`tests/test_venta_simple_selector.py` y `test_venta_seleccion_explicita.py`
comparten widgets Qt: si la suite completa muere en el teardown con
`0xC0000409` y no imprime el resumen, correr **archivo por archivo** para no
perder el nombre de las fallas.

## Qué se implementó

Los tres puntos están hechos. Se eligió **opción B** (`QTableWidget` con
columnas) para el precio, y el ancho se mide en vez de inventarse.

### Archivos tocados

| Archivo | Qué |
|---|---|
| `vistas/VentaSimple.py` | La lista pasó de `QListWidget` a `QTableWidget` con 4 columnas; ancho medido; precio formateado |
| `controladores/VentaSimple.py` | `_coincidencias_articulo` matchea barcode; `buscar_articulo` delega en ella |
| `tests/test_venta_busqueda_codigo_barra.py` | Nuevo, 11 tests, con base real en memoria |
| `tests/test_venta_selector_precio.py` | Nuevo, 14 tests, con base real en memoria |
| `tests/test_venta_seleccion_explicita.py` | 3 ajustes: `count()` → `rowCount()`, `setCurrentRow` → `setCurrentCell` |

### Lo que encontró la implementación

#### Agregar una `QTableWidget` movió el diálogo de tamaño solo

`Formulario._piso_de_tamano()` decide el piso mirando si la ventana tiene una
`QTableWidget` adentro:

| Clase | Piso |
|---|---|
| `ANCHO_MINIMO_CHICO` (sin grilla) | 620 × 420 |
| `ANCHO_MINIMO` (con grilla) | **900 × 560** |

Al meter la grilla, este diálogo pasó de la primera clase a la segunda sin que
nadie lo pidiera. O sea que **una parte del "más ancho" ya venía hecha**, y por
eso el `resize(720, 460)` del principio no es el tamaño final: queda en
900 × 560 en el primer `show`.

No está mal — 900 es lo que el operador pidió — pero conviene saber que el
número final lo decide `Formulario.ajusta_tamano()`, no el diálogo. Y por eso
el tope de pantalla **no** se puso en el diálogo: `ajusta_tamano` ya aplica el
92 % de la pantalla, y dos topes peleándose se quedan siempre con el menor.

Medido en la pantalla real (1920 × 1152) con el catálogo del reporte:

```
ancho medido por el código        899
ancho real de la ventana          900 x 560
columnas                          [65, 618, 91, 124]
el nombre del reporte mide        594 px
el nombre entra entero            True
```

#### "Se mide una vez al abrir" era falso por dos motivos que no eran la medición

El ancho se mide una sola vez, al abrir, para que la ventana no se mueva
mientras se escribe. Los primeros tests de esa idea fallaron, y **ninguno de
los dos motivos era la medición**:

1. **La columna Detalle era `Stretch`.** Qt toma el ancho del contenido como
   *mínimo* del layout, y un layout con mínimo grande empuja la ventana:
   aparecer un nombre más largo agrandaba el diálogo. Ahora es `Fixed` con el
   ancho medido, y el único que decide el ancho es el `resize`.
2. **`lblCuenta` es un `QLabel`, y un `QLabel` toma el ancho de su texto como
   mínimo.** El mensaje `"2 coincidencias. Elegí una con las flechas o el
   mouse."` era más largo que la ventana. Este problema **ya existía** y se ve
   contra el código viejo: el diálogo viejo salía de 838 px y se iba a 940 al
   escribir. Se arregló con `setWordWrap(True)`.

#### Dos tests no contaban nada, y los dos aparecieron verificando al revés

Los dos salieron corriendo la suite nueva contra el código viejo (`git stash`
de los dos archivos de producción):

- `test_los_barcodes_que_arrancan_con_lo_escrito_van_primero` moría con
  `IndexError` en vez de con el `assert`, porque contra el código viejo la
  lista viene vacía. Un `IndexError` dice "no hay elemento 0" y no dice nada
  de códigos de barras. Se agregó un `assert not encontrados` antes de indexar.
- `test_una_coincidencia_de_barcode_no_abre_el_catalogo` **abría los diálogos
  reales** de "crear producto" contra el código viejo, porque no parcheaba
  `confirmar_alta`. Ahora falla con el mensaje del síntoma.

Ninguno de los dos habría detectado nada.

### Verificación en las dos direcciones

`tests/test_venta_busqueda_codigo_barra.py` contra el código viejo:
**5 fallan, 6 pasan.** Los 5 con el síntoma exacto:

```
AssertionError: un fragmento del codigo de barras no encontro nada
AssertionError: un prefijo de barcode compartido tiene que dar mas de una coincidencia, dio 0
AssertionError: 1048 no encontro ningun articulo: el codigo de barras no se busca
AssertionError: un barcode parcial que existe ofrecio crear: ['Producto no encontrado. Desea agregarlo?']
Failed: un barcode existente no debe entrar al camino de DARLO DE ALTA: el mensaje fue 'Producto no encontrado. Desea agregarlo?'
```

Los dos últimos son el daño: un artículo que ya existía ofrecía crearse.

Los 6 que pasan son los que anclan lo que **no** tenía que cambiar: el barcode
completo, la búsqueda por nombre, los acentos, los ceros a la izquierda, y que
un texto que no existe **siga** ofreciendo darlo de alta.

`tests/test_venta_selector_precio.py` contra el código viejo: los tests de
precio mueren con `ImportError` de `COL_PRECIO` y `AttributeError` de
`rowCount`. **Eso no es un síntoma, es la ausencia de la columna**: no se puede
escribir un assert sobre un precio en una grilla que tiene una sola columna de
texto. Son tests de funcionalidad nueva, no de un bug, y se verifican en una
sola dirección. Tres de ellos sí son de las dos:

```
AssertionError: el selector mide 821 px y la pantalla tiene 800     (el viejo se pasaba)
AssertionError: el ancho cambio al escribir 'access': 838 -> 940   (el viejo se movia solo)
AssertionError: editTriggers != NoEditTriggers                     (la lista vieja si es editable)
```

### Suite

Los 13 archivos de `tests/test_venta*.py` pasan, **91 tests**:
13 + 11 + 12 + 14 + 7 + 1 + 4 + 8 + 5 + 4 + 6 + 5 + 1.

La suite **completa** da `915 passed, 2 failed`. Los 2 fallos son de
`tests/test_importar_articulos.py` (el importador de planillas, del trabajo de
`docs/ARTICULOS-INCRE1.md`) y **no tienen nada que ver con este issue**:

```
(176, 'no tiene GANANCIA y no se eligio una por defecto')   x20 de 704 filas
```

Comprobado, no supuesto: con `vistas/VentaSimple.py` y
`controladores/VentaSimple.py` en el stash, los 2 tests siguen fallando igual
(`2 failed, 42 passed`), y el archivo no importa nada de `VentaSimple`. Quedan
abiertos para el trabajo del importador.

### Un detalle que quedó documentado en el código

La búsqueda por barcode se cambió en `_coincidencias_articulo`, **no** en
`buscar_articulo`, y este quedó delegando en aquella. Antes los dos buscaban
por su cuenta y no coincidían entre sí: `_articulo_es_ambiguo` contaba 1
coincidencia y `buscar_articulo` devolvía `None`, que es exactamente el
"Crear producto" del bug.

Delegar es lo que lo cierra. Y es la diferencia entre arreglar el bug y
taparlo: si el arreglo hubiera sido "agregar el barcode a `buscar_articulo`",
los dos caminos seguirían buscando distinto, y el próximo que agregue un
criterio va a tener que acordarse de los dos.

## Fuera de alcance

- **El selector de clientes** (`VentaSimpleSeleccionClienteDialog`) tiene el
  mismo `resize(560, 420)` y va a seguir con el mismo tamaño. Se deja así a
  propósito: el pedido es sobre el catálogo de artículos, y los nombres de
  clientes no llegan a 110 caracteres. Ojo con una cosa: como **no** lleva
  `QTableWidget`, sigue en la clase de piso chico (620 × 420). Si algún día le
  agregan columnas, salta solo a 900 × 560, igual que pasó acá.
- **Índice en `codbarra`** para la búsqueda parcial: con el catálogo que hay no
  se midió que haga falta. Si algún día molesta, se mide antes.
- **Los acentos en la descripción**: este issue **no** lo arregla, pero lo
  destapa. El pendiente de `docs/SELECCION-PRODUCTO.md` decía que
  `buscar_articulo` usaba `contains()` sin normalizar y que por eso las dos
  consultas "podían no coincidir entre sí". Con `buscar_articulo` delegando
  en `_coincidencias_articulo`, ese pendiente se cerró de yapa: los dos
  caminos son ahora el mismo, y ambos normalizan.

## Pendientes

- [x] Ancho del selector con el criterio medido del punto 1.
- [x] Precio al público en columna, con `_formato_importe` y el `None`
      protegido. Opción **B** (`QTableWidget`), como se decidió.
- [x] `_coincidencias_articulo` matchea código de barras, con las que arrancan
      con lo escrito primero.
- [x] Test del barcode **parcial** verificado en las dos direcciones.
- [x] Ancho medido con `QFontMetrics` sobre el texto real de las celdas.
- [ ] **Confirmar a ojo en la pantalla del operador.** Todo lo anterior se
      midió con la plataforma `offscreen` (pantalla de 800 × 600) y con una
      sonda con Qt real (1920 × 1152, ventana de 900 × 560, nombre del
      reporte entrando entero en 618 px). Falta que una persona lo abra y
      confirme que se lee bien con su catálogo.
- [ ] **En pantallas chicas el Detalle puede quedar más ancho que la ventana.**
      Con un nombre de 110 caracteres la columna pide ~600 px y el tope del 92 %
      de una pantalla de 1366 da 1256: entra. En una de 1024, el tope es 942 y
      la columna se pasa, aparece scroll horizontal. No es grave (el nombre se
      lee igual, scrolleando) pero no está resuelto.
- [ ] **El precio se muestra, el IVA no.** La fila dice cuánto sale pero no qué
      porcentaje de IVA tiene. Para comparar productos alcanza; para una venta
      con alícuotas mezcladas, el operador tiene que acordarse del producto.
- [ ] **Los 20 fallos del importador** (punto anterior), que son del trabajo de
      `docs/ARTICULOS-INCRE1.md` y no de acá.