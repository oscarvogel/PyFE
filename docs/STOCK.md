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

**Para empezar:** `Stock → Marcar productos` marca de una vez todo lo que esté
en `False`. Marcar de a uno obliga a entrar veinte veces al ABM de Productos, y
el que se saltea uno se da cuenta semanas después, cuando el stock de ese
producto no baja nunca.

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
