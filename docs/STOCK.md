# Stock

Cómo funciona el stock en PyFE, por qué está armado así, y qué falta.

La versión corta: **el stock no es un número guardado en el producto. Es la
suma de una tabla de movimientos.** Si buscás una columna de stock en
`articulos`, no está, y no es un olvido.

---

## Por qué una tabla de movimientos y no un número

Un número guardado (`articulos.stock`) se actualiza en cada venta, cada
remito, cada compra y cada ajuste. El día que una de esas actualizaciones
falla — un error a mitad, una PC que se apaga, alguien que anula a mano — el
número queda desfasado y no hay forma de saber cuál de los dos miente: ¿el
número está mal o los movimientos?

Con suma no hay nada que mantener. El stock **es** lo que dice la tabla, y
`libs/stock.py::stock_de()` lo calcula. Se puede volver a correr y da lo
mismo.

La tabla se llama `movstock` y está en `modelos/MovStock.py`. Sus reglas:

1. **Un movimiento no se edita ni se borra, nunca.** Para corregirlo se escribe
   el movimiento contrario y se lo enlaza con `anula`. Así el histórico cuenta
   qué pasó y no sólo cómo quedó. Lo único que se le escribe a un movimiento
   ya creado es ese vínculo de anulación.
2. **La cantidad va con signo**: positiva entra, negativa sale. El campo
   `tipo` dice cómo, pero el signo es el que suma.
3. **`origen` dice qué flujo lo produjo** (`VENTA`, `REMITO`, `COMPRA`,
   `INICIAL`, `AJUSTE`). Sin origen, un faltante no se puede explicar.

### Por qué no se deriva de `detfact`

Porque `detfact` no es la historia del stock. `ImportacionAFIP.py` escribe un
renglón falso por cada comprobante importado, siempre con `idarticulo=1` (el
artículo "Servicios") y `cantidad=1`, para que los libros de IVA cuadren. Si
el stock fuera un `SUM` sobre `detfact`, cada factura de un comprobante
emitido en otro sistema bajaría una unidad de un artículo que no existe.

Además: una venta de 2018 no es un movimiento de stock de hoy. Son ocho años
de historia que ya pasó. **El stock arranca en cero.**

---

## De dónde sale cada movimiento

| Flujo | Qué descuenta | Dónde |
|---|---|---|
| Venta rápida | `VENTA` | `Facturas.GrabaFE` |
| Emisión de factura | `VENTA` | `Facturas.GrabaFE` |
| Factura abierta desde un remito | **nada** (el remito ya descontó) | `Facturas.GrabaFE` |
| Nota de crédito | `VENTA` con cantidad **positiva** | `Facturas.GrabaFE` |
| Remito | `REMITO` | `Remitos._guarda` |
| Factura de proveedor | `COMPRA` | `CargaFacturasProveedor._guarda_factura_proveedor` |
| Ajuste manual | `AJUSTE` | `Stock → Ajustes de stock` |

### La regla del remito

El remito descuenta cuando la mercadería sale. La factura llega después, y si
también descontara, **cada venta con remito bajaría el stock dos veces**.

Por eso `cabfact` tiene `idremito` (agregado en la migración 9): si está
puesto, la factura no vuelve a descontar. El botón **"Facturar"** de la
pantalla de remitos guarda el remito y abre la factura con la mercadería
cargada y el vínculo puesto, así que nadie tiene que desvincularlo a mano.

La regla vive en `libs/stock.py::aplica_factuna`, no en los controladores. Si
estuviera en cada pantalla que emite, cada una tendría que acordarse, y la que
se olvide descuenta dos veces sin que nada falle.

Nota: una **nota de crédito** con remito sí repone. Si la mercadería volvió,
entra de nuevo.

### Modificar un remito

Los renglones del remito se borran y se vuelven a escribir. Antes de eso,
`libs/stock.py::revierte_de_comprobante` devuelve lo que se había descontado,
escribiendo los movimientos contrarios. Si no, cada edición dejaría el stock
más bajo que la anterior, sin que ninguna pantalla avise.

---

## Qué se controla y qué no

No todos los productos se controlan. El campo es `articulos.controlastock`,
explícito y en `False` por defecto.

Podría haberse deducido de `concepto` (1 = producto, 2 = servicio), pero en un
mismo catálogo hay productos que no se inventan y servicios que sí. Una regla
que adivine va a fallar en algún caso y nadie va a saber cuál.

**Para empezar:** `Stock → Marcar productos` marca de una vez **todos los
productos** que estén en `False`. Marcar de a uno obliga a entrar veinte veces
al ABM de Productos, y el que se saltea uno se da cuenta semanas después,
cuando el stock de ese producto no baja nunca.

**Ese botón marca solo productos, no servicios.** No es que `controlastock` se
deduzca de `concepto` —sigue siendo explícito, y arriba está por qué—, sino que
un botón de masse no puede tener al lado un "dar de baja". Ver "El bug del
botón de arranque" más abajo.

Al terminar dice cuántos servicios quedaron sin tocar, para que el operador no
crea que se marcó todo el catálogo.

---

## La primera vez: inventario inicial

El stock arranca en **cero**, y hay que cargarlo.

`Stock → Ajustes de stock` → elegí el producto (F2 abre el buscador) → poné
la cantidad → **escribí por qué**. La observación es obligatoria: un movimiento
que dice "ajuste" y nada más no dice si fue un conteo, una rotura o una carga
mal hecha, y el siguiente que vea el faltante no tiene por dónde empezar.

Los movimientos de inventario inicial usan `origen = 'INICIAL'`, que los
distingue de un ajuste de a diario.

---

## Las pantallas

| Pantalla | Para qué |
|---|---|
| **Stock** | Cuánto hay de cada cosa, qué está faltando, y exportar |
| **Ajustes de stock** | Conteo y correcciones (no es un ABM: un movimiento no se edita) |
| **Movimientos de stock** | De dónde sale cada número, con el número de comprobante |
| **Productos** | `Controla stock?` y `Stock minimo` |

