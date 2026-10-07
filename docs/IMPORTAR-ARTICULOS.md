# Importador de artículos desde Excel

Importa la lista de precios que manda un proveedor (`Importacion compuesta.xlsx`)
y crea o actualiza los artículos del catálogo. La pantalla está en
**Stock → Importar productos desde Excel**.

## Qué hace

Por cada fila del Excel arma un artículo con:

| Campo del Excel | A dónde va en el sistema |
|---|---|
| `CODIGO DE BARRA` | `articulos.codbarraart` |
| `NOMBRE1` + `Nombre2` + `Nombre3` + `Nombre4` | `articulos.nombre` (corte en 100) y `articulos.nombreticket` (corte en 30) |
| `GRUPO` | `articulos.idgrupo` — se crea el grupo si no existe |
| `COSTO` | `articulos.costo` |
| `GANANCIA` | se convierte a **porcentaje** y se guarda en `articulos.incre1`; con eso se calcula `articulos.preciopub` |
| `PROVEEDOR` | **se lee pero no manda**: el proveedor es el que se elige en la pantalla |
| `IVA` | `articulos.tipoiva` — la alícuota de la fila si existe en el catálogo; el `0` y las planillas sin columna usan el que se elige en la pantalla |

El precio al público es **`costo × ganancia`**, redondeado a 4 decimales porque
`preciopub` es `DECIMAL(12,4)`.

## Qué se pregunta y por qué

Lo que se pregunta es exactamente lo que el archivo **no puede** decir:

- **De qué proveedor es la lista.** El archivo trae `NORDESTE` en texto libre y
  la base lo guarda como id. Resolver por nombre crearía un "Nordeste" duplicado
  del que ya estaba, así que se elige de los proveedores cargados. Si no hay
  ninguno, la pantalla avisa y no deja importar.
- **La ganancia por defecto.** Sale del archivo renglón por renglón. El valor de
  la pantalla es un **porcentaje** (30 es 30%) y cubre solo los renglones que
  llegan sin ganancia; una lista con 1.4 y 1.5 mezclados respeta la
  diferencia del proveedor. Cuando se elige la planilla, la pantalla **dice
  cuántas filas van a depender de ese campo**, porque si no el operador se
  entera recién en el resumen final, con los artículos ya escritos.
- **El IVA.** Ver abajo.
- **Unidad, concepto de facturación y control de stock.** Defaults razonables
  que se cambian para toda la carga.

Lo que **no** se pregunta es el grupo: sale de la columna `GRUPO` del archivo y
se crea solo si falta. Preguntar de qué grupo va cada producto duplicaría un
dato que ya está en la planilla.

## Las cuatro decisiones que se tomaron

Están confirmadas con quien pidió la herramienta:

1. **`GANANCIA` es multiplicador.** 10142 × 1.4 = **14198.80**. No es un
   porcentaje. Pero el margen **queda guardado como porcentaje**: ese 1.4 se
   escribe como `incre1 = 40`. Ver "El margen queda escrito" abajo.
2. **El `0` de la columna `IVA` no es "exento".** Significa "no lo sé": el
   archivo trae la columna en cero en todas las filas y eso no es una opinión
   sobre el impuesto, es una espera. Si se tomara como exento, el catálogo
   entero quedaría con el impuesto equivocado y nadie se enteraría hasta ver la
   factura. Con el cambio del 7 de octubre de 2026 el `0` sigue siendo "no lo
   sé" (usa el de la pantalla), pero una alícuota **de verdad** en la fila sí
   manda. Ver "El IVA por renglón" abajo.
3. **Si el artículo ya existe, se actualiza.** Se le cambian costo, precio y
   proveedor. Una lista de precios se recarga, no se duplica.
4. **El grupo que falta se crea solo**, con el impuesto por defecto de la base
   (sin percepción).

## El margen queda escrito

Antes del 7 de octubre de 2026 el importador usaba la `GANANCIA` del archivo
para calcular el precio y **la tiraba**: el artículo quedaba con
`preciopub = costo × 1.5` y `incre1 = 0`. El sistema tenía el resultado de la
cuenta pero no la cuenta.

