# Caracteres que la fuente no tiene, y el PDF que se escribia igual

Fecha: 2026-10-05
Rama: `master`
Estado: **implementado y verificado.** No publicado: la version que esta
instalada en `C:\fe` es la `2026.10.05.13.15.58`, que todavia no tiene esto.

## Que se vio

La factura `000300000459` no se imprimia. En el log de `C:\fe\all.log`:

```
ERROR - ProcesarPlantilla fallo para la factura 000300000459:
fpdf.errors.FPDFUnicodeEncodingException: Character "–" at index 63 in text
is outside the range of characters supported by the font used: "helvetica".
Please consider using a Unicode font.
```

Y en `C:\fe\facturas\` quedaba un archivo de **21.517 bytes** al lado de
facturas de verdad que pesan **940.000**. Al abrirlo no habia una factura mal
impresa: habia una hoja con `Excepcion FPDFUnicodeEncodingException:1018` en
rojo y **todos los campos vacios**, con el numero `0000-00000000` y la fecha en
blanco. El 1018 es el numero de linea dentro de `pyafipws/pyfepdf.py`.

## De donde salia el caracter

No de la plantilla. `plantillas/factura.csv` es **100 % ASCII**, byte a byte, y
tambien `factura_qr.csv`, `factura-fce.csv`, `recibo.csv` y `remito.csv`.

El indice del error es la pista: "index 63" es la posicion dentro del **texto
que se estaba escribiendo**, o sea un valor de dato. Era el `descad` del unico
renglon de la 459:

```
"Servicios de desarrollo y mejoras del sistema de logística RND – Septiembre 2026."
                                                                       ↑
                                                          en dash U+2013, posición 63
```

Recorridas las 538 descripciones de `detfact` y los 20 clientes, la 459 es la
**unica** con un caracter por encima de U+00FF. Los clientes estan bien:
`FUNDACIÓN ALFA` y `Instituto Privado de Alta Capacitación` llevan `Ó` y `ó`,
que estan en latin-1 y se imprimen sin problema.

## Por que explota

Las plantillas de comprobante usan **core fonts** (helvetica, courier, times),
que cubren latin-1 y nada mas. En fpdf2 2.8.7, `fpdf/fpdf.py:5675`:

```python
def normalize_text(self, text: str) -> str:
    if not self.is_ttf_font and self.core_fonts_encoding:
        try:
            return text.encode(self.core_fonts_encoding).decode("latin-1")
        except UnicodeEncodeError as error:
            raise FPDFUnicodeEncodingException(...)
```

**Con fpdf 1.7.2 esto no pasaba**: el mismo caracter salia como un cuadrito de
reemplazo, en silencio. De ahi el commit `e3ba08d`, "el pie del comprobante
salia con caracteres de reemplazo". El salto a fpdf2 no introdujo el bug: **lo
destapo**. Cuando una mejora "rompe" algo que antes andaba mal, la pregunta no
es que se rompio, sino que dato invalido estaba aguantandose.

## Los tres defectos, encadenados

### 1. `pyafipws/pyfepdf.py:1617` — el fallo se convierte en parte del documento

`ProcesarPlantilla` captura la excepcion **y sigue pintando**: agrega una hoja
a la misma plantilla con el traceback (escrito en `%TEMP%\traceback.txt`) y una
linea roja con `Excepcion <nombre>:<linea>`. Despues `finally: return ret`
devuelve `False` sin relanzar.

O sea: la plantilla queda con la pagina de error pegada y los campos sin llenar.

### 2. `controladores/Facturas.py` — se escribia igual

Despues de loguear el `False`, el codigo **no cortaba**: llamaba a
`GenerarPDF(salida)`, que renderiza esa plantilla a medias y la escribe encima
de `facturas/FACTURA_C-000300000459.pdf`.

### 3. `_pdf_generado` — se reportaba exito

El unico chequeo era si el archivo se escribio (`if ok: return True`). Como se
escribio, la app **no avisaba nada** y le abria ese PDF al operador creyendo
que era la factura.

El costo real: si la letra que rompio el render hubiera estado en una factura
**ya impresa**, al reimprimir le habria pisado el comprobante bueno. Y una
factura autorizada en ARCA no se puede volver a emitir, asi que ese archivo
anterior era el unico que existia. En la 459 no se perdio nada porque es de ese
dia y nunca se habia impreso.

## Que se cambio

| Archivo | Que |
|---|---|
| `libs/fpdf_compat.py` | `transliterar()`: cambia lo que la fuente no tiene **al escribir**, no en la base. Shim sobre `FPDF.normalize_text`, que es el unico punto por donde pasa todo el texto. |
| `controladores/Facturas.py` | Nuevo `_renderizar_y_escribir()`: si el render falla, no escribe nada y avisa con el CAE. |
| `tests/test_pdf_unicode.py` | 32 tests. |
| `tests/test_pdf_bloqueado.py` | El test de la escritura a temporal apunta ahora al metodo nuevo. |

### Por que el shim y no arreglar el dato

La descripcion guardada queda con su en dash, que es lo que dice el dato, y lo
unico que cambia es el glifo impreso. Touchar la base seria peor: un
comprobante ya autorizado tiene su descripcion registrada en ARCA, y cambiarla
localmente deja las dos copias distintas. Los acentos y demas caracteres de
latin-1 **no se tocan**: salen bien, y `transliterar` solo toca lo que la fuente
no tiene.

Se sustituye por el equivalente mas cercano: guiones y rayas a `-`, comillas
tipograficas a `'` y `"`, ellipsis a `...`, y para lo que no tiene equivalente se
intenta la descomposicion NFKD (`Ā` -> `A`, `ﬁ` -> `fi`). Si no queda nada
imprimible, un `?`: un caracter ilegible es preferible a una excepcion, porque
la excepcion deja al comprobante sin imprimir.

