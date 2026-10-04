# El ABM de clientes: por qué se veía feo y por qué no se podía usar

Fecha: 2026-10-03
Alcance: `vistas/ABM.py` (la clase base de los 12 ABM), `libs/Grillas.py` y
`libs/tema.py`.
Cómo se pidió: "este abm de clientes quedó muy feo" + el `NameError` que
salió al apretar **Editar**.

---

## Qué estaba mal, con números

Todo se verificó renderizando la pantalla con la base real (`sistema.db`, 57
clientes), no leyendo el código. La grilla de una ventana de 959 px:

| | Antes | Después |
|---|---|---|
| Columna `Idcliente` | **732 px (76%)** | **157 px (15%)** |
| Columna `Nombre` | 227 px (24%) | 886 px (85%) |
| Código de cliente | `1,00` | `1` |
| Botón **Nuevo** | `NameError` | funciona |
| Botón **Editar** | `NameError` | funciona |
| Título de la ventana | "ABM de Clientes" + la misma etiqueta adentro | "Clientes", una sola vez |

Esos 700 px de blanco al lado del código no eran un problema de gusto: el
nombre del cliente era lo único que se lee en esa pantalla, y se leía cortado
en dos renglones.

---

## Bug 1 — `limpiar_estado()` llamaba a una función que no existe

`libs/tema.py` definía `marcar_estado()` y la función que la usa decía
`marca_estado()`:

```python
def limpiar_estado(widget):
    marca_estado(widget, "")   # NameError
```

`Agrega()` la llama por cada control y `CargaDatos()` también, así que el
**"Nuevo" y el "Editar" estaban rotos en los doce ABM de la app**: clientes,
proveedores, artículos, localidades, impuestos, grupos, centro de costos,
tipos de documento, tipos de responsable, tipos de comprobante, categorías de
monotributo y parámetros del sistema. No había forma de dar de alta ni de
modificar nada en ninguno.

**Cómo se manifiesta:** el error salía en la consola y la ventana se
quedaba en la pestaña de "Detalle" vacía, sin decir nada en pantalla.

**Por qué ningún test lo agarró:** los tests de grilla y de tema no apretan
los botones. Hacen falta tests que abran la pantalla y aprieten Nuevo y Editar
— por eso está `tests/test_abm.py`.

---

## Bug 2 — la columna de código se comía la tabla

`Grilla._estirar_la_mas_larga()` decide qué columna absorbe el ancho sobrante
eligiendo, entre las que no son numéricas, la que tiene el **encabezado más
largo**. Con la tabla vacía (que es como nace) no hay nada mejor: no se sabe
qué hay en cada columna.

En el ABM de clientes eso elegía `Idcliente` (9 letras) por sobre `Nombre`
(6 letras). Resultado: 732 px para el código, 227 para el nombre.

Se arregla en dos partes:

1. **El ABM declara el tipo de cada columna** (`ABM._formatos_de_campos()`,
   leyendo el campo de peewee). Con `Idcliente` declarado `Entero`, deja de
   ser candidata al sobrante desde el arranque, sin esperar a que carguen
   datos. Sirve para los 12 ABM, y de paso el código se muestra `1` en vez de
   `1,00`.
2. **`_reparte_anchos_con_datos()`** vuelve a repartir cuando entra la
   primera fila, que es cuando recién se sabe qué es numérico y qué es texto.

### La trampa de Qt que hizo fallar el primer intento

Con una sección de la cabecera en modo `Stretch`, **Qt impone el ancho y ni
`resizeColumnsToContents()` ni `setColumnWidth()` la tocan**. El primer arreglo
dejaba la columna con el ancho que tenía antes y el código seguía en 541 px.
Por eso el método vuelve a poner todas las secciones en `Interactive` *antes*
de medir.

---

## Bug 3 — el intento de arreglar el "1,00" que casi rompe la ficha del cliente

La primera solución fue que la grilla dedujera el tipo de la columna a partir
del valor de Python: si es `int`, es un código y no lleva decimales. Con un
test a favor y todo.

