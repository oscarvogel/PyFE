# `articulos.incre1`: el porcentaje de ganancia en el ABM de productos

## Que se agrego

El campo **`incre1`** en la tabla `articulos`: el **porcentaje de ganancia de la
lista 1**. En el ABM de productos aparece un Spinner nuevo, `Ganancia %`, entre
`Costo` y `Precio al publico`.

Es el nombre que ya se usa en la base MySQL de produccion, asi que la columna
se llama `incre1` y no `ganancia`, aunque en la pantalla diga "Ganancia %".

## La cuenta

```
precio al publico = costo x (1 + incre1 / 100)
```

- `incre1 = 40` con `costo = 10142` da `preciopub = 14198.80`.
- El calculo vive en **`libs/ganancia.py`** (`precio_desde_incre1` y
  `margen_activo`), sin PyQt5, para poder probarlo sin `QApplication`.

Es la misma cuenta que hace el importador, en otra escala:

| Donde | Como se llama | Que se carga | Formula |
|---|---|---|---|
| Importador (`libs/importararticulos.py`) | columna `GANANCIA` de la planilla | `1.4` | `costo x 1.4` (multiplicador) |
| ABM de productos (este cambio) | campo `incre1` | `40` | `costo x (1 + 40/100)` (porcentaje) |

El importador **no** se cambio: sigue leyendo multiplicadores, que es lo que
trae la planilla del proveedor. La conversion no hace falta porque cada uno
guarda en su propia escala y el ABM convierte al calcular.

## Como se usa

- **Con `incre1 > 0`**: el precio al publico se calcula solo y el campo de
  precio queda **en solo lectura**. El precio sigue al costo mientras haya
  margen cargado.
- **Con `incre1 = 0`**: el precio se carga a mano, como siempre, y el campo de
  precio queda editable.

Cero significa "no hay regla cargada", **no** "vender a costo". Para vender a
costo se tipea el costo como precio. Un `QDoubleSpinBox` no puede estar vacio, asi
que el cero es la unica forma de decir "apagado".

Un `incre1` negativo se trata como no cargado: descontar es una decision
comercial que se toma en el precio, no escribiendo un numero negativo en un campo
de porcentaje.

## Quien llena este campo

- **El ABM de artículos**: es donde se carga a mano.
- **El importador de Excel**: escribe la `GANANCIA` de cada renglón, convertida
  de multiplicador a porcentaje (1.5 de la planilla se guarda como 50). Antes
  no la guardaba y los artículos importados quedaban con `incre1 = 0` al lado de
  un precio al 50%. Ver "El margen queda escrito" en
  [`IMPORTAR-ARTICULOS.md`](IMPORTAR-ARTICULOS.md).

**Para completar un catálogo que ya tiene precios pero margen en cero:** reimportar
la planilla. No mueve ningún precio, solo escribe el margen.

## Por que no rompe nada

`incre1` entra con **default 0**, no `NULL`. Todos los articulos que ya estan en
la base quedan en "precio a mano", que es como estaban: agregar la columna no
cambia el comportamiento de ninguno. El precio solo se calcula cuando el
operador carga un porcentaje, no por el hecho de que exista la columna.

## La migracion

`MigrarVersion10` en `controladores/MigracionBaseDatos.py` agrega
`articulos.incre1` (`DECIMAL(12,2)`, default 0) y sube `VERSION_DB` a `10`.

- **En sqlite** (la base de desarrollo y de las instalaciones nuevas sin MySQL):
  agrega la columna.
- **En MySQL** (produccion): **no hace nada**. La columna ya existe ahi, y
  `_agregar_columna` la ve y no genera SQL. Por eso es segura correr en los dos
  motores sin preguntar en cual esta.
- **En una instalacion nueva**: tampoco genera SQL, porque `MigrarVersion0` crea
  las tablas desde los modelos y el modelo ya trae `incre1`.

La siembra de `data/articulos.csv` **no** se toco, siguiendo el precedente de la
migracion 9 (`controlastock` y `stockminimo` tampoco estan en el CSV): las
columnas nuevas quedan con su default y el `cargar_csv` no se rompe.

