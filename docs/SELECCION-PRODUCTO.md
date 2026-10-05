# Elegir el producto, no que lo elijan por el operador

## Qué se reportó

Con dos artículos cuyos nombres arrancan igual — dos
`WHEY CUTTER 1080G PROTE+QUEMADOR SPX VAINILLA/...`, que después se
diferencian en el sabor (AMERICAN CREAM / FRUTILLA BOLSA) — escribir una
parte del nombre tomaba el primero y listo.

Las dos capturas del reporte:

1. **Diálogo "Seleccionar producto"**: escribiendo `w` ya aparecían las dos
   filas con la primera marcada. Presionar Enter (o Aceptar) se la llevaba.
2. **Campo "Producto"**: escribiendo `wh` y apretando Agregar, se agregaba
   uno de los dos sin preguntar, y el operador nunca veía la lista.

## Por qué pasaban las dos

Eran dos caminos distintos, y por eso hubo que tocar dos lugares:

| Camino | Qué hacía | Por qué elegía al primero |
|---|---|---|
| `VentaSimpleSeleccionArticuloDialog.buscar` | `setCurrentRow(0)` en **cada tecla** | Con 2+ coincidencias, la fila 0 quedaba marcada al escribir |
| `VentaSimpleSeleccionArticuloDialog._aceptar_primero` | `if currentRow() < 0: setCurrentRow(0)` | Enter sin nada marcado forzaba la fila 0 |
| `VentaSimpleController.buscar_articulo` | `.contains(busqueda).first()` | El campo de producto tomaba el primero de la base |

El tercero es el peor de los tres: el operador no ve la lista, así que no
tiene forma de saber que se eligió por él.

## Qué cambió

La regla nueva es una sola:

> Con **una** coincidencia se elige sola. Con **dos o más**, no se elige
> nada: el operador tiene que marcar la fila.

### `vistas/VentaSimple.py`

- `buscar()` ya no hace `setCurrentRow(0)` cuando hay más de una
  coincidencia. Solo marca cuando la lista tiene exactamente un elemento.
- El contador ahora dice `"N coincidencias. Elegí una con las flechas o el
  mouse."` en vez de solo `"N coincidencias"`. Sin ese aviso, el texto viejo
  parece un resultado y no una decisión pendiente.
- `_aceptar_primero()` pasó a llamarse `_elegir_para_entrar()` y ya **no**
  marca la fila 0: sin nada marcado, Enter no hace nada.
- `accept()` exige una fila válida. Con varias coincidencias y nada
  marcado, Aceptar no cierra el diálogo.

Lo mismo se aplicó a `VentaSimpleSeleccionClienteDialog`: dos
"MUNICIPALIDAD DE..." dan el mismo problema, y cobrarle al cliente equivocado
es peor que agregar el producto equivocado.

### `controladores/VentaSimple.py`

`agregar_articulo()` consulta `_articulo_es_ambiguo()` antes de agregar.
Si lo escrito coincide con dos o más artículos, **no** llama a
`buscar_articulo`, sino que abre el catálogo ya acotado a la búsqueda para
que el operador elija.

Si el operador cancela, no se agrega nada. Antes el fallback era el primero.

`_articulo_es_ambiguo()` pide solo 2 (`limite=2`) y viene con
`try/except`: si no se puede contar, se sigue como antes. Agregar el
producto es menos grave que dejar al operador sin poder cargar la venta.

## Verificación

Los tests están en `tests/test_venta_seleccion_explicita.py` (12 tests).

**Verificados en las dos direcciones.** Contra el código viejo
(`git stash`), 7 de los 12 fallan con el síntoma exacto:

```
AssertionError: Enter sin nada marcado cerro el dialogo: se llevo <_Articulo object ...>
AssertionError: con 2 coincidencias quedo algo marcado automaticamente (fila 0).
AssertionError: con 2 productos que empiezan igual no se abrio el catalogo: quedaron 0 pedidos de selector
AssertionError: con 2 clientes parecidos quedo el primero marcado solo
```

Los 5 que pasan contra el código viejo son los que anclan lo que **no**
tenía que cambiar: que con una sola coincidencia se siga eligiendo sola, y
que cancelar no agregue nada.

Un detalle sobre esa verificación: los tests que aprietan Enter usan
`QTest.keyClick` y no llaman al handler interno a propósito. La primera
versión llamaba `dialogo._elegir_para_entrar()` y contra el código viejo
moría con `AttributeError`, que dice "le falta un método" y no "el operador
estuvo a punto de cargar el producto equivocado". Un fallo que no es el
síntoma no verifica nada.

## Archivos tocados

| Archivo | Qué |
|---|---|
| `vistas/VentaSimple.py` | Los dos diálogos: sin preselección con varias coincidencias |
| `controladores/VentaSimple.py` | `agregar_articulo()` consulta la ambigüedad antes de elegir |
| `tests/test_venta_seleccion_explicita.py` | Nuevo, 12 tests |

## El cuelgue queupidió el cambio

Los tests de `test_venta_simple_selector.py` se quedaron colgados después
del arreglo, y no fue un problema de tiempo: el diálogo modal ya no cerraba
jamás.

La causa estaba en el fixture, no en el código de producción:

```python
def exec_(self):
    QTimer.singleShot(60, self.accept)   # "el operador acepta"
```

El fixture simula al operador **saltándose el paso de elegir**. Con el
código viejo `accept()` tomaba la fila 0 por su cuenta y cerraba, así que
funcionaba. Con el arreglo, `accept()` sin nada marcado no cierra, y el
`QTimer` se quedaba sin efecto para siempre: el test esperaba un cierre que
no llegaba.

Se corrigió el fixture para que marque la fila antes de aceptar, que es lo
que hace una persona:

```python
def elegir(self):
    if self.listaClientes.currentRow() < 0 and self.listaClientes.count():
        self.listaClientes.setCurrentRow(0)
    self.accept()
```

Vale la pena dejarlo anotado: **un test que cuelga es información**. Acá
decía "tu fixture simula mal al operador", no "el código nuevo está roto" y
esa distinction es la que decide dónde mirar.

## Pendientes

- [ ] **Falta el equivalente para `cargar_cliente_desde_busqueda`.** El
      diálogo ya no elige solo, pero el camino de `textCliente` sigue
      llamando a `buscar_clientes()` y tomando el primero. Con dos clientes
      parecidos el operador ve el selector en vez de ver el error, así que el
      síntoma es menos grave, pero el camino sigue existiendo.
- [ ] **Los selectores de otros módulos pueden tener el mismo patrón.**
      Se corrigieron los dos de `VentaSimple` porque son los que el operador
      usa al cargar una venta. No se revisaron los de otros ABMs.
- [ ] **`_articulo_es_ambiguo` suma una consulta.** Con `limite=2` es
      barata, pero es una más en el camino de agregar. Si se nota en un
      catálogo grande, se puede cachear por texto.
- [ ] **`buscar_articulo` sigue usando `contains()`**, así que los acentos
      en la descripción no se encuentran. Era un pendiente previo
      (`docs/BUSQUEDA-CLIENTES.md`) y sigue igual: `_articulo_es_ambiguo`
      usa `_coincidencias_articulo`, que sí normaliza. O sea que ahora las
      dos consultas pueden no coincidir entre sí.