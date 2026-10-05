"""Captura las ventanas nuevas de stock para mirarlas de verdad.

Un smoke test que dice 'se puede abrir' no dice si la pantalla esta bien
armada: si una columna quedo con el ancho de un caracter, o si los botones se
pisan, o si el texto se sale del recuadro, el test pasa igual. Solo mirandola
se ve.

Se corre con la plataforma de Qt de verdad, no con offscreen: con offscreen
los textos no se dibujan (los widgets se pintan, las letras no), y una captura
sin texto no dice nada de la pantalla. La ventana aparece un instante.

Se aplica el tema igual que la app, porque sin el tema las capturas se ven con
otro estilo del que va a ver el operador.
"""

import os
import sys

if len(sys.argv) > 1 and sys.argv[1] == "offscreen":
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

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


def captura(view, nombre, ancho=1180, alto=720):
    view.resize(ancho, alto)
    view.show()
    view.raise_()
    view.activateWindow()
    # Varias vueltas al loop: las grillas ajustan anchos y el alto de fila en
    # un evento posterior, y con una sola vuelta salen con los valores por
    # defecto.
    for _ in range(8):
        app.processEvents()
    ruta = os.path.join(SALIDA, nombre + ".png")
    ok = view.grab().save(ruta)
    print("{}: {} {}".format(nombre, "OK" if ok else "FALLO", ruta))
    view.hide()


from controladores.Stock import (AjustesStockController,  # noqa: E402
                                MovimientosStockController, StockController)

print("construyendo Stock...")
c = StockController()
captura(c.view, "1_stock", 1250, 600)

print("construyendo Ajustes...")
c2 = AjustesStockController()
c2.CargaProducto(1)
c2.view.txtCantidad.setText("-3")
captura(c2.view, "2_ajustes", 640, 360)

print("construyendo Movimientos...")
c3 = MovimientosStockController()
captura(c3.view, "3_movimientos", 1250, 600)

print()
print("Capturas en", SALIDA)
