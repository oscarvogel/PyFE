# coding=utf-8
"""Renderiza pantallas de PyFE a PNG sin base de datos ni ARCA.

Para que sirve
--------------
Un restyle sin verse es trabajar a ciegas. Este script monta cada vista en una
plataforma Qt "offscreen" (sin pantalla), le aplica el tema real y saca un PNG.
Sirve para comparar antes/despues y para detectar de inmediato una vista que
revienta por un cambio de estilo.

No abre la base ni llama a ARCA: solo instancia las clases de vista. Las vistas
que necesitan base se listan como omitidas, que tambien es informacion util.

Uso:
    python tools/render_ui.py                  # todas las que se puedan
    python tools/render_ui.py Main VentaSimple # solo esas
    python tools/render_ui.py --salida docs/ui  # otra carpeta
"""

from __future__ import print_function

import argparse
import os
import sys
import traceback

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtGui import QFont, QFontDatabase  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

# Fuentes de Windows para el render. El plugin offscreen no encuentra la
# carpeta de fuentes de Qt, y sin esto el texto sale como "_". Es un
# artefacto del render, no un problema de la app.
FUENTES_RENDER = ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "arial.ttf", "arialbd.ttf")

SALIDA_POR_DEFECTO = os.path.join(RAIZ, "docs", "ui")


class _ArticuloStub(object):
    """Articulo falso, para el dialogo que solo muestra el nombre."""

    def __init__(self, nombre="Tornillo hexagono 1/4 x 1\""):
        self.nombre = nombre


class _ClienteStub(object):
    """Cliente falso, para el selector de cliente."""

    def __init__(self, idcliente, nombre, cuit="", dni=""):
        self.idcliente = idcliente
        self.nombre = nombre
        self.cuit = cuit
        self.dni = dni


CLIENTES_FALSOS = [
    _ClienteStub(1, "Distribuidora del Sur SRL", cuit="30-71234567-9"),
    _ClienteStub(2, "Ferreteria La Esquina", cuit="", dni="25111222"),
    _ClienteStub(3, "Consumidor Final", cuit="", dni="30111222"),
]


# Vistas que se intentan renderizar.
# (etiqueta, modulo, clase, ancho, alto, argumentos[, metodo])
# Solo las que se construyen sin base de datos.
# ancho/alto == 0 -> se renderiza al tamano que pida la propia vista.
# metodo opcional: se construye la clase y despues se llama a ese metodo, que
# devuelve el widget a renderizar. Sirve para los dialogos que solo existen
# adentro de una vista (el de Acerca de) y que de otro modo no se podrian mirar.
VISTAS = [
    ("Main", "vistas.Main", "MainView", 0, 0, ()),
    ("AcercaDe", "vistas.Main", "MainView", 0, 0, (), "construir_acerca_de"),
    ("CorreoReportes", "vistas.ConfiguracionCorreo", "ConfiguracionCorreoView", 0, 0, ()),
    ("VentaSimple", "vistas.VentaSimple", "VentaSimpleView", 1024, 700, ()),
    ("AltaCliente", "vistas.VentaSimple", "VentaSimpleAltaClienteDialog", 0, 0, ("Acme SA",)),
    ("AltaArticulo", "vistas.VentaSimple", "VentaSimpleAltaArticuloDialog", 0, 0, ("Tornillo",)),
    ("CantidadPrecio", "vistas.VentaSimple", "VentaSimpleCantidadPrecioDialog", 0, 0,
     (_ArticuloStub(), 2, 1500.0)),
    ("SeleccionCliente", "vistas.VentaSimple", "VentaSimpleSeleccionClienteDialog", 0, 0,
     (CLIENTES_FALSOS,)),
    ("PrimerArranque", "vistas.PrimerArranque", "DialogoPrimerArranque", 620, 560, ()),
]

app = None


def cargar_fuentes():
    for nombre in FUENTES_RENDER:
        ruta = os.path.join(r"C:\Windows\Fonts", nombre)
        if os.path.exists(ruta):
            QFontDatabase.addApplicationFont(ruta)


def aplicar_tema_real():
    """Aplica el tema de la app, igual que main.py."""
    from libs.tema import aplicar_tema
    return aplicar_tema(app)


