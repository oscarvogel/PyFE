# Buscar clientes: por qué con tres andaba y con miles no

Fecha: 2026-10-03
Alcance: `libs/busqueda.py` (nuevo), `controladores/VentaSimple.py`,
`vistas/VentaSimple.py`, `vistas/Busqueda.py`, `vistas/ABM.py`, `vistas/Main.py`.
Cómo se pidió: "para tres clientes anda esto, pero si tenemos miles ¿cómo se
busca?" — con la captura del diálogo *Seleccionar cliente* escribiendo "muni".

---

## La respuesta corta

Antes, con miles de clientes **no se podía buscar**: la consulta no tenía tope
y el diálogo no tenía buscador. Escribías algo, salía **todas** las
coincidencias en una lista que no se podía filtrar, y para acotar tenías que
cerrar el diálogo y volver a escribir desde la venta. Con tres resultados se
ve bien; con 800 es una pantalla muerta.

---

## Qué se hacía antes

```python
#Vj.controller.VentaSimple.buscar_clientes
return list(Cliente.select().where(Cliente.nombre.contains(texto)).order_by(Cliente.nombre))
```

Tres cosas mal, todas verificadas contra la base real (57 clientes):

### 1. Sin tope

`list(...)` sin `limit()` trae todas las coincidencias a memoria y el diálogo
las volcaba una por una. Buscando una letra ("a") en la base real ya son **49
clientes**; con 5.000 serían cientos. Y no había forma de seguir acotando desde
ahí.

### 2. El diálogo no tenía buscador

`VentaSimpleSeleccionClienteDialog` recibía la lista **ya armada** y la
mostraba. Sin caja de texto no había forma de refinar: era un callejón sin
salida.

### 3. Las tildes dependían del motor de base

`campo.contains(texto)` compila a `LIKE '%texto%'`, y el `LIKE` no se porta
igual en SQLite (el sandbox) y en MySQL (producción). Con la collation de
MySQL las tildes cuentan, y en SQLite también.

Medido sobre la base real, mismo texto, antes y ahora:

| Se escribe | Antes | Ahora |
|---|---|---|
| `dona` | **0 resultados** | 1 → TRANS. DOÑA ELENA |
| `DONA` | **0 resultados** | 1 → TRANS. DOÑA ELENA |
| `ñ` | **0 resultados** | **37** |
| `muni` | 3 | 3 |

**37 de los 57 clientes de tu base eran inbuscables con la palabra "ñ"**, que
es el segundo cliente de la lista. El más grave no es que no encuentre: es que
"no lo encuentra" se lee como "el cliente no está cargado", y ahí el operador
da de alta un cliente que ya existía.

---

## Qué se hizo

### Un solo criterio de búsqueda, para toda la app

`libs/busqueda.py` (nuevo) tiene `normalizar()`, `sin_tildes()` y `contiene()`.
El texto se pasa a minúsculas y sin tildes en Python, y del lado de la base se
aplica lo mismo con `REPLACE`, que existe en los dos motores. Sin tocar el
esquema.

Se usa en los cuatro lugares donde se busca texto:

| Dónde | Antes |
|---|---|
| `VentaSimpleController.buscar_clientes` | `nombre.contains()` |
| `UiBusqueda` (la ventana de F2) | `campoBusqueda.contains()` |
| `ABM.ArmaTabla` (la lista de los 12 ABM) | `ordenBusqueda.contains()` |
| `MainView._filtrar_lateral` | tenía su propia copia de la normalización |

Ese último ya funcionaba bien: la barra lateral de la app ignoraba tildes
desde antes. **Lo que no podia pasar era que la barra acepta "configuracion" y
el buscador de clientes no.** Ahora las dos usan el mismo criterio, y la copia
duplicada se fue.

### El diálogo became un embudo

- **Tiene buscador propio**, que vuelve a consultar a la base. Se acota
  escribiendo, sin cerrar.
- **Trae un tope de 100** (`LIMITE_BUSQUEDA_CLIENTES`).
- **Dice cuántos hay en total**: "Mostrando 100 de 171 coincidencias. Seguí
  escribiendo para acotar." Sin ese número, ver 100 filas no dice si falta nada
  — y el operador cree que ya los vio a todos.