Cada caracter sustituido se avisa **una sola vez por proceso** al log. Con core
fonts una factura escribe cientos de textos, asi que un aviso por llamada
llenaria `all.log` de lo mismo.

Con una fuente TTF no se sustituye nada: ahi no hay problema, y cambiar el texto
de un comprobante que se puede imprimir bien no tendria sentido.

### Por que `normalize_text` y no los datos del comprobante

Es el unico punto por donde pasa **todo** el texto (empresa, cliente, domicilio,
descripciones, observaciones, CUIT) y funciona con cualquier plantilla, propia o
descargada. El shim usa `functools.wraps` con `*args, **kwargs`, no una firma
copiada: si fpdf2 cambia los argumentos, sigue andando.

## Como se verifico

**Primero el test, despues el arreglo.** Y el test se corro contra el codigo
roto antes de darlo por bueno:

1. Contra `HEAD` (los dos archivos sin el arreglo): **29 de 32 fallan**.
2. Con el metodo puesto pero **sin el `return`** del corte, o sea el
   comportamiento viejo exacto: los 3 tests de comportamiento del corte fallan
   con las aserciones correctas, y una de ellas dice literalmente
   *"el comprobante bueno se perdio"*. Un test que solo mirara que el metodo
   existiria habria dado verde con el bug puesto.
3. Con el arreglo: **32 verdes**.

Los tests arman PDFs de verdad con fpdf2, no dobles: `FPDF().multi_cell()` y un
`Template` con `elements=` (el camino de `pyfepdf`). El camino del `Template`
reventaba con `FPDFUnicodeEncodingException` sin el shim, y ese mismo camino es
el que se prueba.

Ademas `test_el_shim_acepta_la_llamada_real_de_la_libreria` hace
`inspect.signature(type(pdf).normalize_text).bind(pdf, "un texto")` contra un
`FPDF` de verdad: la firma que se prueba es la de la version instalada, no una
copiada de memoria.

## Detalles de fpdf2 2.8.7 que Costaron tiempo

- **`Template(infile=...)` esta deprecado e ignorado** desde 2.2.0. Con solo la
  ruta, la plantilla queda vacia. El camino que usa `pyfepdf` es
  `Template(elements=...)`.
- **Las claves del elemento son `x1/y1/x2/y2`**, no `x/y/w/h`:
  `load_elements` tira `KeyError`.
- **`background` no acepta `None`**: es `TypeError`, tiene que ser un entero.
  Ojo, porque `fpdf_compat` pone `None` a proposito en los fondos heredados
  (para no pintar la pagina negra) y ese `None` es para `elements`, no para el
  constructor.
- **`wrapmode='R'` ya no es valido.**
- **`is_ttf_font` es una property de solo lectura.** Para probar que con una
  fuente Unicode no se toca el texto hay que cargar una TTF de verdad
  (`C:\Windows\Fonts\arial.ttf`), no cambiar el flag a mano.
- **DeprecationWarning: "Substituting font arial by core font helvetica"** en
  cada render. Es la confirmacion de que la plantilla cae en un core font, que
  es justo donde rompe.

## La trampa del `REGEXP` de MySQL

Para medir el alcance se quiso filtrar con
`WHERE descad REGEXP '[\\x{0100}-\\x{FFFF}]'`. **MySQL no soporta escapes
`\x{}`**: el patron se interpreta como un conjunto de caracteres raros y
devolvió **533 filas de 538**, o sea casi todo. Parecia que habia 533
comprobantes rotos.

La forma que no miente es filtrar en Python recorriendo `ord(c) > 255`. Con eso
salio que hay **una sola** descripcion afectada. Cuando un filtro de base de
datos devuelve de mas, el numero que se reporta es peor que no reportar nada.

## Que falta

1. **Publicar.** La version instalada en `C:\fe` es la
   `2026.10.05.13.15.58`, sin nada de esto. Con `.\release.ps1 -Notas "..."` se
   publica y la app de produccion lo toma con el actualizador.
2. **Reimprimir la 459.** Con el shim, el en dash se imprime como guion corto y
   la factura sale. Verificarlo en la PC.
3. **El aviso podria ser un dialogo y no una linea de log.** Hoy el operador no
   se entera de que se sustituyo un caracter: se entera si busca en el log. Se
   eligio asi para no interrumpir, pero es una decision reversible y talvez
   convenga un aviso al pie de la pantalla de emision.
4. **Los `migraciones` y `movstock` en bases viejas** (de la instalacion de
   `C:\fe` del mismo dia) siguen pendientes: `MigrarVersion9` falla en bases sin
   facturas de proveedor. Ver la seccion de abajo.

## Lo que NO es de este arreglo

La base de `C:\fe` quedo con `VERSION_DB = 7` y sin la tabla `movstock`, porque
`movstock` tiene una clave foranea a `pcabecera` (facturas de proveedor) y esa
base de 2018 no la tiene. No tiene relacion con el PDF, pero salio en la misma
sesion: `MigrarVersion9` deberia saltarse lo que referencia una tabla que no
existe, en vez de fallar y dejar la version trabada para siempre.
