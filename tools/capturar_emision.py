"""Captura la pantalla de emision tal como quedo, en los dos estados.

No es un mockup: es la pantalla real de la app, con los componentes, el tema
y el controlador de verdad, con datos de ejemplo. La unica diferencia con lo
que ve el operador es que los campos no se guardan.
"""

import os
import sys
from datetime import date

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

from controladores.Facturas import FacturaController  # noqa: E402
from modelos.Articulos import Articulo  # noqa: E402


def _prepara(autorizada):
    c = FacturaController()
    c.view.show()
    c.view.raise_()

    # Un cliente, para que la pantalla se vea con algo.
    c.view.lblNombreCliente.setText("Estación de Servicio Palermo")
    c.view.lineEditDomicilio.setText("Av. Corrientes 1234, CABA")
    c.view.lineEditDocumento.setText("30-12345678-9")
    c.view.validaCliente.setText("1")

    # Tres renglones de ejemplo. Los numeros con coma porque es como los
    # muestra la grilla; el controlador los vuelve a floats al sumar.
    c.view.gridFactura.setRowCount(0)
    for linea in (["2", "1", "GASOLINA NAFTA SUPER", "500", "21", "1000"],
                  ["1", "1", "ACEITE 5W30 x 4L", "18000", "21", "18000"],
                  ["3", "1", "SERVICIO DE LAVADO", "3500", "21", "10500"]):
        c.view.gridFactura.AgregaItem(items=linea)

    c.view.ActualizaTotales(subtotal=29500.0, tributos=0.0, iva=6195.0,
                            total=35695.0)

    if autorizada:
        c.view.MuestraAutorizacion(
            numero="Factura A 0001-00002345",
            cae="7501234567890", resultado="A",
            vencimiento="14/10/2026", vencimiento_sql="20261014")
    else:
        c.view.MuestraSinAutorizar()

    for _ in range(14):
        app.processEvents()
    return c


for autorizada, nombre in ((False, "emision_rediseñada"),
                           (True, "emision_rediseñada_autorizada")):
    c = _prepara(autorizada)
    ruta = os.path.join(SALIDA, nombre + ".png")
    c.view.grab().save(ruta)
    print("{}: {}x{}".format(ruta, c.view.width(), c.view.height()))
    c.view.close()