Los ajustes **no** son un ABM a propósito. `vistas/ABM.py` edita y borra
registros; acá el operador tendría un botón de borrar que no se puede dejar
habilitado, y la primera vez que lo aprieta se pierde el historial de por qué
el stock quedó así.

---

## Vender sin stock

**Avisa y deja vender igual.** Bloquear una venta por un dato de stock que
puede estar mal es peor que el faltante: en un comercio real, quedarse sin
poder cobrar cuesta más plata que equivocarse de inventario.

El aviso (en `Venta rápida`, antes de emitir) acumula por producto: si quedan
5 y la venta lleva 3 y 3 del mismo artículo, dice "se venden 6", no "se venden
3". El botón dice **"Emitir igual"**, no "Aceptar", para que quede claro que la
app no está decidiendo.

---

## Las transacciones

`Facturas.GrabaFE` y `CargaFacturasProveedor._guarda_factura_proveedor`
escriben cabecera, renglones y movimientos de stock dentro de un
`db.atomic()`. Antes cada `save()` era su propia transacción, y un renglón que
fallaba dejaba la cabecera guardada con la mitad de los ítems.

`ImprimeFactura` queda **afuera** de la transacción a propósito: una factura
autorizada ante ARCA existe más allá de esta app, y revertirla porque el PDF
no salió sería peor que un PDF que hay que reimprimir.

Es el primer `db.atomic()` del proyecto. Si agregás una escritura nueva a
`GrabaFE`, va adentro.

---

## La migración

`VERSION_DB` pasó de 8 a 9. `MigrarVersion9` crea `movstock` y agrega cuatro
columnas: `articulos.controlastock`, `articulos.stockminimo`,
`cabfact.idremito` y `pdetalle.idarticulo`.

Es idempotente: en una base recién creada no queda ninguna migración
pendiente, porque `MigrarVersion0` ya arma el schema final con los modelos
actualizados.

**El sello `VERSION_DB` está hardcodeado en tres lugares**, y si cambiás la
versión hay que tocar los tres:

- `controladores/MigracionBaseDatos.py:109`
- `tests/test_migraciones.py` (dos asserts)

---

## Compras

`pdetalle` ahora tiene `idarticulo`, y la grilla de carga de comprobantes
tiene columnas `Producto` y `Nombre Producto` (F2 abre el buscador).

El producto es **opcional**, y es a propósito: una factura de proveedor tiene
gastos, impuestos y servicios que no entran al inventario. Si fuera
obligatorio, habría que inventar un producto "varios" para poder guardar el
renglón, y ese producto terminaría con stock real.

La columna va **última** a propósito: el resto de la grilla usa índices fijos
(el F2 del centro de costos es la columna 0, el salto de fila con Enter corta
en la última) y meterla en el medio los correría en silencio. El índice es
`GrillaFactProv.COL_PRODUCTO`.

---

## La base de trabajo se migró, y cómo volver atrás

Al agregar la versión 9, `sistema.db` de la raíz pasó a estar en versión 9 con
la tabla `movstock` creada. **Los datos están intactos**: las mismas 283
facturas, los mismos 2068 renglones, los mismos 3 artículos y 57 clientes, y
cero movimientos de stock.

La causa no fue el arranque de la app, sino la suite de tests:
`tests/test_componentes.py` instanciaba `Main()`, y `Main.__init__` corre
`CreaTablas()` y `Migraciones()`. Ese test ya modificaba la base antes de que
existiera la versión 9; no se notaba porque la base ya estaba al día y las
migraciones no tenían nada que hacer. En cuanto la 9 sí tenía trabajo, cada
corrida de los tests migraba la base de desarrollo.

**Arreglado**: ese test ahora anula `CreaTablas` y `Migraciones`, porque sólo
mira el mapa de destinos del menú y no necesita la base. Correr los tests ya
no modifica `sistema.db`.

### Volver atrás

`sistema.db.bak` es una copia de la base tal como estaba antes de la
migración (versión 8, sin `movstock`). Para volver:

```
ren sistema.db.bak sistema.db
```

También sirve `tools/migrar_base.py`, que migra la base de trabajo sin
levantar Qt y hace el `.bak` antes de tocar nada.

### Si la base queda en una versión vieja

Si `sistema.db` está en versión 8 y se corren los tests, fallan siete tests de
`test_venta_simple_*` con `no such column: t1.controlastock`. No es un bug del
stock: son tests que leen la base de trabajo y asumen que el modelo y la base
coinciden. Se arregla corriendo `tools/migrar_base.py`.

---

```
modelos/MovStock.py         el modelo y sus reglas
libs/stock.py               toda la lógica: registrar, sumar, anular, falantes
controladores/Stock.py      las tres pantallas
vistas/Stock.py             las tres ventanas
controladores/MigracionBaseDatos.py   MigrarVersion9
```

**La lógica está en `libs/stock.py` y no en los controladores a propósito:**
es la única parte que se puede probar sin QApplication, sin ARCA y sin una
factura emitida. Los tests de `tests/test_stock.py` son los que dicen si el
stock está bien; los de las pantallas sólo dicen si la pantalla no se rompe.

---

## Cómo probarlo a mano, paso a paso

Los tests cubren la lógica y las ventanas se abren, pero el camino completo
—vender, remitir, facturar, comprar— sólo se comprueba con las manos. Esta es
la vuelta que ejercita todo, y qué tiene que verse en cada paso.

La primera vez, en homologación: **no pruebes esto con una factura de verdad
contra ARCA.** Usá un cliente de prueba.

**1. Abrí `Stock`.** Tiene que aparecer el cartel "Ningún producto controla
stock todavía". Si aparece una grilla vacía sin cartel, algo se rompió.

**2. `Marcar productos`.** Tiene que preguntar cuántos son. Aceptar.

**3. `Stock` de nuevo.** Ahora listan los productos, todos en `Sin stock`.

