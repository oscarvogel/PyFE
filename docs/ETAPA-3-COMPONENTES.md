# Etapa 3 — Componentes: tablas, importes y buscador

Fecha: 2026-10-03
Etapa anterior: `docs/ETAPA-2-NAVEGACION.md`
Pendiente que NO se hizo: el rediseño de la pantalla de emisión, que quedó en el
issue #32 porque necesita una decisión de producto antes de tocar una línea.

---

## Qué se hizo

Dos cosas que se usan en todas las pantallas: **las tablas** y **el buscador de
la barra lateral**. Las dos eran puntos de fricción daily con 36 acciones y
muchas columnas de importes.

---

## 1. Tablas: los importes se leen y los números se calculan bien

### La trampa

Las celdas mostraban `str(valor)`, y el código que suma leía el texto con
`re.sub("[^0123456789\\.]", "", ...)`. Agregar un separador de miles —que es
como se lee un importe en Argentina— rompía esa lectura en silencio: `"1.234,56"`
se convertía en `1.23456`, la tabla se veía bien y **el total salía mal**.

### La solución

**El texto es para mirar, el valor es para calcular.** La celda guarda el número
crudo en `Qt.UserRole` y muestra el texto formateado:

| | Se ve | Se lee |
|---|---|---|
| Importe | `1.234.567,89` | `1234567.89` |
| Cantidad | `2` | `2` |
| IVA | `21` | `21` |

`_a_numero_texto()` se encarga de entender las dos formas, y hay un test que
hace el viaje de ida y vuelta con 2000 importes aleatorios: formatear y volver
a leer tiene que dar el mismo número. Esa es la garantía de que se puede
formatear para mostrar sin miedo.

### Además

- **Encabezado alineado con los datos.** Una columna de importes con el título a
  la izquierda y los números a la derecha se ve rota. El tipo se puede declarar
  al armar el encabezado, y si no se declara **se descubre con la primera fila**:
  así las ~30 pantallas quedan bien sin tocar una por una.
- **Anchos por columna, no `resizeColumnsToContents`.** Con la tabla vacía (que
  es como nace) esa función calcula anchos mínimos y el encabezado queda
  arrancado a la izquierda con un mar de blanco al lado. Ahora el ancho se
  reparte según el texto del encabezado, lo que también resolvió que **"Cant."
  se comiera media fila** en la pantalla de venta.
- **El sobrante va a la columna de texto más larga**, no a la última. Estirar
  la última dejaba una columna de importe ocupando media tabla, que es al revés
  de lo que conviene: los importes se comparan entre sí en una columna angosta
  y el que se lee es el detalle.
- **`resizeColumnsToContents` solo cuando entra la primera fila.** Recalcular en
  cada fila hacía que la tabla "tiemblara" mientras se cargaba.
- **Excel:** los números se escriben como número, no como texto, así se pueden
  sumar en la planilla. Las fechas siguen yendo como fecha.

---

## 2. Buscador en la barra lateral

Con 36 acciones scrollear la barra era la única forma de encontrar algo que no
esté en las cuatro primeras líneas.

- Filtra por **nombre de la acción, clave interna y nombre de la sección**, así
  que escribir "monotributo" trae las dos acciones de esa sección aunque ninguna
  se llame así.
- **Ignora tildes y mayúsculas**: "CONFIGURACION" encuentra "Configuración".
- Esconde las secciones que se quedan sin resultados, no solo los botones.
- Aviso cuando no encuentra nada, con lo que se buscó.
- **Ctrl+K** lleva al buscador desde cualquier lado.
- Enter lleva al primer resultado, para poder emitir sin llegar al mouse.

---

## Bugs encontrados

### Los diccionarios de clase se filtraban entre tablas

