# coding=utf-8
"""Genera el set de iconos de PyFE: SVG monoline, una sola gramatica visual.

Por que SVG y no los PNG que habia
----------------------------------
Los iconos viejos son clipart de distintas epocas y estilos: un calendario
rojo de flaticon, un Excel verde, una flecha de puerta, gente en circulo
amarillo. Mezclados en la misma barra se nota que no pertenecen al mismo
producto, y no se pueden recolorear ni escalar sin pixelarse.

Este set es lo contrario: un solo trazo, un solo grosor, un solo color, todos
sobre una grilla de 24x24. Es el mismo criterio con el que se dibujan los
iconos de las aplicaciones profesionales modernas, y como son vectoriales se
ven nítidos en cualquier monitor y se pueden pintar con otro color desde el
tema.

Los archivos se commitean. Se generan con este script solo cuando cambia el
set, no en cada arranque.

    python tools/generar_iconos.py
"""

from __future__ import print_function

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "imagenes", "iconos")

# Subcarpetas con los mismos iconos en otros colores, para botones con fondo
# de color o con texto de color.
BLANCO_SUBCARPETA = "blanco"
PELIGRO_SUBCARPETA = "peligro"

# Gramatica del set. Cambiar estos tres numeros cambia el aspecto de TODOS los
# iconos, asi que viven aca y no repetidos en cada dibujo.
LIENZO = 24
TRAZO = 1.7
COLOR = "#0863C6"
BLANCO = "#FFFFFF"
PELIGRO = "#C62F35"

_PLANTILLA = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ll} {ll}" '
    'width="{ll}" height="{ll}" fill="none" stroke="{color}" '
    'stroke-width="{trazo}" stroke-linecap="round" stroke-linejoin="round">\n'
    "{cuerpo}\n</svg>\n"
)

