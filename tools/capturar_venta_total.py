"""Captura la venta rapida con datos, para ver el total como queda de verdad.

Con `offscreen` los textos no se dibujan, asi que esto corre con la plataforma
de Qt real, como `capturar_stock_sembrado.py`.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
SANDBOX = os.path.join(RAIZ, "_sandbox_prueba")
if not os.path.isdir(SANDBOX):
    raise SystemExit("No existe el sandbox. Corré tools/sembrar_stock.py")

os.environ["PYFE_CARPETA_DATOS"] = SANDBOX
os.chdir(RAIZ)

from PyQt5.QtWidgets import QApplication  # noqa: E402

SALIDA = os.path.join(RAIZ, "_capturas")
if not os.path.isdir(SALIDA):
    os.makedirs(SALIDA)

app = QApplication.instance() or QApplication([])

from libs.tema import aplicar_tema  # noqa: E402
aplicar_tema(app)

from decimal import Decimal  # noqa: E402

from controladores.VentaSimple import VentaSimpleController  # noqa: E402
from modelos.ModeloBase import db  # noqa: E402

db.connect(reuse_if_open=True)

controller = VentaSimpleController()
controller.view.resize(1180, 700)
controller.view.show()
controller.view.raise_()
controller.view.activateWindow()


def agregar(idarticulo, cantidad):
    from modelos.Articulos import Articulo
    articulo = Articulo.get_by_id(idarticulo)
    controller.solicitar_cantidad_y_precio = (
        lambda art, cant: (Decimal(str(cantidad)), Decimal(str(art.preciopub))))
    controller._agregar_este_articulo(articulo)


# Tornillo: hay 160, minimo 50. Dos renglones que juntos se llevan 200, o sea
# que no alcanzan: es el caso que tiene que verse en rojo.
agregar(7, 150)
agregar(7, 50)

for _ in range(8):
    app.processEvents()

print("total :", repr(controller.view.textTotal.text()))
print("lectura:", controller.view.textTotal.isEnabled(),
      "solo lectura:", controller.view.textTotal.isReadOnly())

grilla = controller.view.gridVenta
columnas = {}
for c in range(grilla.columnCount()):
    item = grilla.horizontalHeaderItem(c)
    if item is not None:
        columnas[item.text()] = c
for fila in range(grilla.rowCount()):
    valores = [grilla.item(fila, columnas[n]).text()
               for n in ("Cant.", "Detalle", "Stock", "Unitario", "SubTotal")
               if n in columnas]
    print("   ", " | ".join(valores))

ruta = os.path.join(SALIDA, "venta-total-formateado.png")
controller.view.grab().save(ruta)
print("captura:", os.path.relpath(ruta, RAIZ))

db.close()