"""Abre las pantallas de stock contra el sandbox y las captura.

El seed puede dejar la base perfecta y el operador encontrar la pantalla vacia
igualmente. Por eso esto abre las ventanas de verdad, con el tema aplicado, y
las mira: una pantalla vacia no dice "todo bien" en ningun test.

    python tools/capturar_stock_sembrado.py
"""

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

SANDBOX = os.path.join(RAIZ, "_sandbox_prueba")
if not os.path.isdir(SANDBOX):
    raise SystemExit(
        "No existe el sandbox.\n"
        "  python tools/armar_sandbox.py\n"
        "  python tools/sembrar_stock.py")

# Antes de que se importe nada del modelo: `libs.rutas` lee esto al resolver
# la carpeta de datos, y `modelos.ModeloBase` la consulta al importarse.
os.environ["PYFE_CARPETA_DATOS"] = SANDBOX
os.chdir(RAIZ)

from PyQt5.QtWidgets import QApplication  # noqa: E402

SALIDA = os.path.join(RAIZ, "_capturas")
if not os.path.isdir(SALIDA):
    os.makedirs(SALIDA)

app = QApplication.instance() or QApplication([])

from libs.tema import aplicar_tema  # noqa: E402
aplicar_tema(app)

from controladores.Stock import (AjustesStockController,  # noqa: E402
                                 MovimientosStockController, StockController)
from modelos.ModeloBase import db  # noqa: E402

db.connect(reuse_if_open=True)


def captura(controller, nombre, ancho=1180, alto=720):
    view = controller.view
    view.resize(ancho, alto)
    view.show()
    view.raise_()
    view.activateWindow()
    for _ in range(8):
        app.processEvents()

    ruta = os.path.join(SALIDA, nombre + ".png")
    view.grab().save(ruta)
    print("  {:<28} {}x{} -> {}".format(nombre, view.width(), view.height(),
                                        os.path.relpath(ruta, RAIZ)))
    return view


print("Capturas contra", os.path.relpath(SANDBOX, RAIZ))

print("Stock:")
vista_stock = captura(StockController(), "sembrado-stock")
filas = vista_stock.findChildren(object)
print("  filas en la grilla:",
      vista_stock.grilla.rowCount() if hasattr(vista_stock, "grilla")
      else "?")

print("Ajustes de stock:")
captura(AjustesStockController(), "sembrado-ajustes-stock", 640, 340)

print("Movimientos de stock:")
vista_mov = captura(MovimientosStockController(), "sembrado-movimientos-stock")

print()
print("Lo que se ve:")
try:
    grilla = vista_stock.findChild(type(vista_mov.grilla))
except Exception:
    pass

for etiqueta, vista in (("Stock", vista_stock),
                        ("Movimientos", vista_mov)):
    for hijo in vista.children():
        if hasattr(hijo, "rowCount") and hasattr(hijo, "columnCount") and \
                hijo.columnCount() > 3:
            print("  {:<12} {} filas x {} columnas".format(
                etiqueta, hijo.rowCount(), hijo.columnCount()))
            for fila in range(min(hijo.rowCount(), 14)):
                celdas = []
                for c in range(hijo.columnCount()):
                    item = hijo.item(fila, c)
                    celdas.append((item.text() if item else "")[:18])
                print("      " + " | ".join(celdas))
            break

db.close()
print()
print("listo")