**4. Doble click en uno → se abre "Ajustar stock".** Poné la cantidad real
(`10`), escribí un motivo (`conteo inicial`) y `Grabar`. Fijate que **sin
motivo no te deja**: es a propósito.

**5. `Stock`.** El producto tiene que estar en `10` y en `OK`.

**6. Venta rápida.** Agregá el producto con cantidad `15` y emití. Tiene que
aparecer el aviso de que se queda en `-5`, con el botón **"Emitir igual"**.
Emití igual.

**7. `Stock`.** El producto está en `-5`, estado `Negativo`.

**8. `Movimientos de stock`.** Tres movimientos: el inicial de `+10`, la venta
de `-15`, y el número de factura en la columna Comprobante. Si el comprobante
está vacío, el stock bajó sin dejar rastro.

**9. Remitos.** Cargá un remito con `3` del mismo producto y guardá.

**10. `Stock`.** Bajó a `-8`. El remito descontó.

**11. Volvé al remito y apretá `Facturar`.** Se abre la factura con la
mercadería cargada. Emitila.

**12. `Stock`.** Sigue en `-8`. **Si bajó a `-11`, la mercadería salió dos
veces**, que es el error más caro de esta feature.

**13. Compras → Cargar comprobantes.** Cargá una factura de proveedor con la
columna `Producto` elegir ese producto y cantidad `20`. `Stock` tiene que
mostrar `12`.

**14. Editá el remito del paso 9** y cambiale la cantidad a `5`. `Stock` tiene
que mostrar `14`, no `12`: lo que se había descontado se devuelve antes de
rehacer los renglones. Si te da `10`, cada edición te está comiendo stock.

**15. `Stock → Exportar`.** Abre un Excel con los totales. Si no abre nada,
mirá la carpeta `excel/` del proyecto.

Los pasos 9 a 12 son los que importan. Los demás andan solos.

### El F2 y la ventana de búsqueda

En **Ajustes de stock** y en **Movimientos de stock**, apretar `F2` con el
campo de producto enfocado abre el buscador. Ese camino lo encontró un
`TypeError` la primera vez que se lo apretó, después de que 660 tests pasaba:
la ventana de búsqueda es **modal**, así que ningún test la abre, y el error
salía recién con el operador debajo.

Ahora hay un test que la cubre (`tests/test_stock_ui.py`): reemplaza **sólo la
ventana** por una que devuelve al toque, y deja el callback y el controlador
como son. Si un callback cambia de firma, el test lo ve.

Eso no alcanza para todo: el **botón Facturar del remito** abre la pantalla de
emisión con `exec_()`, que también es modal y bloquea. Ese camino no lo cubre
ningún test y hay que probarlo a mano (es el paso 11).

---

## Cómo se prueba en MySQL

SQLite y MySQL difieren justo donde el stock se rompe:

- `MigrarVersion9` agrega claves foráneas con `_clave_foranea`, que en sqlite
  es un no-op comentado y en MySQL hace un `ALTER TABLE` de verdad.
- `BitBooleanField` es `BIT(1)`: en MySQL vuelve `b'\x01'`, en sqlite un entero.
- `SUM` de un `DECIMAL` devuelve float en sqlite y `DECIMAL` exacto en MySQL.
- MySQL no deja crear una tabla que apunte a otra que todavía no existe.

Probado contra **MySQL 8.4.11** con los 14 chequeos de
`tools/probar_stock_mysql.py`: la migración, las cinco claves foráneas de
`movstock`, el bit, la suma con decimales, el remito que no descuenta dos
veces, la anulación, la reversa de un remito, la reversa de una transacción y
la idempotencia.

```
sudo mysql < /mnt/c/Programacion/PyFE/tools/_setup_mysql.sql
python tools/probar_stock_mysql.py
```

### Los dos bugs que sólo aparecen en MySQL

Los dos estaban escondidos porque en sqlite las claves foráneas no se aplican
al crear la tabla, y en sqlite la migración nunca falla.

**1. `_clave_foranea` agregaba claves que ya existían.** En una base MySQL
nueva, `MigrarVersion0` crea cada tabla desde el modelo y sus claves foráneas
salen ahí; después `MigrarVersion1` intentaba volver a ponerlas. MySQL
devolvía `Duplicate foreign key constraint name`, la versión no se sellaba y
el schema quedaba a medias. Ahora `_clave_foranea` consulta primero
`db.get_foreign_keys()`.

**2. `Cabfact.idremito` apuntaba a una tabla que todavía no existía.** La
columna es de la migración 9, y MySQL no crea `cabfact` si su clave foránea
manda a `remito`, que se crea en la versión 7. `MigrarVersion0` ahora incluye
`Remito` y `DetalleRemito` en su lista.

Sin el segundo, una instalación MySQL desde cero creaba nueve tablas de
veintitrés y la app no arrancaba.

## Cómo se miran las ventanas sin hacerlas a mano

`tools/capturar_stock.py` abre las tres pantallas con la plataforma de Qt de
verdad y guarda un PNG de cada una en `_capturas/`. Con `offscreen` los textos
**no** se dibujan: los widgets se pintan y las letras no, así que una captura
sin texto no dice nada de la pantalla y parece que la ventana está rota.

`tools/abrir_todas_las_pantallas.py` recorre el menú completo, abre cada
pantalla y dice cuál se cae. Es lo que sirve cuando el operador reporta un
error de una pantalla que no es de stock: el bug casi nunca está donde se mira
primero.

## Las pantallas: cómo se mide que no estén apretadas

`tools/medir_ventanas.py` recorre las 40 pantallas del menú y dice cuáles
están chicas, cuáles se recortan y qué columnas quedaron en 56 px. Antes de
tocar una pantalla a ojo, se mide: un número dice "le faltan 272 px", una
impresión solo dice "se ve raro".