**Se descartó porque es un error esperando.** `controladores/Clientes.py:70`
carga la primera fila de la ficha del cliente así:

```python
[fecha, 'Saldo Inicial', 0, 0, saldo_inicial, 0]
```

Ese `0` de debe y haber es un `int`. Con la regla nueva, la columna se
tipaba `Entero` para toda la ficha y los importes de las filas siguientes se
veían **redondeados**: `1.234,56` se mostraba como `1.235`. Un test lo
detectó antes de que llegara a la pantalla, y por eso quedó escrito el test
`test_la_primera_fila_no_poisona_el_resto_de_la_columna`.

**La regla que quedó:** el tipo de una columna lo declara quien arma la tabla.
Si no se declara, la grilla asume `Decimal`, que es lo que corresponde a un
importe. Ver "1,00" de más en un código molesta; redondear un importe no.

---

## Otras correcciones de la misma pantalla

- **El título estaba dos veces**: en la barra de la ventana y como etiqueta
  arriba de la lista. Ahora va solo en la barra, y con el nombre de la tabla
  ("Clientes") en vez de "ABM de Clientes": la pantalla se abre desde la barra
  lateral, donde ya se sabe que es un alta-baja-modificación.
- **Placeholder "Busqueda"** → "Buscar". Y no "Buscar por nombre", porque hay
  ABMs que filtran por otra cosa (los parámetros del sistema, por parámetro; los
  impuestos, por detalle): un cartel que miente sobre lo que busca es peor que
  uno que no precisa.
- **Dos `print()` de depuración** en `Modifica()` y `CargaDatos()`, que
  escupían la fila y todos los datos del cliente por consola en cada edición.

---

## Verificación

| Qué | Cómo |
|---|---|
| Nuevo y Editar no tiran | 2 tests que abren la pantalla y aprietan los botones |
| Anchos de la tabla | comparación entre columnas, en la grilla y en la pantalla |
| El código sale entero | test sobre las 5 filas de la pantalla |
| El título no se repite | busca la etiqueta repetida en el árbol de widgets |
| Un `0` de arranque no envenena la columna | test de la fila "Saldo Inicial" |
| Base real | 57 clientes de `sistema.db`, render y lectura de anchos |
| Suite | **289 tests** (280 antes, 9 nuevos) |

Un detalle sobre los tests de anchos: comparan columnas entre sí y no pixeles
sueltos. Cuánto mide un encabezado depende de la fuente instalada en la
máquina, y un test que falla en la computadora de otro por un cambio de
tipografía no sirve para nada. Passaron recién después de corregir el umbral,
que estaba calculado con la fuente del entorno de pruebas.

---

## Pendientes

- [ ] **El "Detalle" sigue siendo un formulario plano**, con los campos en una
      sola columna y sin agrupar. Es la mitad de la pantalla y la que se mira
      al dar de alta un cliente. Es un rediseño, no un arreglo.
- [ ] **La lista muestra solo código y nombre.** Con 57 clientes, dos de ellos
      no se distinguen: falta CUIT o tipo de documento. Agregar columnas es
      decisión de producto, no un arreglo de estilo.
- [ ] **La columna que se estira se elige por el encabezado**, y no por el
      contenido. En tablas con varias columnas de texto (por ejemplo
      Localidades, que tiene nombre, provincia y nación) la elección es la del
      encabezado más largo, que no siempre es la que más texto tiene. Nunca
      elige una columna numérica, que era el problema grave, pero no es
      infalible.
- [ ] **`Borrar` no pide confirmación** y borra el cliente a la primera. Es el
      único botón de la barra que hace algo irreversible.
- [ ] **Mientras se esté con esta pantalla**: hay otra sesión trabajando en el
      mismo repo. El arreglo del `NameError` quedó commiteado por esa sesión
      (`65662f1`) y el resto del trabajo llegó a perderse una vez en un stash.
      Conviene commitear esto antes de seguir.
