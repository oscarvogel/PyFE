# coding=utf-8
"""Genera los derivados del logo de Vogel Consultoria a partir del original.

Por que un script y no los archivos a mano
------------------------------------------
El .exe necesita un .ico multi-resolucion, y la interfaz necesita el logo en
varios tamanos. Generarlos desde un unico original garantiza que todos salieron
de la misma imagen: si alguien reemplaza el logo y no regenera, el test de
recursos lo detecta.

Salidas
-------
imagenes/marca/logo-vogel.png          original, sin tocar
imagenes/marca/logo-vogel.ico          multi-resolucion, para el .exe y la
                                       barra de tareas
imagenes/marca/logo-{16,24,32,48,64,128,256}.png
imagenes/marca/marca-recortada.png    solo el isotipo, sin el aire de los
                                       costados, para el encabezado

Uso:
    python tools/generar_marca.py [ruta-del-original]
"""
from __future__ import print_function

import os
import sys

RAIZ = None
for _nivel in range(4):
    _c = os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), *([".."] * _nivel)))
    if os.path.isfile(os.path.join(_c, "main.py")):
        RAIZ = _c
        break
if RAIZ is None:
    RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DESTINO = os.path.join(RAIZ, "imagenes", "marca")
ORIGINAL = os.path.join(DESTINO, "logo-vogel.png")

TAMANOS = (16, 24, 32, 48, 64, 128, 256)

# El original tiene mucho aire alrededor, y ademas el logo es un simbolo (arriba)
# mas un nombre (abajo). Para el encabezado, que el logo va a 40 px, hace falta
# solo el simbolo: con el logo entero queda diminuto, y con un recorte mal hecho
# se cuela un pedazo de la palabra.
#
# Estas fracciones estan medidas sobre el original de 1254x1254: la caja de
# contenido va de y=355 a y=858, con un corte claro entre y=752 y y=817 que
# separa el simbolo del nombre. El simbolo ocupa x=393..894.
ISOTIPO = (0.305, 0.272, 0.733, 0.612)   # izquierda, arriba, derecha, abajo

# El bloque completo (simbolo + nombre), para donde haga falta la marca entera.
MARCA_COMPLETA = (0.145, 0.272, 0.860, 0.695)


def _cargar():
    from PyQt5.QtGui import QImage
    if not os.path.isfile(ORIGINAL):
        raise SystemExit(
            "No existe {}.\nColoca ahi el logo original (1254x1254) y volve a "
            "correr el script.".format(ORIGINAL))
    return QImage(ORIGINAL)


def _escalar(img, lado):
    from PyQt5.QtCore import Qt
    return img.scaled(lado, lado, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def recortar(img, fracciones):
    from PyQt5.QtCore import QRect
    w, h = img.width(), img.height()
    l, a, r, b = fracciones
    caja = QRect(int(w * l), int(h * a), int(w * (r - l)), int(h * (b - a)))
    return img.copy(caja)


def principal(origen):
    if not os.path.isdir(DESTINO):
        os.makedirs(DESTINO)

    if not os.path.isfile(ORIGINAL):
        # Primera corrida: el original no esta en el repo todavia.
        import shutil
        os.makedirs(os.path.dirname(ORIGINAL), exist_ok=True)
        shutil.copy2(origen, ORIGINAL)
        print("original guardado en", os.path.relpath(ORIGINAL, RAIZ))

    img = _cargar()
    print("original: {}x{}".format(img.width(), img.height()))

    # PNG por tamano, para la interfaz.
    for lado in TAMANOS:
        ruta = os.path.join(DESTINO, "logo-{}.png".format(lado))
        _escalar(img, lado).save(ruta, "PNG")
    print("PNG: {}".format(", ".join(str(t) for t in TAMANOS)))

    # Isotipo (solo el simbolo), para el encabezado y la barra de tareas.
    iso = recortar(img, ISOTIPO)
    iso.save(os.path.join(DESTINO, "marca-recortada.png"), "PNG")
    for lado in (32, 48, 64):
        _escalar(iso, lado).save(
            os.path.join(DESTINO, "marca-{}.png".format(lado)), "PNG")
    print("isotipo: {}x{} (simbolo solo)".format(iso.width(), iso.height()))

    # Bloque completo (simbolo + nombre), para donde haga falta la marca entera.
    completa = recortar(img, MARCA_COMPLETA)
    completa.save(os.path.join(DESTINO, "marca-completa.png"), "PNG")
    for ancho_destino in (200, 400):
        completa.scaledToWidth(ancho_destino).save(
            os.path.join(DESTINO, "marca-completa-{}.png".format(ancho_destino)),
            "PNG")
    print("marca completa: {}x{}".format(completa.width(), completa.height()))

    # .ico multi-resolucion. Windows toma el tamano que necesita de la misma
    # lista, asi que el icono se ve bien en la barra de tareas, en el
    # administrador de archivos y en la lista de programas.
    _escribir_ico([os.path.join(DESTINO, "logo-{}.png".format(t))
                   for t in TAMANOS if t <= 256],
                  os.path.join(DESTINO, "logo-vogel.ico"))
    print("ico: imagenes/marca/logo-vogel.ico")
    return 0


def _escribir_ico(rutas_png, destino):
    """Escribe un .ico multi-resolucion.

    Se hace a mano y no con QIcon.write por dos motivos: QIcon necesita una
    QApplication viva (este script corre sin ventana) y no siempre escribe
    .ico. El formato es simple: cabecera, un directorio de entradas y los PNG
    tal cual; Windows Vista en adelante acepta PNG dentro de un .ico.
    """
    import struct

    from PyQt5.QtGui import QImage

    entradas = []
    for ruta in rutas_png:
        lado = QImage(ruta).width()
        if lado > 256:
            # El formato ICO clasico no tiene entrada de 256: se descarta.
            continue
        with open(ruta, "rb") as f:
            entradas.append((lado, f.read()))

    if not entradas:
        raise SystemExit("no hay PNG para escribir el .ico")
    entradas.sort(key=lambda par: par[0])

    cantidad = len(entradas)
    offset = 6 + 16 * cantidad
    partes = [struct.pack("<HHH", 0, 1, cantidad)]
    for lado, datos in entradas:
        # En el formato ICO el ancho y el alto van en un byte, y 256 no entra:
        # el valor 0 significa "256". Es la convencia de Windows, no un error.
        byte_lado = lado if lado < 256 else 0
        partes.append(struct.pack("<BBBBHHII",
                                  byte_lado,
                                  byte_lado,
                                  0,             # paleta
                                  0,             # reservado
                                  1,             # planos de color
                                  32,            # bits por pixel
                                  len(datos),    # tamaño de la imagen
                                  offset))       # offset en el archivo
        offset += len(datos)
    for _lado, datos in entradas:
        partes.append(datos)

    with open(destino, "wb") as f:
        f.write(b"".join(partes))


if __name__ == "__main__":
    origen = sys.argv[1] if len(sys.argv) > 1 else None
    if origen is None and os.path.isfile(ORIGINAL):
        origen = ORIGINAL
    elif origen is None:
        raise SystemExit(
            "Falta el original.\nUso: python tools/generar_marca.py "
            "ruta\\al\\logo.png")
    sys.exit(principal(origen))