Para que el número sea creíble, mide contra `minimumSizeHint` y **no**
contra `sizeHint`. El mínimo es lo que el layout necesita para no cortar
nada; el `sizeHint` se infla con cualquier contenedor sin layout (una pestaña
vacía pide 640×480 de default y empuja la ventana a 2678 px). Y mide con la
plataforma de Qt de verdad: con `offscreen` la pantalla reporta 800×600 y
todas las ventanas parecen más grandes que la pantalla.

La primera medición dio **26 pantallas con problemas**. Dio 0 después de
cinco cosas, todas en `libs/Grillas.py` y `libs/Formulario.py`:

1. **`Formulario.resizeEvent` llamaba a `Center()` en cada redimensionado.**
   La ventana se iba para otro lado mientras el operador la agranda con el
   borde, que es como falla el gesto entero. También hacía un `print` en cada
   movimiento del mouse (los `Alto X Ancho Y` de la consola). El centrado
   vive en `Center()`, que lo llama `exec_()`.

2. **No había tamaño mínimo.** `Formulario` tiene ahora un piso de 900×560
   para las ventanas con grilla y 620×420 para los diálogos sin ella, aplicado
   en `showEvent`, que es el primer momento en que el layout está armado.
   Antes cada pantalla escribía su `resize()` a mano y ninguna coincidía con
   lo que el contenido pedía.

   Ese piso después se comió a los diálogos chicos: ver "El piso de tamaño
   se comía a los diálogos", más abajo.

3. **`_reparte_anchos` le daba la diferencia completa a la última columna.**
   `anchos[-1] += total - sum(anchos)` solo funciona si la diferencia es
   positiva. Con nueve columnas en una grilla angosta la suma de los pisos
   supera el ancho, la diferencia sale negativa y la última se come −500 px.

4. **El peso de cada columna era la longitud de su encabezado.** Eso hacía
   que `Idcliente` (9 letras) pesara más que `Nombre` (6) y se llevara 555 de
   959 px. Ahora las columnas que no son texto tienen ancho fijo según su
   tipo (id 110, fecha 90, importe 110) y el sobrante se lo reparten solo las
   de texto. Un identificador son cuatro dígitos, mida lo que mida su nombre.

5. **`ArmaCabeceras` repartía los anchos ANTES de aplicar los formatos.**
   El reparto decide el ancho según el tipo de columna, así que sin el tipo
   todavía, todas se repartían como texto. Y `AgregaItem` pisaba los formatos
   declarados con `'String'` al cargar la fila de arranque vacía, que
   devolvía a `Neto` e `IVA` al ancho de un texto corto.

Además, las columnas que arrancan con `_` (la convención del proyecto para
las que solo guardan un id) ahora se esconden: antes se repartían el ancho
como si fueran datos y quedaban a la vista como una franja de números.

`tests/test_pantallas_del_menu.py` abre las 40 pantallas del menú y dice
cuál se cae.

---

Tres, en este orden. Los dos primeros los encontró el operador con las
ventanas abiertas; el tercero, con el F2.

**`Grillas._reparte_anchos` reventaba con la grilla vacía.** `ABM.py` deja
`cabeceras = []` cuando el modelo no tiene `camposAMostrar`, y
`anchos[-1] += ...` sobre una lista vacía es un `IndexError`. Ahora no
reparte si no hay columnas.

**`ControladorBaseABM` construía una ventana inútil.** Su `__init__` hacía
`self.view = ABM()` —la vista base, sin modelo ni columnas— y cada subclase la
reemplazaba después con la suya. Se construían **dos ventanas por apertura** y
la primera, al repartirse los anchos, tiraba el `IndexError` de arriba. La
pantalla andaba igual: se veía el traceback y nada más. Ahora la clase de la
vista se declara con `vistaClase` y se construye una sola.

**El F2 tiraba `TypeError`.** Está en la sección de la prueba manual.

### Por qué los tests no los ven

Los tres se les pasaron a los tests: una grilla vacía no se abre en ninguno, un
`__init__` que arma algo y lo descarta no deja rastro, y una ventana modal no
se abre desde un test sin bloquearlo.

`tests/test_pantallas_del_menu.py` recorre ahora las 40 pantallas del menú y
dice cuál se cae al abrirla. Para no quedar viejo, el mapeo de clave a
controlador lo saca de `controladores/Main.py` con `ast`, en vez de tener una
lista escrita a mano.

---

## Bugs que aparecieron usando la app, no los tests

Cuatro, en este orden. Los tres primeros los encontró el operador con las
ventanas abiertas; el último, con el F2.

**`Grillas._reparte_anchos` reventaba con la grilla vacía.** `ABM.py` deja
`cabeceras = []` cuando el modelo no tiene `camposAMostrar`, y
`anchos[-1] += ...` sobre una lista vacía es un `IndexError`.

**`ControladorBaseABM` construía una ventana inútil.** Su `__init__` hacía
`self.view = ABM()` —la vista base, sin modelo ni columnas— y cada subclase la
reemplazaba después con la suya. Se construían **dos ventanas por apertura** y
la primera, al repartirse los anchos, tiraba el `IndexError` de arriba. La
pantalla andaba igual: se veía el traceback y nada más. Ahora la clase de la
vista se declara con `vistaClase` y se construye una sola.

**El F2 tiraba `TypeError`.** Está en la sección de la prueba manual.

### Por qué los tests no los ven

Se les pasaron a los tests: una grilla vacía no la abre ninguno, un `__init__`
que arma algo y lo descarta no deja rastro, y una ventana modal no se abre
desde un test sin bloquearlo.

`tests/test_pantallas_del_menu.py` recorre ahora las 40 pantallas del menú y
dice cuál se cae al abrirla. Para no quedar viejo, el mapeo de clave a
controlador lo saca de `controladores/Main.py` con `ast`, en vez de tener una
lista escrita a mano.

---

## Pendientes

- **Un solo depósito.** No hay modelo de depósito; el stock es global. Si
  hacen falta dos locales, es otra decisión y otra tabla.