Eso producía exactamente esta pantalla: un artículo con costo 34.540,20, precio
51.810,30 (que es 1.5) y **"Ganancia % 0,00"**. El operador no tenía forma de
saber de dónde salía ese precio ni cambiarlo sin editar los 704 artículos uno por
uno. Y si cargaba 30% en "Ganancia por defecto" al importar, el catálogo
quedaba partido sin que nadie lo supiera: 679 artículos al 50% (el 1.5 del
archivo) y 20 al 30% (su valor de respaldo), todos con el margen en cero.

Ahora el multiplicador se convierte y se guarda:

| Del archivo | Se guarda en `incre1` |
|---|---|
| `1.5` | `50` |
| `1.4` | `40` |
| `1.25` | `25` |
| el porcentaje que cargó el operador (`30`) | `30` |

Y el precio sale **del margen guardado**, no del multiplicador, para que los dos
números nunca se contradigan. Como `incre1` es `DECIMAL(12,2)`, un margen con
más de dos decimales se redondea y el precio sigue al margen redondeado: con
un multiplicador de 1.33333 el margen es 33.33 y el precio sale de ese 33.33.
Con los multiplicadores de dos decimales que traen las listas reales no hay
diferencia ninguna.

**Para completar el catálogo que ya está cargado:** reimportar la misma
planilla. Los artículos se detectan como actualizados porque el margen cambia,
se les escribe y **no se mueve ningún precio** (el margen derivado da el mismo
número que el que ya estaba). Es la única forma de obtener el dato sobre 700
artículos sin tocar el catálogo a mano.

## El IVA por renglón

Hasta el 6 de octubre de 2026 el IVA era **uno solo para toda la carga**: el
que se elegía en la pantalla. A partir del 7, cada fila puede traer el suyo.

El archivo trae la **alícuota** (21, 10.5) y la base guarda el **código**
(`01`, `02`), así que hay que traducir una en otra contra el catálogo de
`tipoiva`. Las reglas:

| La fila trae | Qué pasa |
|---|---|
| Una alícuota que está en el catálogo | Se usa esa, renglón por renglón |
| `0`, o no hay columna IVA | Usa el que eligió el operador |
| Una alícuota que **no** está en el catálogo (5.5, por ejemplo) | **La fila no entra**, y se dice por qué |

Lo del tercer caso es una decisión, no una comodidad. Adivinar el impuesto
produce una factura con el impuesto equivocado, y eso no se ve hasta que hay
que emitir. Es el mismo criterio que ya se aplicaba con un `COSTO` ilegible:
una fila mala no frena a las otras 399, pero tampoco entra a medias.

Por qué el `0` no se mapea a "exento": el catálogo tiene un `50` CONCEP. NO
GRAVADOS con alícuota 0. Si el `0` del archivo se tomara por exento, una lista
de precios de mercaderia entera entraría sin impuesto.

**El `PROVEEDOR` sigue sin mandar por renglón.** Un Excel compuesto con 2 o 3
proveedores distintos todavía se importa entero con el proveedor que se elige en
la pantalla. Está anotado como pendiente abajo.

## Lo que la pantalla avisa antes de importar

Al elegir la planilla, el resumen dice cuántas filas hay y, si hay, cuántas van
a depender del campo "Ganancia por defecto":

> La planilla tiene 704 filas de datos. 20 no traen ganancia y van a usar la
> que está arriba: sin ese valor no entran.

Sin ese número, el operador descubre el problema en el resumen final, con los
artículos ya escritos, y tiene que rehacer la carga. En la planilla real de
`ANYWAY` son 20 de 704 las que llegan sin ganancia.

Solo se cuentan las filas que todavía son importables: una fila con un dato
ilegible va a fallar por ese motivo y no por la ganancia, y contarla sería
mentir sobre la causa del error que el operador va a ver después.

## Pendientes