`formatos`, `cabeceras`, `columnasOcultas`, `widgetCol` y `backgroundColorCol`
eran **atributos de clase**, o sea compartidos por todas las grillas de la app.
La tabla de la venta dejaba sus tipos (Cantidad, Moneda...) en la de
proveedores, que abría después en la misma corrida: ahí una columna de texto se
alineaba como número y un importe se formatted con los decimales de una cantidad.

Apareció porque un test pasaba solo y fallaba en la suite completa. Se
corrigió copiándolos a la instancia en `__init__`.

### El formato declarado no se aplicaba

El controlador arma la fila con `str(cantidad)`, `str(precio)`, `str(subtotal)`.
Como el tipo declarado nunca se usaba para decidir el formato, los importes
seguían saliendo como texto pelado. Ahora, si la columna declara tipo numérico y
el valor llega como texto, se convierte.

Esto no apareció leyendo el código: apareció al renderizar la venta con datos
reales y ver que los importes no llevaban separador de miles.

### Exportar a Excel se iba a romper

`ExportaExcel` hacía `dato.strip()` sobre lo que devuelve `ObtenerItem`. Con el
valor crudo (un número) eso es un `AttributeError`. Se reescribió ese bloque
para distinguir número, texto y fecha.

---

## Qué cambió en el contrato de `ObtenerItem`

En una columna numérica ahora devuelve el número, no el texto de la celda. Antes
devolvía `"450.00"`; ahora devuelve `Decimal("450.00")`.

Es una mejora: el que llama puede hacer cuentas sin envolverlo en `str()`.
Los dos tests que fijaban el contrato viejo se actualizaron, y ahora comprueban
**las dos cosas por separado**: el valor (`Decimal("450.00")`) y lo que se ve
(`"150,00"`), que es más informativo que antes.

---

## Verificación

| Qué | Cómo |
|---|---|
| Ida y vuelta formato → lectura | 2000 importes aleatorios |
| Suma de la columna correcta | test con 4 filas de importes reales |
| Encabezado alineado | declarado y descubierto |
| Anchos | columna de cantidad angosta, detalle ancha |
| Buscador | 8 casos: texto, tildes, sección, sin resultados, limpiar |
| Aislamiento de grillas | el test que destapó el bug de clase |
| **App real** | `compila.bat` y ejecutable en pantalla |
| Suite | **210 tests** (empezaban en 153) |

Herramientas nuevas:
  * `tools/render_tabla.py` — renderiza una grilla **con datos**. Las capturas
    anteriores mostraban tablas vacías, que es como nacen; con una tabla vacía no
    se puede ver si los importes se leen bien.
  * `tools/sembrar_stock.py` — siembra el sandbox con un catálogo de ferretería,
    mínimos, movimientos y un remito, para ver la venta y las tres pantallas de
    stock con datos de verdad. **Reemplaza a `cargar_productos_prueba.py`**,
    que queda como atajo que delega acá: los dos sembraban el mismo catálogo y
    corriendo ambos quedaban duplicados, con nombres iguales y códigos de barra
    distintos. El viejo además tenía un error de mapeo que guardaba el costo en
    la columna `concepto` (un float en un campo de un carácter), así que sus
    artículos no los marcaba el botón "Marcar productos" sin que se entendiera
    por qué.
  * `tools/probar_buscador.py` — prueba el filtro y deja la salida escrita.

---

## Pendientes

- [ ] Aplicar los tipos declarados a las otras tablas con importes, para que
      también se vean se vean con los decimales correctos (por ahora se
      descubren solos al cargar la primera fila, que ya es una mejora, pero en
      algunas tablas convendría declararlos).
- [ ] La fila vacía que la grilla deja al final de la tabla: es comportamiento
      viejo, se ve rara.
- [ ] Buscador en el resto de pantallas: con 30 tablas y muchos diálogos,
      buscar un cliente o un artículo a través de pantallas es el siguiente
      cuello de botella.
- [ ] **El rediseño de la pantalla de emisión** (issue #32), que necesita
      decidir primero cuál de las dos pantallas es la de emitir.