- **Conteos cíclicos.** Hoy el inventario inicial se carga una vez. No hay
 ni diferencia ni diferencia entre lo contado y lo esperado.
- **Costo promedio ponderado.** El costo está congelado en el renglón
  (`detfact.costo` y `articulos.costo`) y no hay valuación de inventario.
- **Histórico anterior al arranque.** Las 283 facturas que ya estaban en la
  base no generaron movimientos. Es intencional (ver arriba), pero si algún
  cliente quiere que el stock refleje ese histórico, hay que decidir cómo.
---

## El bug del boton de arranque

`Stock -> Marcar productos` llamaba `marcar_como_controlados()` sin argumentos,
y eso ponia `controlastock = True` en **todo** lo que estuviera en `False`. En
un catalogo de comercio general, que es para lo que esta armado el modulo,
casi todos los servicios estan en `False`.

Consecuencias, todas silenciosas:

1. Cada venta de un servicio escribia un movimiento de stock y lo dejaba en
   negativo para siempre.
2. El reporte de faltantes se llenaba de mercaderia que no existe.
3. El filtro "Sin controlar" desaparecia para siempre: no quedaba nada en
   `False`.

El test lo certificaba en vez de detectarlo.
`test_marcar_como_controlados_pasa_todo_lo_que_falta` afirmaba
`controla(Articulo.get_by_id(2)) is True`, y el articulo 2 es MANTENIMIENTO, un
servicio. El test pasaba porque el codigo hacia lo que el test pedia, y los dos
estaban equivocados juntos.

Ahora `marcar_como_controlados()` marca solo `concepto == '1'`, y
`sin_controlar()` acepta `incluir_servicios=False` y `solo_servicios=True` para
que la pantalla pueda decir "marcaste 12, quedaron 3 servicios sin tocar".

**El que si se controla se marca a mano, en Productos.** Un servicio que se
quiera inventar es un caso raro y deliberado. Lo que no puede ser es que un
boton de masse lo haga sin que nadie lo haya pedido, y que `controlastock`
deje de ser explicito para eso.

El UPDATE primero pregunta la lista y recien despues escribe. Un filtro directo
contaria como "modificados" las filas que ya estaban en `True` en MySQL, que
devuelve las rows matched y no las changed, y el controller usa ese numero
para decir "marque N".

---

## El stock se ve mientras se vende

La grilla de Venta rapida tiene una columna **Stock** entre Detalle y Unitario,
y el renglon se pinta de rojo cuando la venta se lleva mas de lo que hay.

El motivo: antes el operador se enteraba del faltante **al final**. Con la
venta entera escrita, Emitir abria "se venden 6 y hay 5". Para entonces el
trabajo de tipeo estaba hecho, y en un mostrador con cola el tiempo que se
tardo es tiempo en el que el cliente espera.

El aviso previo a emitir **no se quita**: avisa del total de toda la venta, que
una columna fila por fila no puede saber. Pasa a ser la segunda vez que se ve,
no la primera.

**La columna acumula por producto y no renglon por renglon**, por el mismo
motivo que el aviso: con 5 en stock y dos renglones de 3 del mismo producto,
mirando fila por fila los dos "entran" cuando juntos se llevan 6.

Que la columna y el aviso digan lo mismo no es casualidad: si la grilla dice
"estas bien" y el aviso dice "no alcanza", el operador deja de mirar el aviso
por desconfianza, y el aviso era la unica red.

Un servicio muestra un guion y ningun color. Poner `0` seria mentir, porque
dice que no hay cuando en realidad no hay nada que contar, y pintarlo de rojo
seria gritarle al operador por algo que esta bien.

El color sale de `temas/pyfe.css`: el rojo de peligro `#C62F35` sobre el fondo
de error `#FDF3F2`. No son colores inventados para esta pantalla, son los que
la app ya usa para decir "esto esta mal".

El estado del color tiene TRES valores y no dos: alcanza, no alcanza, y "el
stock no aplica". Con un solo booleano el servicio caia en el caso de "no
alcanza" y salia en rojo. Un color de mas es un color que ya no significa
nada.

---

## Editar un renglon: tres cosas que estaban rotas

Al conectar la edicion de celda aparecen tres problemas que no se veian porque
no habia handler. En orden de gravedad.

### 1. La factura llevaba la cantidad vieja

**Este es el que cuesta plata.** `AgregaItem` guarda el numero en `UserRole` y
`ObtenerItem` lo devuelve crudo, pero **editar una celda solo cambia el texto**.
Verificado:

```
>>> g.AgregaItem(items=["2", "GASOLINA", "100"])
texto visible   : '2'
ObtenerItem     : Decimal('2')
>>> g.item(0, 0).setText("4")
texto visible   : '4'
ObtenerItem     : Decimal('2')      <-- el viejo
```

Como `obtener_renglones` arma la factura con `ObtenerItem`, la pantalla
mostraba 4 y el comprobante decia 2.

Se arregla con `_normaliza_celda`, que es el mismo patron que ya usa
`Facturas._normaliza_celda` en la grilla de emision: `setData` sobre la misma
celda para devolverle el numero crudo. Con `setData` y no `ModificaItem`,
porque reemplazar una celda que se esta editando hace que Qt la dibuje
avanzando a la fila siguiente mientras se tipea.

El parser es `libs/Grillas._a_numero_texto`, que distingue "1.234,56" de
"1,234". El de `Facturas._a_numero` solo quita puntos, y con eso "1.234,56"
da 1.23456 sin avisar.

### 2. El SubTotal y el total no se recalculaban

La cantidad se podia cambiar a mano y el subtotal se quedaba con el valor
anterior: cantidad 2 y subtotal de 6 en la misma fila.

### 3. Dos senales parecidas que no son la misma

`QTableWidget` tiene `itemChanged(QTableWidgetItem*)` y
`cellChanged(int, int)`. Se conecto la primera por costumbre, y el handler
recibio un item donde esperaba un int.