- **Texto vacío no vuelca la tabla**: dice "Escribí para buscar entre los
  clientes". Meter 5.000 filas en una lista no es una búsqueda.
- **Enter elige el de arriba**, sin llegar al mouse.

### Código, CUIT y DNI siguen siendo exactos

Eso no se tocó a propósito. Un `contains` sobre el CUIT devolvería *cualquier*
cliente que comparta los primeros dígitos: en una venta, elegir al cliente
equivocado. El nombre sí es búsqueda difusa; el documento no.

---

## Bugs que aparecieron de paso

### El buscador F2 declaraba un `limite` que nunca usaba

`UiBusqueda` tenía `limite = 100` desde siempre y no lo aplicaba. Peor: contaba
las filas con `setRowCount(len(rows))`, y **`len()` de una consulta de peewee la
ejecuta entera** — todas las filas a memoria, en cada tecla.

### Pasar un campo de peewee mataba la app entera sin dejar traza

`CargaDatos` hacía `self.campos[col].capitalize()`. Los que llaman hoy pasan
nombres (`['idcliente', 'nombre']`), y un `str` tiene `.capitalize()`, así que
nunca se rompió. Pero un campo de peewee **no** tiene ese método, y pasarlos
—que es lo natural— lo revienta.

Lo importante es *cómo* revienta: `CargaDatos` corre dentro del slot de
`textChanged`, y **una excepción dentro de un slot de Qt no se muestra: PyQt5
aborta el proceso entero sin dejar traza**. Por eso este bug se va a acordar
tarde si no se sabe. Ahora `campos` acepta los dos formatos.

### Un test que pasaba sin cubrir nada

`test_cliente_no_encontrado_propone_alta_y_lo_carga` parcheaba
`buscar_cliente` (en singular), un método **que no lo llama nadie**. El
`monkeypatch` no tenía efecto, y el test pasaba porque la base real no tiene un
cliente llamado "Cliente nuevo". Parecía cubrir el camino de "no encontrado" y
no lo cubría: si el método hubiera empezado a llamarse, el test seguía en verde.

Se parchea ahora el método que sí se usa. El método muerto se borró.

---

## Verificación

| Qué | Cómo |
|---|---|
| 1200 clientes, no 57 | base en memoria: con la base real el recorte no se vería |
| El tope se respeta | `super` → 100 filas de 171 |
| El total se avisa | el contador del diálogo |
| Se acota sin cerrar | test del diálogo: escribe, baja de 100 a 1, elige |
| Texto vacío no vuelca la tabla | contador con el aviso |
| Tildes, mayúsculas y ñ | 3 tests contra la base en memoria |
| CUIT con y sin guiones | sobre la base real, que los tiene mezclados |
| CUIT parcial no matchea | `3067` → 0 resultados, a propósito |
| F2 respeta el límite | 100 filas de 199 |
| F2 acepta campos y nombres | los dos formatos |
| La barra y la base normalizan igual | test cruzado |
| Base real | 57 clientes, 8 búsquedas, antes/después de cada una |
| Suite | **304 tests** (289 antes, 15 nuevos) |

---

## Pendientes

- [ ] **La búsqueda por nombre recorre la tabla.** Con 5.000 clientes va bien;
      con 500.000 filas de otra tabla, no. La solución de verdad es una columna
      `nombre_busqueda` con el texto ya normalizado, que además se indexa y
      permite acotar por prefijo. Es un cambio de esquema con migración, así
      que no se hizo acá.
- [ ] **La búsqueda de productos tiene el mismo problema** que tenía el de
      clientes: `buscar_articulo` sigue usando `contains()`, así que los acentos
      en la descripción no se encuentran. No se tocó porque el diálogo de
      artículos es otro flujo y conviene revisarlo aparte.
- [ ] **`Consumidor Final` tiene el CUIT guardado como `'0'`**, no como cadena
      vacía. No rompe nada (el diálogo cae al DNI cuando el CUIT viene en
      ceros), pero ensucia la base.
- [ ] **Los ABMs muestran 100 filas sin avisar** (`ABM.limite = 100`). Ahora sí
      dicen cuántas hay, pero el buscador está en la grilla, no arriba: con
      muchos clientes hay que escribir para acotar.
- [ ] **Sin índice**: mientras la búsqueda sea un recorrido, escribir "a" en
      una tabla grande se va a notar.
