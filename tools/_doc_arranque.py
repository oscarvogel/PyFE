# coding=utf-8
"""Anota en la doc el bug de arranque y el test nuevo."""
import io
import sys

RUTA = "docs/STOCK.md"

with io.open(RUTA, "r", encoding="utf-8", newline="") as f:
    texto = f.read()

with open(RUTA, "rb") as f:
    CRLF = b"\r\n" in f.read()
SALTO = "\r\n" if CRLF else "\n"

if "800 tests en verde y la app sin arrancar" in texto:
    print("ya esta")
    sys.exit(0)

ANCLA = "### Para mirar las pantallas con datos"
if ANCLA not in texto:
    sys.exit("No se encuentra el ancla '{}'".format(ANCLA))

SECCION = '''
### 800 tests en verde y la app sin arrancar

Paso probando la pantalla y la app no abria: `NameError: name 'ComboSQL' is
not defined` en `modelos/Proveedores.py`.

**Falta un import.** El archivo define `class ComboProveedor(ComboSQL)` y usa
`ComboSQL` sin haberlo importado nunca. No era una importacion circular: era un
import que no estaba.

Lo que lo hace digno de anotarse es que **los 800 tests daban verde**. Los tests
importan lo que necesitan, y `controladores.Main` no es de ninguno: lo unico que
lo importa es `main.py`, que no se corre en ningun test.

El error aparecia tres niveles mas arriba del archivo roto, en la linea donde
`vistas.Articulos` pide el modulo:

```
main.py -> controladores.Main -> controladores.Articulos
        -> vistas.Articulos    -> modelos.Proveedores   <-- NameError
```

Asi que el mensaje de error hablaba de un archivo y el problema estaba en otro.

**Lo que se agrego:** `tests/test_arranque_importa.py`, que importa la cadena
completa del arranque (`modelos -> vistas -> controladores`), un modulo por
test para que el que fallo diga cual es.

Y un segundo test que mira el archivo con `ast`: toda clase tiene que heredar
de algo que el modulo defina o importe. Ese cubre el caso de que el modulo ya
este en cache por otro test y la cadena de imports no llegue a ejecutarlo de
verdad.

Se comprobaron los dos: quitar el import deja los **8 tests en rojo**, y el
archivo queda como estaba.

#### La leccion, que no es de este modulo

**"La suite pasa" y "la app arranca" son dos cosas distintas**, y la diferencia
son los imports que nadie importa. Un modulo que solo carga el arranque es un
modulo que no tiene ningun test, por mas verde que este el resto.
'''

texto = texto.replace(ANCLA, SECCION.replace("\n", SALTO) + ANCLA, 1)

with io.open(RUTA, "w", encoding="utf-8", newline="") as f:
    f.write(texto)

print("OK: doc actualizada")