Lo que hace de esto un hallazgo y no una trivia: **una excepcion dentro de un
slot que Qt llama desde C++ deja el proceso en un estado del que no vuelve**, y
el test muere con `0xC0000409` sin backtrace. El sintoma, un crash sin salida,
no apunta al error, que era un TypeError de tipos. Recien con una reproduccion
 minima que imprime un paso por vez se ven las dos cosas: el TypeError en el
handler y, despues, el silencio.

La reentrada tambien estaba: `AgregaItem` dispara `cellChanged` una vez por
celda, y el handler escribe en la grilla, que lo dispara otra vez. Sin el
candado de `_escribiendo` eso es recursion hasta que la pila se queda sin
memoria. Va como contextmanager y no como dos lineas porque un `return` en el
medio sin limpiar el flag deja la grilla muda para el resto de la vida de la
ventana.

---

## Los tests de esto

`tests/test_stock_en_venta.py` son 11 tests de lo que se ve en la pantalla: que
la columna exista, que no sea editable, que pinte lo que no alcanza, que los
dos renglones del mismo producto sumen, y que editar recalcule el color, el
subtotal y la cantidad que se factura.

El camino real de agregar un renglon se ejercita por
`_agregar_este_articulo`, que es donde convergen el selector de catalogo y el
nombre escrito. Lo unico que se reemplaza es el dialogo de cantidad y precio,
que es modal y bloquearia: el resto del camino es el de verdad.

Un detalle que casi sale mal: el test leia el SubTotal con
`float(texto.replace(".", "").replace(",", "."))`, y la celda muestra
"4.000,00". Ese parser da 4000, o sea que el test estaba midiendo su propia
conversion y no el subtotal. Ahora usa `_a_numero_texto`, que es el que sabe.

Agregar la columna tambien rompio un test que leia el Unitario por indice
fijo, porque las columnas de la derecha se corrieron. Ese test ahora resuelve
el indice por encabezado, que es lo que hace el resto del archivo y lo que lo
hace inmune a la proxima columna que se agregue.

---

## Lo que sigue pendiente

Esto es lo que se decidio **no** hacer todavia, y por que:

- **Un solo deposito.** No hay modelo de deposito; el stock es global. Si
  hacen falta dos locales, es otra decision y otra tabla.
- **Conteos ciclicos.** Hoy el inventario inicial se carga una vez. No hay
  diferencia entre lo contado y lo esperado.
- **Costo promedio ponderado.** El costo esta congelado en el renglon
  (`detfact.costo` y `articulos.costo`) y no hay valuacion de inventario.
- **Historico anterior al arranque.** Las 283 facturas que ya estaban en la
  base no generaron movimientos. Es intencional (ver arriba), pero si algun
  cliente quiere que el stock refleje ese historico, hay que decidir como.
- **Carga masiva del inventario inicial.** Hoy son 300 productos = 300
  dialogos, cada uno con su motivo obligatorio. Hay exportacion a Excel pero no
  importacion. Es la mayor friccion del arranque.
- **Lista de reposicion.** `libs/stock.faltantes()` ya calcula que falta, con
  el faltante y ordenado de mas a menos, y **ninguna pantalla la usa**. Esta
  escrito y testeado, y lo que falta es una pantalla que la llame.
- **Editar `stockminimo` desde la grilla de Stock.** Hoy hay que entrar al ABM
  de Productos de a uno.

`faltantes()` es el pendiente mas barato de todos: la logica esta, los tests
estan, y lo unico que falta es un boton.
---

## El piso de tamaño se comía a los diálogos

Ocurrió porque el piso que arregló las 40 pantallas del menú se aplicaba
**también a los diálogos chicos**, y una cosa y la otra no son lo mismo.

Medido, antes del arreglo:

| Diálogo | Pide | Recibía | Título de alto |
|---|---|---|---|
| Cantidad y precio | 420x160 | 620x420 | **307 px** |
| Agregar cliente | 520x220 | 620x420 | 276 px |
| Agregar artículo | 520x220 | 620x420 | 245 px |
| Ajustar stock | 560x320 | 620x420 | - |
| Informe recategorización | 650x150 | 650x420 | - |
| RG 3685 | 650x100 | 650x420 | - |
| Ficha de cliente | 500x350 | 620x420 | - |

Eran diez en total. Todos declaraban un tamaño y recibían otro, y eso no se ve
leyendo el código: se abre el diálogo y se mide.

### Los 307 px del título

`EtiquetaTitulo` es un `QLabel`, y la política vertical por omisión de un
`QLabel` es **Expanding**. Adentro de un `QVBoxLayout` eso significa que se
come todo el sobrante vertical. Medido: en "Cantidad y precio" ocupaba
`(11, 11, 598, 307)` para unos 20 px de texto de una línea.

Es exactamente lo que se ve en la captura: "PRODUCTOS" flotando en el medio de
la ventana y los dos campos abajo de todo. Un título es una línea, y ahora
tiene `QSizePolicy.Fixed` vertical.

El `addStretch(1)` antes de la botonera va aparte del `QSizePolicy`: sin él, el
título deja de crecer pero el sobrante se va al fondo y la botonera queda
pegada al tope. Son las dos caras del mismo problema.

### El piso, sin tocar las 40 pantallas

`Formulario.declara_tamano(ancho, alto)` deja que un diálogo diga su tamaño
**una sola vez** y use ese mismo número como piso. Antes había que escribirlo
dos veces —el `resize()` en la vista y el piso en la clase—, y por eso se
desincronizan.

Solo afecta al piso de los diálogos **sin grilla**. Con grilla manda
`ANCHO_MINIMO`/`ALTO_MINIMO` (900x560), que es el que salvó a las pantallas
grandes y no se toca.

El contenido sigue mandando por encima del piso, porque `minimumSizeHint` se
aplica igual: declarar un tamaño chico nunca termina con algo cortado. "Agregar
artículo" pide 220 de alto y abre de 238, y "RG 3685" pide 100 y abre de 145,
porque el contenido necesita más. Eso es el piso haciendo su trabajo.

