# coding=utf-8
"""Genera los recursos graficos del tema (temas/recursos/).

Se generan con Qt y se commitean, no se generan en cada arranque: son tres
dibujitos de 16 px y depender de generarlos en runtime seria una complicacion
mas en el camino de arranque.

    python tools/generar_recursos_tema.py
"""

from __future__ import print_function

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QPointF, Qt  # noqa: E402
from PyQt5.QtGui import QColor, QImage, QPainter, QPen, QPolygonF  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

DESTINO = os.path.join(RAIZ, "temas", "recursos")
ESCALA = 4  # se dibuja grande y se reduce: sale mas nitido que directo a 16 px

# Acentos y grosores del tema, para que el dibujo no se aparte de la paleta.
COLOR_TEXTO = QColor("#52606D")
GROSOR = 1.8


def _lienzo(tamano):
    img = QImage(tamano * ESCALA, tamano * ESCALA, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    return img


def _guardar(img, nombre, tamano):
    pequena = img.scaled(tamano, tamano,
                         Qt.KeepAspectRatio, Qt.SmoothTransformation)
    ruta = os.path.join(DESTINO, nombre)
    if not pequena.save(ruta, "PNG"):
        raise RuntimeError("no se pudo escribir {}".format(ruta))
    return ruta


def chevron_abajo(tamano=16):
    """Flecha hacia abajo, para el desplegable de los QComboBox."""
    img = _lienzo(tamano)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(COLOR_TEXTO)
    pen.setWidthF(GROSOR * ESCALA)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)

    lado = tamano * ESCALA
    margen = 0.28 * lado
    p.drawPolyline(QPolygonF([
        QPointF(margen, lado * 0.42),
        QPointF(lado * 0.5, lado * 0.66),
        QPointF(lado - margen, lado * 0.42),
    ]))
    p.end()
    return _guardar(img, "chevron-abajo.png", tamano)


def chevron_derecha(tamano=16):
    """Flecha a la derecha, para los grupos plegables."""
    img = _lienzo(tamano)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(COLOR_TEXTO)
    pen.setWidthF(GROSOR * ESCALA)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)

    lado = tamano * ESCALA
    margen = 0.28 * lado
    p.drawPolyline(QPolygonF([
        QPointF(lado * 0.40, margen),
        QPointF(lado * 0.62, lado * 0.5),
        QPointF(lado * 0.40, lado - margen),
    ]))
    p.end()
    return _guardar(img, "chevron-derecha.png", tamano)


def buscar(tamano=16):
    """Lupa, para los botones de consultar/filtrar."""
    img = _lienzo(tamano)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(COLOR_TEXTO)
    pen.setWidthF(GROSOR * ESCALA)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)

    lado = tamano * ESCALA
    p.drawEllipse(QPointF(lado * 0.44, lado * 0.42), lado * 0.24, lado * 0.24)
    p.drawLine(QPointF(lado * 0.62, lado * 0.60), QPointF(lado * 0.84, lado * 0.82))
    p.end()
    return _guardar(img, "buscar.png", tamano)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    if not os.path.isdir(DESTINO):
        os.makedirs(DESTINO)

    for fn in (chevron_abajo, chevron_derecha, buscar):
        print("generado:", fn())
    return 0


if __name__ == "__main__":
    sys.exit(main())