- **Importación compuesta con varios proveedores.** Hoy un Excel con 2 o 3
  proveedores distintos se importa entero con uno solo. Resolver el nombre del
  archivo contra la base tiene el riesgo de crear un "Nordeste" duplicado del
  "Nordeste" que ya estaba, así que hace falta una decisión explícita sobre qué
  pasa con un proveedor que no está cargado (crearlo, como se hace con los
  grupos, o frenar la fila).
- **`PROVEEDOR` del archivo no se usa para nada.** Se lee, se guarda en el
  registro, y ahí queda.

## Cómo se decide que un artículo ya existe

En este orden, y por qué:

1. **Código de barras.** Es el único identificador que el proveedor y el sistema
   comparten de verdad. Si el renglón trae un código que **no** está en la base,
   es un producto nuevo aunque se parezca en el nombre a uno viejo: un código de
   barras no se reasigna solo.
2. **Nombre normalizado**, cuando el renglón no trae código. Sin acentos, en
   mayúsculas y con espacios colapsados, para que `whey protein` y
   `WHEY   PROTEIN` sean el mismo producto.

Un artículo sin código de barras y sin nombre reconocible recibe un código
interno que empieza con `INT`, para que se vea que no es un EAN y nadie lo
escanee en el mostrador.

## Bugs que se encontraron haciendo esto

Esta es la parte que conviene no perder, porque son errores que **pasan los
tests si no se busca el síntoma**.

### El separador de miles del COSTO

`Decimal("10.142")` son diez con mil y cuatro centésimas, no diez mil ciento
cuarenta y dos. En una lista de precios real el costo viene con el punto de
miles, y con esa lectura el costo entra **mil veces más chico** y el precio sale
con tres ceros de más. El error no se ve hasta que la factura no cierra.

La regla quedó **por columna**, porque el mismo texto significa cosas distintas:

| | `1.400` significa |
|---|---|
| `COSTO` | 1400 (punto de miles) |
| `GANANCIA` | 1.400 (punto decimal) |

En `GANANCIA` el punto es siempre decimal: una ganancia de mil cuatrocientos no
existe en una lista de precios, y `1.4` tiene que seguir siendo `1.4`.

### El IVA por defecto caía en 10.5%

`ComboIVA` ordena por descripción, y `"10.5"` ordena **antes** que
`"IVA GENERAL"`. El primer elemento de la lista era el 10.5%, así que la
pantalla quedaba con ese y **todo artículo importado entraba con el impuesto
bajo**. El dato estaría mal en el catálogo entero y parecería correcto.

La pantalla ahora fuerza el `01`. Hay un test que falla si el 10.5% vuelve a
quedar elegido.

### peewee devuelve objetos en las claves foráneas

Este es el que más tiempo costó y el que más daño hacía en silencio.

Cuando se lee un `Articulo`, `articulo.grupo` es un `<Grupo: 2>`,
`articulo.tipoiva` es un `<Tipoiva: 01>` y `articulo.provppal` es un
`<Proveedor: 1>` — **objetos, no los valores crudos**. Comparar eso contra el
`2` o el `"01"` que uno tiene en la mano dice siempre *"cambio"*.

El efecto: **recargar la misma lista de precios reportaba "4 actualizados" y no
tocaba nada**. Un resumen que miente deja de servir, y el operador deja de
mirarlo justo el día que sí importa.

La solución está en `_mismo_que_ya_esta`, que lee el renglón con
`.dicts()` y compara los escalares. Un test (`test_la_planilla_original_es_idempotente`)
falla con el código roto.

Dos caminos que **no** sirven para leer el valor crudo, por si alguien los
prueba:

- `articulo.__data__[columna]` viene con las claves por **nombre de campo**, y
  para los campos cuyo `column_name` difiere (`grupo` → `idgrupo`,
  `codbarra` → `codbarraart`) devuelve `None`.
- El sufijo `_id` no existe en todos los FK: hay `provppal_id`, `unidad_id` y
  `tipoiva_id`, pero `grupo_id` no.