### Lo que NO se tocó

El piso de 620 px de ancho que usa `tools/medir_ventanas.py` como regla. Al
bajar "Ajustar stock" a 560, el medidor lo marcó:

```
MAL ajustes-stock   560x320   min 415x236   chica: 560 px de ancho
```

No se cambió la regla del medidor: se agrandó el diálogo a 640x340, que la
cumple y sigue siendo compacto. Un instrumento que da cero problemas es un
instrumento al que hay que escuchar, no al que hay que silenciar.

`medir_ventanas.py` recorre las pantallas del **menú**, no los modales, y por
eso este bug no aparecía en la medición. Hay `tools/capturar_dialogos.py`
para los diálogos y `tests/test_dialogos_chicos.py` que los mira por número.

---

## La botonera de los diálogos

Los cinco diálogos de `vistas/VentaSimple.py` y `AjustesStockView` llevan
`addStretch(1)` antes de los botones, que es lo que ya hacían `vistas/Stock.py`,
`vistas/ABM.py` y `vistas/Main.py`.

Sin él, el sobrante vertical no tiene destino y Qt lo reparte como puede: o el
título crece (el caso de arriba), o la botonera queda pegada al tope con el
vacío abajo. Las dos se ven mal.
---

## Sembrar datos para probar a mano

    python tools/sembrar_stock.py            # siembra el sandbox
    python tools/sembrar_stock.py --revisar  # solo muestra, no escribe
    python tools/sembrar_stock.py --rehacer  # borra lo sembrado y rehace

Tres articulos de prueba no alcanzan para probar el modulo: con eso nunca hay
uno en negativo, nunca hay un remito, y el boton de marcar productos no tiene
con que fallar. `sembrar_stock.py` deja un catalogo de ferreteria con los
**cinco estados** que puede mostrar la columna "Estado", para que cada camino
del operador tenga un caso.

### Que deja

| Articulo | Stock | Minimo | Estado | Para que sirve |
|---|---|---|---|---|
| TORN-0001 Tornillo hexagonal | 160 | 50 | OK | el caso normal |
| ARAND-114 Arandela plana | 85 | 200 | **Falta** | el mas faltante |
| TUE-880 Tubo de acero | 4 | 10 | Falta | falta de poco |
| CABLE-25 Cable NYY | 0 | **0** | **Sin stock** | con minimo 0 no puede ser "Falta" |
| PILA-AA Pila AA blister | 5 | 20 | Falta | el del remito |
| LIJA-180 Lija al agua | 60 | 40 | OK | tiene una venta **anulada** |
| MASILLA-5 Masilla acrilica | 1 | 6 | Falta | tiene un **ajuste** con observacion |
| REMACHE-4 Remache popper | **-2** | 5 | **Negativo** | se vendio sin stock |
| CARTON-90 Carton corrugado | 500 | 0 | OK | minimo 0 |
| ACEITE-3 Aceite de motor | 10 | 8 | OK | |
| TINTA-01 Tinta universal | - | 0 | **Sin controlar** | producto que no se inventaria |
| SERV-INST / SERV-VIS | - | 0 | Sin controlar | servicios |

Los tres ultimos son los que separan una cosa de la otra: `TINTA-01` es
`concepto` 1 y no se controla, los dos servicios son `concepto` 2. "Marcar
productos" tiene que marcar la primera y dejar las otras dos, y con el seed se
puede ver.

### El remito, que es el que vale

`PILA-AA` tiene un remito de 10 y su factura con `idremito` puesto. El remito
descuenta y la factura **no** vuelve a descontar: quedan en **5**, no en -5.

Es la regla mas cara del modulo, porque si se rompe no se ve en ninguna
pantalla: el total de la factura esta bien, el comprobante esta bien, y el stock
queda mal. El seed la deja escrita en los datos y se verifica sola: si el
numero no da, el script sale con codigo 1.

### Que se autoverifica

No es un `INSERT` a ciegas. Al final vuelve a leer el stock con
`libs.stock.stock_de` y lo compara con el numero que el catalogo declara, y con
el estado que da `controladores.Stock.estado_de`. Ademas, al sembrar, comprueba
que la factura del remito escribiera **0** movimientos.

`tests/test_semilla_stock.py` corre el mismo `sembrar()` contra la base en
memoria y mira las diferencias. Se verifico que **detecta la rotura**: al
neutralizar la regla del remito en `libs/stock.py`, los tests caen.

### Por que no toca la base de trabajo

Porque ya paso: una migracion de prueba corrio sobre la base de trabajo y perdio
37 ventas. El seed fija la carpeta destino con `PYFE_CARPETA_DATOS` (que
`libs/rutas.py` lee antes que el directorio de trabajo), copia la base a un
`.bak` con fecha antes de escribir, y **se niega a correr** si la carpeta
resulta ser la de la instalacion o `%LOCALAPPDATA%\Asiento`. Eso ultimo esta
probado: no es una regla de palabra.

### Un detalle que aparecio mirando