def _construir(modulo, clase, ancho, alto, argumentos, metodo=None):
    mod = __import__(modulo, fromlist=[clase])
    widget = getattr(mod, clase)(*argumentos)

    # Las clases del proyecto parten de Formulario, que.center() re-centra en
    # cada resize. Sin pantalla no hay geometria util, asi que se fuerza.
    if hasattr(widget, "Center"):
        widget.Center = lambda: None

    # Las vistas que arman su UI en un initUi() aparte (MainView, por
    # ejemplo) llegan vacias si no se llama. Las que lo hacen en __init__
    # (VentaSimpleView) ya estan listas y no tienen el metodo.
    if hasattr(widget, "initUi"):
        widget.initUi()

    # El metodo devuelve el widget a mostrar (por ejemplo el dialogo de
    # Acerca de, que cuelga de la vista principal y no se abre solo).
    if metodo:
        widget = getattr(widget, metodo)()

    # ancho == 0 significa "al tamano que pida la propia vista", para no
    # inventar un tamano de pantalla que el usuario nunca ve.
    if ancho and alto:
        widget.resize(ancho, alto)
    else:
        widget.adjustSize()
        if ancho:
            widget.resize(ancho, widget.height())
    widget.show()
    app.processEvents()
    return widget


def render(etiqueta, modulo, clase, ancho, alto, argumentos, salida, metodo=None):
    destino = os.path.join(salida, "{}.png".format(etiqueta))
    try:
        widget = _construir(modulo, clase, ancho, alto, argumentos, metodo)
    except Exception as e:  # noqa: BLE001 - acá se reporta, no se propaga
        return "omitida", "{}: {}".format(type(e).__name__, e), None

    app.processEvents()
    if not widget.grab().save(destino):
        return "error", "no se pudo escribir {}".format(destino), None

    # Si la ventana no entra en el ancho pedido, Qt no la achica: la deja en
    # su minimo y el contenido de la derecha queda cortado en pantalla. Es el
    # bug que tenia la pantalla principal (una fila de 9 botones que pedia
    # 1836 px y se abria en 620), asi que se avisa en vez de dejar que pase.
    minimo = widget.minimumSizeHint()
    detalle = destino
    if ancho and minimo.width() > ancho:
        detalle += "  [DESBORDE: necesita {} px y se pidio {}]".format(
            minimo.width(), ancho)
    return "ok", detalle, widget


def main():
    p = argparse.ArgumentParser()
    p.add_argument("vistas", nargs="*", help="etiquetas a renderizar (por defecto, todas)")
    p.add_argument("--salida", default=SALIDA_POR_DEFECTO)
    args = p.parse_args()

    global app
    app = QApplication.instance() or QApplication(sys.argv)
    cargar_fuentes()

    info = aplicar_tema_real()
    print("tema: css={} fuente={} estilo={}".format(
        info.get("css"), info.get("fuente"), info.get("estilo")))
    if not info.get("css"):
        print("AVISO: no se encontro el stylesheet, el render no es representativo")

    if not os.path.isdir(args.salida):
        os.makedirs(args.salida)

    objetivos = VISTAS
    if args.vistas:
        pedidos = set(a.lower() for a in args.vistas)
        objetivos = [v for v in VISTAS if v[0].lower() in pedidos]
        if not objetivos:
            print("No coincide ninguna vista. Disponibles: {}".format(
                ", ".join(v[0] for v in VISTAS)))
            return 1

    resultados = []
    for entrada in objetivos:
        etiqueta, modulo, clase, ancho, alto, argumentos = entrada[:6]
        metodo = entrada[6] if len(entrada) > 6 else None
        estado, detalle, _ = render(etiqueta, modulo, clase, ancho, alto,
                                    argumentos, args.salida, metodo)
        resultados.append((etiqueta, estado, detalle))
        print("{:<20} {:<8} {}".format(etiqueta, estado, detalle))
        app.processEvents()

    ok = sum(1 for _, e, _ in resultados if e == "ok")
    print("")
    print("renderizadas: {}/{}  ->  {}".format(ok, len(resultados), args.salida))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
