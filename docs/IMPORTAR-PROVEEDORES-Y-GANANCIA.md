# Importar artículos: proveedores, escala de la ganancia y vista previa

## Qué se reportó

Tres cosas del operador, en este orden:

1. **"2900% de ganancia quedó"** en artículos importados.
2. **"Importé más de una vez la misma planilla, con errores entre medio,
   hasta que salió sin errores."**
3. Después: en la selección quieren **importar más de un proveedor según lo
   que figura en el Excel**, y una **forma más visual de ver lo que se está
   importando**.

Las tres salieron de dos planillas reales, no de casos imaginados.

---

## Las dos planillas

Se usaron las que trajo el operador, que están en su carpeta de Descargas y
no en el repo (los tests arman las suyas, para no depender de otra máquina).

| | `Importacion compuesta.xlsx` (ANYWAY) | `Importacion compuesta BOTZ.xlsx` |
|---|---|---|
| Filas con datos | 704 | 69 (de 15.686 filas: 15.616 vacías) |
| Proveedor | ANYWAY | GP |
| `GANANCIA` | **1.5** | **30** |
| `CODIGO DE BARRA` | sí | **no, la columna está vacía** |
| `IVA` | 0 | 21 |
| Nombres repetidos | no | sí: `6308` en las filas 59 y 60 |

### La columna GANANCIA no significa lo mismo en las dos

Ahí está el 2900%, y es la diferencia más importante entre ambos archivos:

- ANYWAY: `1.5` es un **multiplicador** → 50%.
- BOTZ: `30` es un **porcentaje** → 30%.

El código leía las dos como multiplicador: `(30 − 1) × 100 = 2900`. Con costo
4700 el precio salía **141.000** en vez de **6.110**.

La lectura automática corta en **5**: un multiplicador de 5 ya es un markup del
400%, que no existe en una lista de precios, mientras que un porcentaje de 30 es
lo más común que hay. En la zona de confusión manda la lectura que produce un
número de negocio.

---

## Los cuatro cambios

### 1. La escala de la ganancia se detecta sola

`_porcentaje_de_ganancia()` ahora decide por archivo, y hay una función
`escala_ganancia(registros)` que devuelve `"porcentaje"`, `"multiplicador"` o
`"mixta"`. La vista previa muestra cuál se detectó.

### 2. Cada fila va con el proveedor que dice su fila

**CAMBIO DE REGLA.** Antes la columna PROVEEDOR se leía y se tiraba: todos los
artículos quedaban con el proveedor del desplegable, así que una planilla
compuesta entraba con el catálogo entero mal atribuido.

Ahora manda el nombre de la fila, buscado entre los proveedores ya cargados y
normalizado (`"Nordeste"`, `"NORDESTE "` y `"NOR DESTE"` son el mismo).

**Lo que NO cambió y no tiene que cambiar:** no se crea un proveedor que no
exista. El nombre viene en texto libre de otro programa, y "NORDESTE S.R.L." al
lado de un "NORDESTE" ya cargado dejaría dos proveedores para el mismo. Cuando
el nombre no está, la fila usa el proveedor del desplegable **y el resumen lo
avisa**, porque si no el catálogo queda atribuido a un proveedor que el archivo
nunca nombró.

### 3. Reimportar ya no mueve artículos

Este era el "importé hasta que salió sin errores". Sin código de barras, cada
fila genera un código interno, y el índice en memoria guardaba `None` en vez del
id del artículo recién creado:

```python
por_codigo.setdefault(codigo, None)      # antes
por_codigo[codigo] = nuevo.idarticulo    # ahora
```

Como el código generado no se reutilizaba, en la vuelta siguiente se generaba
otro con sufijo (`INT607ZZ` → `INT607ZZ-2`), el artículo se encontraba igual por
nombre, lo actualizaba y le cambiaba el código. Cada vuelta movía un artículo
más. ANYWAY ahora da `sin_cambios=704` en las dos reimportaciones.

### 4. No se borra el código de barras al reimportar

El más grave, y apareció al arreglar el anterior. Al invertir el orden (generar
el código solo en la alta), una fila sin código dejaba al artículo existente con
`codbarra = ''`: **perdía su EAN y dejaba de poder cobrarse con lector**. Con una
planilla como la de BOTZ, que no trae esa columna, le pasaba a todos los
artículos con EAN.

Ahora, si la fila no trae código, se conserva el que el artículo ya tenía.

---

## La vista previa

`libs/importararticulos.py::previsualiza()` calcula qué va a pasar **sin
escribir nada**, y la pantalla lo muestra en una grilla antes del botón
Importar:

| Fila | Código | Nombre | Proveedor | Costo | Ganancia % | Precio | Estado |
|---|---|---|---|---|---|---|---|
| 2 | INT607ZZ | 607 ZZ | GP | 4.700,00 | 30,00% | 6.110,00 | nuevo |

Las filas que no entran van en el color de error del tema. Los avisos van
**encima**, en rojo, antes de importar:

> La columna GANANCIA trae PORCENTAJES: se leyó como 30% y no como
> multiplicador. ATENCION: 1 nombre(s) se repiten y no hay código de barras
> para distinguirlos, así que el último costo pisa al anterior: **6308 (filas
> 59, 60)**. 69 filas en la planilla, 69 se van a importar.

Es la forma en que los dos errores se vuelven visibles: en el resumen final
decían "69 artículos importados" como si todo estuviera bien, porque lo estaba
— con el precio mal.

---

## Verificación

