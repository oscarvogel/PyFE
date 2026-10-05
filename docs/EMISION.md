# La pantalla de emisión

`vistas/Facturas.py` y `controladores/Facturas.py`. Cómo está armada, por
qué está así, y qué contratos no se pueden tocar.

---

## Qué cambió

**Tres columnas, y cada una contesta una pregunta distinta:**

```
izquierda   QUÉ  se está emitiendo      tipo, fecha, conceptos, período
centro      QUÉ  se está vendiendo      los renglones
derecha     CUÁNTO sale y CÓMO terminó  los totales y el CAE
```

Antes era todo del mismo peso, en el mismo orden de arriba hacia abajo, con
la misma caja. No había forma de ver de un vistazo qué parte llena el
operador y cuál es el resultado.

**El cliente arriba, con el nombre como titular.** El nombre del cliente es lo
primero que hay que confirmar de que se está facturando a la persona correcta,
y era una `Etiqueta` más al lado del campo de código.

**Los totales son etiquetas alineadas a la derecha, no campos de formulario.**
Eran cuatro `EntradaTexto` deshabilitados con etiquetas de 10 px. El Total,
que es lo único que el operador viene a ver, no se distinguía de los otros
tres.

**El CAE es el dato principal cuando la factura está autorizada.** Antes eran
tres campos de texto deshabilitados en un grupo gris abajo a la izquierda, al
lado del botón Emitir, y había que ir a buscarlos. Ahora el número, el CAE en
monoespaciado y el vencimiento van juntos arriba a la derecha, con el estado
("Sin autorizar" / "Autorizada" / "Rechazada") en la cabecera de la ventana.

**El período facturado solo aparece con Factura C.** Con Factura A o B no hay
período que informar, y antes ocupaba el mismo lugar que los conceptos con dos
de las tres fechas deshabilitadas.

**La acción principal es un botón, no media pantalla.** "Emitir factura",
después "Imprimir" y "Nueva factura". Antes Emitir y Cerrar ocupaban la mitad
del ancho cada uno, con el mismo peso.

---

## Los contratos que no se tocan

`controladores/Facturas.py` tiene **154 referencias a `self.view.*`** sobre 30
atributos, y once archivos de test los usan. Por eso esto es una
reorganización y no un rediseño desde cero: ningún atributo cambió de nombre.

`gridFactura` es el más delicado. `GrabaFE` la lee por **nombre de columna**:
`"Cant."`, `"Codigo"`, `"Detalle"`, `"Unitario"`, `"IVA"`, `"SubTotal"`. Los
nombres se pueden cambiar, pero solo actualizando `GrabaFE` en el mismo
commit.

`tools/verificar_contrato_vistas.py` recorre los pares controlador/vista y
dice qué atributos faltan. Correlo antes de tocar una vista con 30
referencias colgando: sin él, un atributo que falta no se entera nadie hasta
que el operador llega a esa parte de la pantalla.

---

## Los totales se guardan dos veces

`EntradaTexto.value()` devolvía un float **con cultura** (1234.5), mientras
que lo que se veía era "1234.50". El número que se guardaba en `cabfact` y el
que se mostraba eran dos números distintos escritos de dos maneras.

Ahora:

- `view.total_iva`, `view.total_subtotal`, `view.total_tributos`,
  `view.total_final` son **números**, y el controlador los usa para guardar la
  cabecera.
- Las etiquetas son solo lo que se ve, y las formatea `ActualizaTotales()`.

Lo mismo con el vencimiento del CAE: `vencimiento_cae` es "14/10/2026" (lo
que se ve) y `vencimiento_cae_sql` es "20261014" (lo que se guarda). Antes
estaba en un `Fecha` de Qt con un formato de entrada y otro de salida.

---

## Leer los números de la grilla

La grilla guarda el número aparte del texto (`UserRole`) y `ObtenerItem` lo
devuelve crudo, así que nunca se parsea el texto. **Salvo cuando el operador
edita la celda**: Qt reemplaza el item por uno nuevo que solo tiene el texto,
y ese texto va con separador de miles y coma decimal.

Ahí `float("500,00")` reventaba con un `ValueError` y una ventana de error
que no decía qué celda lo había causado. Por eso:

- Todo número que sale de la grilla pasa por `FacturaController._a_numero()`.
- Al confirmar con Enter o Tab, `_normaliza_celda()` vuelve a escribir la
  celda por `ModificaItem` para que recupere el número crudo.

`tests/test_emision_numeros.py` cubre los dos caminos.

---

## Un detalle que se ve en la captura

La grilla de artículos **debe declarar sus formatos**. Sin ellos, `Unitario` y
`SubTotal` no son columnas de importe para la grilla y se reparten como texto
corto, con el número pegado al borde. Y con los formatos puestos, la pantalla
necesita 1340 px: con menos, las cinco columnas fijas se comen el ancho de la
grilla y "Detalle" —que es la que el operador lee— queda de 30 px.

`Grilla.columna_preferida` dice qué columna de texto se lleva el sobrante. En
la grilla de la factura es "Detalle"; sin eso ganaba la de nombre más largo y
el reparto era proporcional a la longitud del encabezado, que no es lo mismo.