# Cada entrada: nombre -> cuerpo del SVG (sin el <svg>).
ICONOS = {
    # -- Pantalla principal -------------------------------------------------
    "nueva-venta": (
        '  <path d="M6 3h12v18l-2.5-1.8L13 21l-2.5-1.8L8 21 6 21V3z"/>\n'
        '  <path d="M12 8.5v5"/>\n'
        '  <path d="M9.5 11h5"/>'
    ),
    "clientes": (
        '  <circle cx="9.5" cy="8" r="3.5"/>\n'
        '  <path d="M3.5 20v-1.5a6 6 0 0 1 12 0V20"/>\n'
        '  <path d="M16.5 5a3.5 3.5 0 0 1 0 6.9"/>\n'
        '  <path d="M18 14.4a5 5 0 0 1 2.5 4.3V20"/>'
    ),
    "productos": (
        '  <path d="M12 3l8 4.2v9.6L12 21l-8-4.2V7.2L12 3z"/>\n'
        '  <path d="M4 7.2l8 4.3 8-4.3"/>\n'
        '  <path d="M12 11.5V21"/>'
    ),
    "comprobantes": (
        '  <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/>\n'
        '  <path d="M8 13h8"/>\n'
        '  <path d="M8 16.5h5"/>'
    ),
    "cuentas": (
        '  <path d="M5 5.5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-13z"/>\n'
        '  <path d="M9 8h6"/>\n'
        '  <path d="M9 11.5h6"/>\n'
        '  <path d="M9 15h3.5"/>'
    ),
    "reportes": (
        '  <path d="M4 20V4"/>\n'
        '  <path d="M4 20h16"/>\n'
        '  <path d="M8.5 20v-6"/>\n'
        '  <path d="M12.5 20V8.5"/>\n'
        '  <path d="M16.5 20v-4"/>'
    ),
    "arca": (
        '  <path d="M12 3l7.5 2.8V12c0 4.8-3.2 7.6-7.5 9c-4.3-1.4-7.5-4.2-7.5-9V5.8L12 3z"/>\n'
        '  <path d="M9 12l2.2 2.2L15.5 10"/>'
    ),
    "configuracion": (
        '  <path d="M4 7.5h8"/>\n'
        '  <path d="M16 7.5h4"/>\n'
        '  <circle cx="14" cy="7.5" r="2"/>\n'
        '  <path d="M4 16.5h4"/>\n'
        '  <path d="M12 16.5h8"/>\n'
        '  <circle cx="10" cy="16.5" r="2"/>'
    ),
    "salir": (
        '  <path d="M14.5 4H6.5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8"/>\n'
        '  <path d="M10 12h10"/>\n'
        '  <path d="M16.8 8.6L20.2 12l-3.4 3.4"/>'
    ),

    # -- Acciones -----------------------------------------------------------
    "buscar": (
        '  <circle cx="10.5" cy="10.5" r="6.5"/>\n'
        '  <path d="M15.4 15.4L20 20"/>'
    ),
    "guardar": (
        '  <path d="M5 4.5h10.5L19 8v11.5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-14a1 1 0 0 1 1-1z"/>\n'
        '  <path d="M8 4.5v5h7v-5"/>\n'
        '  <path d="M8 20.5v-6h8v6"/>'
    ),
    "nuevo": (
        '  <circle cx="12" cy="12" r="8.5"/>\n'
        '  <path d="M12 8.5v7"/>\n'
        '  <path d="M8.5 12h7"/>'
    ),
    "agregar": (
        '  <path d="M12 5v14"/>\n'
        '  <path d="M5 12h14"/>'
    ),
    "editar": (
        '  <path d="M4 20l1-4.2L16.2 4.6a1.6 1.6 0 0 1 2.3 0l.9.9a1.6 1.6 0 0 1 0 2.3L8.2 19 4 20z"/>\n'
        '  <path d="M14.6 6.2l3.2 3.2"/>'
    ),
    "borrar": (
        '  <path d="M4 6.5h16"/>\n'
        '  <path d="M6.5 6.5V19a1.5 1.5 0 0 0 1.5 1.5h8a1.5 1.5 0 0 0 1.5-1.5V6.5"/>\n'
        '  <path d="M9.5 6.5V5a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v1.5"/>\n'
        '  <path d="M10.5 10.5v6"/>\n'
        '  <path d="M13.5 10.5v6"/>'
    ),
    "cerrar": (
        '  <path d="M6.5 6.5l11 11"/>\n'
        '  <path d="M17.5 6.5l-11 11"/>'
    ),
    "imprimir": (
        '  <path d="M7 8.5V4h10v4.5"/>\n'
        '  <path d="M6 8.5h12a1.5 1.5 0 0 1 1.5 1.5v6h-3.5V20h-8v-4H4.5v-6A1.5 1.5 0 0 1 6 8.5z"/>\n'
        '  <path d="M8 16h8"/>'
    ),
    "email": (
        '  <rect x="3" y="5.5" width="18" height="13" rx="2"/>\n'
        '  <path d="M3.8 7l8.2 5.6L20.2 7"/>'
    ),
    "check": (
        '  <circle cx="12" cy="12" r="8.5"/>\n'
        '  <path d="M8.2 12.2l2.6 2.6 5-5.4"/>'
    ),
    "excel": (
        '  <rect x="3" y="4" width="18" height="16" rx="2"/>\n'
        '  <path d="M3 9.5h18"/>\n'
        '  <path d="M9 9.5V20"/>\n'
        '  <path d="M15 9.5V20"/>'
    ),
    "adjuntar": (
        '  <path d="M20 11.5l-7.8 7.8a5 5 0 0 1-7-7l8.5-8.5a3.3 3.3 0 0 1 4.7 4.7l-8.5 8.5a1.7 1.7 0 0 1-2.4-2.4l7.8-7.8"/>'
    ),
    "importar": (
        '  <path d="M12 3.5v10"/>\n'
        '  <path d="M8 10l4 4 4-4"/>\n'
        '  <path d="M4 15v3.5a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V15"/>'
    ),
    "refrescar": (
        '  <path d="M20 12a8 8 0 1 1-2.5-5.8"/>\n'
        '  <path d="M20 4.5V10h-5.5"/>'
    ),
    "certificado": (
        '  <circle cx="12" cy="9" r="5.5"/>\n'
        '  <path d="M8.5 13.5L7 21l5-2.5L17 21l-1.5-7.5"/>'
    ),
    "documento": (
        '  <path d="M6 3.5h8l4 4V20a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1z"/>\n'
        '  <path d="M14 3.5V8h4"/>\n'
        '  <path d="M8.5 12.5h7"/>\n'
        '  <path d="M8.5 16h4.5"/>'
    ),
    "proveedores": (
        '  <path d="M3 20.5V9.5l6-3.5 6 3.5v11"/>\n'
        '  <path d="M15 12.5h4.5a1 1 0 0 1 1 1v7"/>\n'
        '  <path d="M3 20.5h18"/>\n'
        '  <path d="M6.5 11.5h2M11 11.5h2M6.5 15h2M11 15h2"/>'
    ),
    "monotributo": (
        # Etiqueta de precio. La primera version era un circulo con una C y se
        # leia como simbolo de copyright, que no dice nada.
        '  <path d="M11.5 3.5H20a.5.5 0 0 1 .5.5v8.5l-8.5 8.5a1.4 1.4 0 0 1-2 0l-6.5-6.5a1.4 1.4 0 0 1 0-2l8-8.5z"/>\n'
        '  <circle cx="16.5" cy="7.5" r="1.4"/>'
    ),
    "carpeta": (
        '  <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/>'
    ),
    "vacio": (
        '  <rect x="3.5" y="5" width="17" height="14" rx="2"/>\n'
        '  <path d="M3.5 9.5h17"/>\n'
        '  <path d="M9 13.5h6"/>'
    ),

    # -- Barra de texto enriquecido ---------------------------------------
    # Van aparte de los de arriba a proposito: "copiar" y "pegar" en un editor
    # de texto no pueden ser el mismo icono generico de "documento", se
    # distinguen por la accion.
    "deshacer": (
        '  <path d="M4 9h9a5.5 5.5 0 0 1 0 11H8"/>\n'
        '  <path d="M7.5 5.5L4 9l3.5 3.5"/>'
    ),
    "rehacer": (
        '  <path d="M20 9h-9a5.5 5.5 0 0 0 0 11h5"/>\n'
        '  <path d="M16.5 5.5L20 9l-3.5 3.5"/>'
    ),
    "cortar": (
        '  <circle cx="6.5" cy="18" r="2.5"/>\n'
        '  <circle cx="17.5" cy="18" r="2.5"/>\n'
        '  <path d="M8.2 16.1L18 4"/>\n'
        '  <path d="M15.8 16.1L6 4"/>'
    ),
    "copiar": (
        '  <rect x="8" y="8" width="12" height="12" rx="2"/>\n'
        '  <path d="M16 5.5a1.5 1.5 0 0 0-1.5-1.5h-9A1.5 1.5 0 0 0 4 5.5v9A1.5 1.5 0 0 0 5.5 16"/>'
    ),
    "pegar": (
        '  <path d="M9 4.5h6v2H9z"/>\n'
        '  <path d="M15 5.5h2.5a1.5 1.5 0 0 1 1.5 1.5v12a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 5 19V7a1.5 1.5 0 0 1 1.5-1.5H9"/>\n'
        '  <path d="M9 12h6"/>\n'
        '  <path d="M9 15.5h4"/>'
    ),
    "seleccionar-todo": (
        '  <path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8"/>\n'
        '  <path d="M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8"/>\n'
        '  <path d="M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16"/>\n'
        '  <path d="M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16"/>\n'
        '  <path d="M8.5 12h7"/>'
    ),
    "ajustar-texto": (
        '  <path d="M3.5 6.5h17"/>\n'
        '  <path d="M3.5 11h12"/>\n'
        '  <path d="M3.5 15.5h17"/>\n'
        '  <path d="M3.5 20h9"/>\n'
        '  <path d="M20 9.5v6"/>\n'
        '  <path d="M17.5 13L20 15.5 22.5 13"/>'
    ),
    "negrita": (
        '  <path d="M7 4.5h6a3.75 3.75 0 0 1 0 7.5H7z"/>\n'
        '  <path d="M7 12h6.8a3.75 3.75 0 0 1 0 7.5H7z"/>\n'
        '  <path d="M7 4.5v15"/>'
    ),
    "cursiva": (
        '  <path d="M15.5 4.5h-4a3.5 3.5 0 0 0 0 7h2.5a3.5 3.5 0 0 1 0 7h-4"/>\n'
        '  <path d="M13 4.5l-3 15"/>'
    ),
    "subrayado": (
        '  <path d="M7 4.5v7a5 5 0 0 0 10 0v-7"/>\n'
        '  <path d="M5 20.5h14"/>'
    ),
    "alinear-izquierda": (
        '  <path d="M3.5 5h17"/>\n'
        '  <path d="M3.5 10h10"/>\n'
        '  <path d="M3.5 15h14"/>\n'
        '  <path d="M3.5 20h8"/>'
    ),
    "alinear-centro": (
        '  <path d="M3.5 5h17"/>\n'
        '  <path d="M7 10h10"/>\n'
        '  <path d="M5 15h14"/>\n'
        '  <path d="M8.5 20h7"/>'
    ),
    "alinear-derecha": (
        '  <path d="M3.5 5h17"/>\n'
        '  <path d="M10.5 10h10"/>\n'
        '  <path d="M6.5 15h14"/>\n'
        '  <path d="M12.5 20h8"/>'
    ),
    "alinear-justificado": (
        '  <path d="M3.5 5h17"/>\n'
        '  <path d="M3.5 10h17"/>\n'
        '  <path d="M3.5 15h17"/>\n'
        '  <path d="M3.5 20h17"/>'
    ),
}