En la pantalla de Movimientos, las compras muestran **"Compra 3"** —el id de la
fila— mientras que las ventas muestran el numero del comprobante ("Factura
0001-00000045"). No es el seed: es `controladores/Stock.py`, que para las ventas
consulta el numero y para las compras imprime el id. Un numero interno no le
sirve a nadie para pedir un comprobante.


### --rehacer no era idempotente, y --revisar no lo delataba

Las dos fallas aparecieron por usar el seed de verdad, y estan aqui porque las
merecen.

**El seed se sembraba dos veces y el stock quedaba exactamente al doble.** La
causa: `_deshacer()` borraba los movimientos filtrando por la marca que va en la
observacion, y solo la ponen los movimientos directos (el conteo inicial y el
ajuste). Los que escriben `aplica_factura`, `aplica_compra` y `aplica_remito`
van con la observacion **vacia**, porque esas funciones no la toman. O sea: la
mitad de lo sembrado no se borraba nunca y el seed siguiente sumaba encima.

Ahora borra por **articulo**, no por marca: es lo que no deja ninguno.

**Y `--revisar` salia con codigo 0 aunque encontrara diferencias.** Eso es lo
peor de las dos: el script detecta que el stock no da (imprimio
`se esperaba 160` en nueve filas) y despues se va con codigo de exito. Un chequeo
que encuentra una diferencia y no la hace pasar es un chequeo que no le sirve al
que lo pide, porque el que lo pide mira el codigo de salida y no la pantalla.

Ahora `--revisar` imprime las diferencias, dice la causa mas probable y sale con
codigo 1.

**Un detalle de nombres de columna.** La primera version de `_deshacer()` iba
con SQL a mano y se equivocaba en tres columnas: en esta base `detalleremito`
usa `producto_id` y `remito_id`, y `remito` usa `cliente_id`. Solo `cabfact`
tiene `idCliente`, porque el modelo lo declara asi. Por eso ahora todo va con los
modelos de peewee y no con SQL escrito a mano: los nombres salen del modelo, y
un nombre bien escrito a mano en otra base borra otra cosa.

Con eso, dos `--rehacer` seguidos dan el mismo stock.


### Los numeros que se escriben a mano salian sin formatear

Este se encontro mirando la pantalla, no leyendo el codigo. En una venta de 100
unidades a 1.500, la celda **Unitario** decia `1.500,00` y el **SubTotal** de al
lado decia `150000.0`, en la misma fila. La columna **Stock** decia `85.0000`
en vez de `85`.

**La causa es de `Grilla.ModificaItem`:** formatea SOLO si el valor es `int`,
`float` o `Decimal`. Si le pasas un string, lo escribe tal cual, sin formato y
sin `UserRole`. El handler pasaba `str(cantidad * precio)`, y `_pinta_celda`
hacia `item.setText(str(hay))`.

Lo corregido es pasar el numero y dejar que la grilla lo formatee segun el tipo
que declaro la columna, que es lo que ya hace `AgregaItem`.

#### Por que ningun test lo habia visto

Porque el test comparaba el **numero** del texto, parseandolo con
`_a_numero_texto`: le daba lo mismo `150000.0` que `150.000,00`. Un aserto que
mira el valor y no el texto literal no ve un problema de presentacion, y esta
pantalla es de mirar.

Los tres tests de esto comparan la cadena exacta: `"10.000,00"`, `"85"`.

#### Y un test que era vacio

El primero que se escribio para esto no fallaba contra el codigo roto, y la
razon fue util: recargaba la cantidad con **el mismo numero** que ya estaba.
Qt no emite `cellChanged` cuando el texto no cambia, asique el handler no se
recorria y el SubTotal conservaba el formato original de `AgregaItem`.

Un test que pone el mismo valor y mira el resultado no esta probando el camino
que dice probar. Para editar de verdad hay que cambiar el numero.


### El total de la venta se veia apagado y sin separador de miles

Tambien por mirar la pantalla. Con dos renglones, los **SubTotal** de la grilla
salian `187.575,00` y `62.525,00`, y el **total** de abajo decia `250100.00`.

**El numero estaba bien.** `calcular_totales` trata el precio unitario como
precio final con el IVA adentro (desprende el IVA para armar la factura), asi
que sumar los SubTotal es lo correcto y no hay nada que recalcular. Lo que
fallaba era como se leia.

Tres cosas:

1. **Sin separador de miles.** `str(Decimal("250100.00"))` sale
   `250100.00`: sin puntos, con punto decimal y con la coma cambiada. Al lado
   de los SubTotal, que salen con el formato argentino, el total se veía como si
   fuera de otra pantalla. Ahora usa `_formato_importe`, el mismo de la grilla.
2. **Apagado, porque el campo estaba deshabilitado.**
   `EntradaTexto(tamanio=16, enabled=False)` llama `setEnabled(False)`, y Qt
   pinta un widget deshabilitado con la paleta de inactivo: el numero mas
   importante de la pantalla se veía gris, como un campo de formulario que no
   se puede tocar, al lado de una botonera con "Emitir factura".
   Ademas un campo deshabilitado no deja seleccionar el texto, y un operador
   que necesita pasarlo por whatsapp no lo podia copiar.
   Ahora es `setReadOnly(True)`: no se puede escribir a mano, pero se ve normal
   y se puede seleccionar.
3. **A la izquierda.** Los importes alineados a la derecha hacen que las cifras
   encajen y se puedan comparar entre ventas; a la izquierda, un total de cinco
   digitos queda pegado al rotulo y uno de siete se separa.

El `0` inicial tambien paso de `0.00` a `0,00`, para que el cambio de formato no
se note cada vez que se borra un renglon.

#### Que no estaba verificado

Los cuatro tests de esto comparan la cadena literal y detectan cada rotura por
separado: sin formato, sin alineacion, deshabilitado, y el `0` inicial. Se
comprobó rompiendo cada cosa y viendo que el test correspondiente cae.

#### Y un error mio al aplicar el arreglo

El primer parche metio DOS llamadas a `setText` seguidas en `recalcular_total`
(un reemplazo de mas), asi que el archivo tenia la misma instruccion repetida.
No rompia nada, porque las dos escriben lo mismo, pero quedo al detectar que un
test de verificacion contaba `2 coincidencias` donde esperaba `1`.

Es el mismo criterio de los parches con conteo previo, aplicado al archivo: un
`2` donde se esperaba `1` es la senal de que algo se aplico dos veces.
### Para mirar las pantallas con datos

    python tools/capturar_stock_sembrado.py

Abre Stock, Ajustes y Movimientos contra el sandbox, con el tema aplicado, y las
guarda en `_capturas/`. Con la plataforma de Qt de verdad, porque con
`offscreen` los textos no se dibujan y una captura sin texto no dice nada de la
pantalla.