Para probar la pantalla hay que armar el **controlador**, no la vista suelta:
`ConectarWidgets` lo llama el controlador, y armar la vista a mano se saltean
todas las señales. Diagnosticarlo al revés dio "la grilla no anda" cuando en la
app anda perfecto — el mismo error que el fixture que simulaba mal al operador,
del otro lado.

| Qué | Cómo |
|---|---|
| Los 3 bugs, contra las 2 planillas reales | `tools/_diag_bug_reexport.py` (ya borrado) |
| Reimportación estable | vuelta 2 y 3 dan `sin_cambios=704` |
| EAN conservado | test que falla si se borra |
| 13 tests nuevos | `tests/test_importar_proveedores_y_ganancia.py` |
| Verificado contra el código roto | 10 de 13 fallan con `2900.00 == 30` y `1 == 2` |
| Suite completa | 872 tests |

### Dos tests viejos que afirman lo contrario

- `test_el_proveedor_es_el_que_se_eligio` decía que la columna del archivo NO
  manda. Se dio vuelta y ahora es `test_el_proveedor_es_el_de_la_fila_si_esta_cargado`,
  con el cambio de regla escrito en el docstring. El caso del nombre
  desconocido se sigue cubriendo aparte.
- `test_el_codigo_generado_no_se_repite` pedía dos códigos para dos filas con el
  mismo nombre. Sin código de barras el nombre es la única clave, así que dos
  filas iguales son el **mismo** producto con dos costos: la segunda actualiza a
  la primera. Pedir dos artículos era crear un duplicado. Ahora se prueba el caso
  que ese test cubría sin verlo: dos productos **distintos** con nombres que
  arrancan igual y se truncan al generar el código.

---

## Dos incidentes que costaron tiempo, y por qué importan

### Un crash de Qt sin traceback

`pytest tests/test_pantallas_del_menu.py` moría con:

```
Windows fatal exception: access violation
exit -1073741819 (3221225477)
```

**Sin traceback, sin exception de Python, sin decir qué línea.** Y pasaba al
hacer `resize()`, no al crear el widget.

La causa fue poner las cabeceras como atributo de instancia:

```python
self.grillaPrevia.cabeceras = ["Fila", "Código", ...]     # MAL
```

`Grilla` define `cabeceras = []` como **atributo de clase**, compartido entre
todas las grillas del proceso. Puestas en la instancia no se usan:
`ArmaCabeceras()` sin argumento lee la de clase, y la grilla maqueta con una
lista de columnas que no es suya. Lo correcto, como en `vistas/Stock.py`:

```python
self.grillaPrevia.enabled = True
self.grillaPrevia.ArmaCabeceras(cabeceras=[...])   # por parámetro
```

Y `ArmaCabeceras()` **una sola vez**, en `setupUi`: llamarlo en cada repintado
reinicia las cabeceras y vuelve a la lista compartida.

**Un crash de Qt sin traceback no es un problema de Qt: es memoria mal usada
por un widget.** Para encontrarlo hay que aislar por archivo (correr cada
`test_*.py` por separado), porque el crash depende del estado del proceso y la
suite completa no dice nada.

### `git stash pop` cruzó dos archivos

Al verificar los tests contra el código viejo, un `stash pop` sobrescribió
`libs/importararticulos.py` con el contenido de `vistas/ImportarArticulos.py`.
Los dos archivos tienen el mismo prefijo, y el pop no aviso nada.

Se vio por el sintoma: 43 tests con `AttributeError: module
'libs.importararticulos' has no attribute 'leer_filas'`. Un `AttributeError`
de "el modulo no tiene X" cuando X existe, no es un bug del modulo: **alguien
tiene otro archivo**.

La parte cara: el `.pyc` de `__pycache__` era de la version rota, asi que no
habia de donde recuperar. Hubo que reescribir la libreria entera.

**Por eso ahora se commitea antes de verificar contra el codigo viejo.** Un
`stash` de trabajo sin commitear es trabajo que un `pop` puede pisar sin avisar.

---

`v.show()` en modo `offscreen` mata el proceso con un access violation de Qt
(3221225477). No es este código. Para probar la pantalla hay que armar el
**controlador**, no la vista suelta: `ConectarWidgets` lo llama el controlador, y
armarla a mano saltea todas las señales. Diagnosticarlo así dio "la grilla no
anda" cuando en la app anda perfecto — el mismo error que el fixture que
simulaba mal al operador, del otro lado.

---

## Pendientes

- [ ] **`escala_ganancia` es por archivo, no por fila.** Si un mismo Excel
      mezclara porcentajes y multiplicadores (`"mixta"`), avisa pero calcula
      igual. Se detectó el caso pero no se resolvió.
- [ ] **Los nombres repetidos se avisan, no se resuelven.** `6308` aparece dos
      veces con costos 29.070 y 2.000 y el último gana. Hace falta que el
      operador decida; la app no puede saber si son el mismo producto con dos
      precios o dos productos distintos con el mismo nombre.
- [ ] **`proveedores_no_encontrados` no crea el proveedor.** Si el archivo trae
      un proveedor nuevo, hay que cargarlo en el ABM y reimportar. Podría
      ofrecer hacerlo desde la vista previa.
- [ ] **`previsualiza` corta en 500 filas.** Con una planilla de 3.000 solo se
      ven las primeras 500, aunque el resumen cuenta todas. La grilla no dice
      "y 2.500 más".
- [ ] **`buscar_articulo` del ABM sigue usando `contains()`** y no el buscador
      normalizado, así que hay dos criterios de búsqueda distintos en el
      producto. Ver `docs/BUSQUEDA-CLIENTES.md`.