def generar(trazo=TRAZO, color=COLOR, destino=DESTINO):
    if not os.path.isdir(destino):
        os.makedirs(destino)

    escritos = []
    for nombre, cuerpo in sorted(ICONOS.items()):
        svg = _PLANTILLA.format(ll=LIENZO, color=color, trazo=trazo, cuerpo=cuerpo)
        ruta = os.path.join(destino, "{}.svg".format(nombre))
        with open(ruta, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
        escritos.append(ruta)

    # Segunda y tercera pasada: variantes en blanco (botones primarios) y en
    # rojo (botones destructivos).
    #
    # Sin esto, el icono de un boton azul se dibuja azul sobre fondo azul y
    # desaparece: se ve el texto y un manchon. Y en un boton de borrar, con el
    # texto en rojo y el icono en azul, el dibujo dice otra cosa. Qt no sabe
    # recolorear un QIcon desde el CSS, asi que las variantes tienen que existir
    # como archivo.
    for subcarpeta, color in ((BLANCO_SUBCARPETA, BLANCO), (PELIGRO_SUBCARPETA, PELIGRO)):
        for nombre, cuerpo in sorted(ICONOS.items()):
            svg = _PLANTILLA.format(ll=LIENZO, color=color, trazo=trazo, cuerpo=cuerpo)
            ruta = os.path.join(destino, subcarpeta, "{}.svg".format(nombre))
            if not os.path.isdir(os.path.dirname(ruta)):
                os.makedirs(os.path.dirname(ruta))
            with open(ruta, "w", encoding="utf-8", newline="\n") as f:
                f.write(svg)
            escritos.append(ruta)

    return escritos


def main():
    if "--preview" in sys.argv:
        # Renderiza una hoja de contactos en PNG para revisar el set de un
        # vistazo, sin abrir la app.
        return _preview()

    escritos = generar()
    print("iconos generados: {}".format(len(escritos)))
    for ruta in escritos:
        print("  ", os.path.relpath(ruta, RAIZ).replace("\\", "/"))
    return 0


def _preview():
    """Dibuja todos los iconos en una grilla y la guarda como PNG."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtCore import QRectF, Qt
    from PyQt5.QtGui import QColor, QImage, QPainter
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    nombres = sorted(ICONOS)
    columnas = 6
    celda = 96
    filas = (len(nombres) + columnas - 1) // columnas
    margen = 16

    ancho = columnas * celda + margen * 2
    alto = filas * (celda + 26) + margen * 2
    img = QImage(ancho, alto, QImage.Format_ARGB32)
    img.fill(QColor("#FFFFFF"))

    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QColor("#1F5FA9"))
    p.setFont(QFont_(11))
    for i, nombre in enumerate(nombres):
        c, f = i % columnas, i // columnas
        x = margen + c * celda
        y = margen + f * (celda + 26)
        p.drawImage(QRectF(x + 18, y + 12, 60, 60),
                    QImage(os.path.join(DESTINO, "{}.svg".format(nombre))))
        p.drawText(QRectF(x, y + celda + 8, celda, 20),
                   Qt.AlignCenter, nombre)
    p.end()

    destino = os.path.join(RAIZ, "docs", "ui", "iconos.png")
    if not os.path.isdir(os.path.dirname(destino)):
        os.makedirs(os.path.dirname(destino))
    img.save(destino)
    print("hoja de contactos:", destino)
    return 0


def QFont_(tamano):
    from PyQt5.QtGui import QFont
    f = QFont("Segoe UI", tamano)
    return f


if __name__ == "__main__":
    sys.exit(main())
