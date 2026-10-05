"""Captura los dialogos chicos, antes y despues, para mirarlos.

Con offscreen los textos NO se dibujan (los widgets se pintan, las letras no), y
una captura sin texto no dice nada de la pantalla. Se corre con la plataforma
de Qt de verdad, como tools/capturar_stock.py.

Ademas del PNG imprime la geometria de cada widget: una captura muestra que
algo se ve mal, el numero muestra cuanto.
"""
import os
import sys

if len(sys.argv) > 1 and sys.argv[1] == "offscreen":
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
else:
    os.environ.pop("QT_QPA_PLATFORM", None)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

from PyQt5.QtWidgets import QApplication  # noqa: E402

SALIDA = os.path.join(RAIZ, "_capturas")
if not os.path.isdir(SALIDA):
    os.makedirs(SALIDA)

app = QApplication.instance() or QApplication([])

from libs.tema import aplicar_tema  # noqa: E402
aplicar_tema(app)
print("tema aplicado; plataforma:", app.platformName())


def captura(view, nombre):
    view.show()
    view.raise_()
    view.activateWindow()
    for _ in range(6):
        app.processEvents()

    ruta = os.path.join(SALIDA, nombre + ".png")
    view.grab().save(ruta)

    print("{}: {}x{}  ->  {}".format(nombre, view.width(), view.height(), ruta))
    titulo = getattr(view, "lblTitulo", None)
    if titulo is not None:
        print("    titulo en (x={}, y={}, w={}, h={})".format(
            titulo.x(), titulo.y(), titulo.width(), titulo.height()))
    return ruta


class _TipoIva(object):
    iva = "21"


class _Articulo(object):
    idarticulo = 1
    nombre = "PRODUCTOS"
    preciopub = "1"
    tipoiva = _TipoIva()


from vistas.Stock import AjustesStockView  # noqa: E402
from vistas.VentaSimple import (VentaSimpleAltaArticuloDialog,  # noqa: E402
                                VentaSimpleAltaClienteDialog,
                                VentaSimpleCantidadPrecioDialog)

captura(VentaSimpleCantidadPrecioDialog(_Articulo(), 1, 1),
        "dialogo-cantidad-precio")
captura(VentaSimpleAltaClienteDialog("x"), "dialogo-agregar-cliente")
captura(VentaSimpleAltaArticuloDialog("x"), "dialogo-agregar-articulo")
captura(AjustesStockView(), "dialogo-ajustar-stock")

print("listo")