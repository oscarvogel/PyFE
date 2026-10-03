# coding=utf-8
"""Renderiza una grilla CON DATOS, para ver de verdad como queda.

    python tools/render_tabla.py

Las capturas que se hicieron hasta ahora mostraban tablas vacias, que es como
nacen antes de cargar. Con una tabla vacia no se puede ver si los importes se
leen bien, si los titulos quedan alineados con los numeros ni si las columnas se
reparten de forma razonable: eso solo se aprecia con filas adentro.
"""
from __future__ import print_function

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import datetime  # noqa: E402
import decimal  # noqa: E402
from PyQt5.QtGui import QFont, QFontDatabase  # noqa: E402
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QWidget  # noqa: E402

SALIDA = os.path.join(RAIZ, "docs", "ui")

# Una venta de ejemplo con los numeros que rompen el formato: importes de
# cuatro y seis cifras, una cantidad con decimales, un porcentaje entero.
RENGLONES = [
    [2, "TORN-0001", "Tornillo hexagonal 1/4 x 1\" con arandela", 1250.5, 21, 3025.21],
    [1, "ARAND-114", "Arandela plana M6 zincada", 85.9, 21, 103.94],
    [150, "TUE-880", "Tubo de acero 3/4\" x 6m", 18450.0, 21, 336117.0],
    [1, "SERV-001", "Mano de obra - instalación", 485000.0, 0, 485000.0],
    [3, "TORN-0001", "Tornillo hexagonal 1/4 x 1\" con arandela", 1250.5, 21, 7888.15],
]


# Columnas numericas de RENGLONES: 0=cant, 3=unitario, 4=iva, 5=subtotal
NUMERICAS = (0, 3, 4, 5)


def main():
    from PyQt5.QtWidgets import QLabel, QVBoxLayout

    app = QApplication.instance() or QApplication(sys.argv)
    for nombre in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf"):
        ruta = os.path.join(r"C:\Windows\Fonts", nombre)
        if os.path.exists(ruta):
            QFontDatabase.addApplicationFont(ruta)

    from libs.tema import aplicar_tema
    aplicar_tema(app)
    from libs.Grillas import Grilla

    if not os.path.isdir(SALIDA):
        os.makedirs(SALIDA)

    ventana = QWidget()
    ventana.setWindowTitle("Grilla de prueba")
    vertical = QVBoxLayout(ventana)
    vertical.setContentsMargins(16, 16, 16, 16)

    titulo = QLabel("Como se veria una tabla con datos de verdad")
    vertical.addWidget(titulo)

    grilla = Grilla(tamanio=10)
    grilla.ArmaCabeceras(
        cabeceras=["Cant.", "Codigo", "Detalle", "Unitario", "IVA", "SubTotal"],
        formatos=["Cantidad", "String", "String", "Moneda", "Entero", "Moneda"])
    grilla.enabled = True
    grilla.columnasHabilitadas = [0, 1, 2, 3, 4]
    grilla.textoVacio = "Todavía no hay productos en la venta."
    for renglon in RENGLONES:
        # Solo las columnas numericas van como Decimal; el resto es texto y
        # Decimal() revienta con una cadena.
        fila = [decimal.Decimal(str(renglon[i])) if i in NUMERICAS else renglon[i]
                for i in range(len(renglon))]
        grilla.AgregaItem(fila)
    vertical.addWidget(grilla)

    ventana.resize(1024, 320)
    ventana.show()
    app.processEvents()
    destino = os.path.join(SALIDA, "tabla_con_datos.png")
    ventana.grab().save(destino)
    print("generado:", os.path.relpath(destino, RAIZ))

    # El total de la columna SubTotal, leido como lo lee el controlador, para
    # comprobar que el formato no rompio los calculos.
    total = sum(grilla.ObtenerItemNumerico(fila=i, col="SubTotal")
                for i in range(grilla.rowCount()))
    print("suma de SubTotal leida de las celdas: {}".format(total))
    print("suma esperada:                      {}".format(
        sum(decimal.Decimal(str(r[5])) for r in RENGLONES)))
    ventana.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