### Los bits de MySQL

MySQL devuelve un `BIT(1)` como `b'\x01'`, que nunca es igual a `True` con
`==`. La comparación de "cambió" usa `_a_bit()` de `modelos/ModeloBase.py`.

### El nombre partido en cuatro columnas

Los nombres de esta lista pasan de los 100 caracteres, y `articulos.nombre` es
`CHAR(100)`. MySQL **corta en silencio** y quedan dos productos con el nombre
igual. El importador recorta a propósito (`nombre[:100]`) y arma
`nombreticket` con los primeros 30, como hace el ABM de artículos.

## Qué se probó

`tests/test_importar_articulos.py`, 33 tests:

- **Núcleo** (base en memoria, sin Qt): lectura, nombres partidos, separador de
  miles, precio, grupos, alta, actualización, idempotencia, ganancia por
  defecto, IVA, control de stock.
- **La planilla original**: se lee `Importacion compuesta.xlsx` de verdad. Si el
  proveedor cambia el formato de la columna `GANANCIA`, esos tests avisan.
- **La pantalla**: se construye la vista real y se ejecuta `importar()` de punta
  a punta, con los dos diálogos modales parcheados porque no hay nadie para
  apretarlos.

Los tests que importan usan la base en memoria de `tests/ayuda_stock.py`. **No**
escriben en `sistema.db`: una importación de prueba contra la base de
desarrollo metería artículos falsos en el catálogo real.

### Cómo se verificaron los tests

Un test que no falla con el código roto no está probando nada. Se rompió el
código a propósito dos veces y se comprobó que los tests lo detectaran:

| Qué se rompió | Qué test lo detectó |
|---|---|
| Sacar el `quantize` del precio | `test_el_precio_respeta_cuatro_decimales` (con el `assert`, no con un error) |
| Volver a leer el modelo en vez de `.dicts()` | `test_una_recarga_sin_cambios_no_dice_que_actualizo` y `test_la_planilla_original_es_idempotente` |

## Archivos

| Archivo | Qué es |
|---|---|
| `libs/importararticulos.py` | Toda la lógica. Sin Qt, se puede probar sola. |
| `vistas/ImportarArticulos.py` | La pantalla. Solo junta lo que se pidió. |
| `controladores/ImportarArticulos.py` | El registro en `controladores/Main.py`. |
| `tests/test_importar_articulos.py` | Los 33 tests. |
| `modelos/Proveedores.py` | Se agregó `ComboProveedor` (el combo del catálogo). |

## Pendientes

- [ ] **Probar con la lista real del proveedor, no con las 4 filas de prueba.**
      El archivo de ejemplo tiene 4 renglones y nombres largos; una lista de
      varios cientos con partidas repetidas es el caso real y todavía no pasó
      por acá.
- [ ] **El proveedor puede no existir todavía.** Hoy la pantalla exige elegir uno
      cargado y avisa si no hay ninguno. Si el flujo real es "dar de alta el
      proveedor y después importar", falta un atajo para crearlo desde la misma
      pantalla (hoy hay que ir a Proveedores, salir y volver).
- [ ] **Sin barra de progreso real.** La barra queda en modo indeterminado
      mientras corre: con una lista de miles de artículos el operador ve la
      pantalla ocupada y no cuánto falta.
- [ ] **Sin resumen exportable.** El aviso final dice cuántas filas quedaron
      afuera, pero no se puede guardar para revisarlo después.
- [ ] **El concepto de facturación y el control de stock son para toda la
      carga.** Si un mismo Excel mezcla productos y servicios, hay que correrlo
      dos veces.
- [ ] **No probado contra MySQL.** Todo el desarrollo y los tests son con la
      base en memoria (sqlite). Los caminos que solo existen en MySQL —el
      `BIT(1)` de `controlastock`, los `DECIMAL` reales— están escritos según
      lo que dice el modelo, pero conviene una prueba contra una base MySQL de
      verdad antes de confiar en los importes de una lista real.