## AVISO: revisar los valores que ya estan en MySQL

Esto hay que hacerlo **antes** de abrir el catalogo de los clientes, no despues.

La migracion no toca los valores existentes de `incre1`. Si la base MySQL de
produccion venia usando ese campo, sus valores van a empezar a **calcular
precios** en cuanto se abra un articulo en el ABM. Si esos valores son un
porcentaje, la cuenta es correcta. Si son otra cosa (un multiplicador como el
`1.4` del importador, o un valor de otra epoca del sistema), el ABM va a calcular
un precio que no es el que el operador espera.

Como verificarlo, en MySQL:

```sql
SELECT incre1, COUNT(*) FROM articulos GROUP BY incre1 ORDER BY COUNT(*) DESC;
SELECT idarticulo, nombre, costo, preciopub, incre1
  FROM articulos WHERE incre1 IS NOT NULL AND incre1 <> 0;
```

Que hacer segun lo que salga:

- **Si hay valores y son porcentajes**: no hay nada que hacer. El ABM los usa
  tal cual.
- **Si hay valores y NO son porcentajes**: convertir (`incre1 = incre1 * 100`
  si eran multiplicadores) o dejarlos en 0 con
  `UPDATE articulos SET incre1 = 0 WHERE incre1 <> 0` para volver al modo de
  precio a mano.
- **Si la consulta no devuelve nada**: no hay nada que revisar.

El default 0 protege a los articulos que **no** tienen valor cargado: esos
siguen con precio a mano. El riesgo esta solo en los que ya traian algo.

## Tests

`tests/test_incre1_ganancia.py` (28 tests):

- La cuenta, incluidos los cuatro decimales de `preciopub` (`DECIMAL(12,4)`).
- Que cero y negativo no son margen activo.
- Que el modelo declara el campo con default 0.
- `RecalculaPrecio`: calcula, bloquea el precio, y volver a 0 lo desbloquea.
- La pantalla de verdad, con las senales de `ArmaCarga`: costo 100 + 40% da
  140 bloqueado, cambiar el costo a 200 recalcula a 280, y volver a 0
  desbloquea.
- El guardado persiste la cuenta y no lo que quedo escrito en el control.
- La migracion: agrega la columna en una base vieja, no genera SQL en una nueva,
  es idempotente, sella la version en 10, y no toca los precios existentes.

### Dos trampas que los tests esquivan a proposito

1. **`ArticulosView.__new__` sin `__init__` no prende las senales.** La vista
   hereda de un `QWidget`; una instancia creada sin `__init__` no tiene lado C++
   y una conexion a un metodo ligado de esa instancia no dispara. Un test que
   use `__new__` y espere que la senial dispare pasa en verde sin probar nada.
   Por eso la parte rapida llama a `RecalculaPrecio()` directo, y las senales se
   prueban con la pantalla construida de verdad.

2. **`isEnabled()` devuelve el estado efectivo**, o sea el del control Y el de
   sus padres. La pestana de detalle arranca deshabilitada, asi que sin
   `v.tabDetalle.setEnabled(True)` todos los controles dan `False` y el test
   estaria probando la pestana y no el bloqueo del precio.

## Pendientes / cosas que quedaron fuera

- **`modificaprecios` sigue siendo un campo muerto.** Se graba y se muestra en
  pantalla, pero ningun codigo del proyecto lo lee. Era el bandera que
  deberia gobernar "este precio sale del costo con este margen", y ahora que
  `incre1` existe la pregunta es si se lo deja (porque quizas signifique algo
  en el sistema de origen) o se lo saca. **No se toco** en este cambio.
- **El reporte de ventas por grupo no muestra margenes.** Se decidiu que este
  cambio era solo el ABM.
- **La tabla de la lista no muestra `incre1`.** `camposAMostrar` sigue con
  `idarticulo, nombre, preciopub`.
- **La lista 2 no existe todavia.** El nombre `incre1` deja el lugar prepared
  para un `incre2`, pero no se agrego nada.