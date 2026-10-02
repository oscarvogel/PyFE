# coding=utf-8
"""Smoke test de la interfaz: que las pantallas se puedan construir y no desborden.

Por que existe
--------------
Un cambio de estilos no da errores: si un selector del QSS esta mal escrito, el
control simplemente se ve sin estilo y no pasa nada visible. Y si un layout
cambia de tamaño, la ventana puede pedir mas ancho del que la pantalla tiene y
lo que sobra queda cortado sin avisar. Los dos fallos aparecen recien cuando un
cliente mira la pantalla.

Estos tests cubren las dos cosas:
  1) que las vistas se construyan sin reventar con el tema puesto
  2) que ninguna pida mas ancho del que se le pasa
  3) que el tema este aplicado de verdad y no sea un archivo vacio

Va con QT_QPA_PLATFORM=offscreen: no necesita pantalla, ni base de datos, ni
AFIP. Solo monta los widgets y los mira.
"""

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from PyQt5.QtWidgets import QApplication  # noqa: E402

# Ancho de referencia: 1024x768, la resolucion de una notebook econica. Si una
# pantalla no entra ahi, tampoco entra en la de un cliente con monitor chico.
ANCHO_MINIMO = 1024
ALTO_MINIMO = 600


class _ArticuloStub(object):
    def __init__(self, nombre="Tornillo hexagono 1/4 x 1\""):
        self.nombre = nombre


VISTAS = [
    ("MainView", "vistas.Main", "MainView", 1024, ALTO_MINIMO, ()),
    ("VentaSimpleView", "vistas.VentaSimple", "VentaSimpleView", ANCHO_MINIMO, 700, ()),
    ("AltaCliente", "vistas.VentaSimple", "VentaSimpleAltaClienteDialog", 0, 0, ("Acme",)),
    ("AltaArticulo", "vistas.VentaSimple", "VentaSimpleAltaArticuloDialog", 0, 0, ("Tornillo",)),
    ("CantidadPrecio", "vistas.VentaSimple", "VentaSimpleCantidadPrecioDialog", 0, 0,
     (_ArticuloStub(), 2, 1500.0)),
    ("PrimerArranque", "vistas.PrimerArranque", "DialogoPrimerArranque", 620, 560, ()),
    ("DialogoPassword", "vistas.DialogoPassword", "DialogoPassword", 0, 0, ()),
]


@pytest.fixture(scope="module")
def app():
    aplicacion = QApplication.instance() or QApplication(sys.argv)
    # El tema real, igual que en main.py: si el smoke test corre sin el, deja
    # de cubrir justo lo que se quiere cubrir.
    from libs.tema import aplicar_tema
    aplicar_tema(aplicacion)
    yield aplicacion


def _construir(app, modulo, clase, argumentos):
    mod = __import__(modulo, fromlist=[clase])
    widget = getattr(mod, clase)(*argumentos)
    if hasattr(widget, "Center"):
        widget.Center = lambda: None
    if hasattr(widget, "initUi"):
        widget.initUi()
    return widget


# -- 1) El tema -------------------------------------------------------------

def test_el_tema_se_aplica(app):
    assert app.styleSheet(), "no se aplico ningun stylesheet a la aplicacion"
    assert "QPushButton" in app.styleSheet(), "el stylesheet no parece ser pyfe.css"


def test_el_tema_usa_los_tokens_de_la_paleta(app):
    """Si el css se vacia o se rompe, la app sigue andando pero sin estilo.

    Los tokens son los de la marca Vogel Consultoria, medidos sobre
    imagenes/marca/logo-vogel.png (ver tools/generar_marca.py).
    """
    from libs.tema import ruta_tema
    ruta = ruta_tema()
    assert ruta, "no se encontro temas/pyfe.css"
    with open(ruta, "r", encoding="utf-8") as f:
        css = f.read()
    for color, que in (
        ("#0863C6", "azul de la marca"),
        ("#031A3E", "navy de la marca"),
        ("#F4A807", "dorado de la marca"),
        ("#1F2933", "texto"),
        ("#FFFFFF", "superficie"),
        ("#D5DCE4", "borde"),
    ):
        assert color in css, "falta el token {} ({}) en el tema".format(color, que)


def test_la_paleta_contrasta(app):
    """El texto tiene que poder leerse: contraste WCAG AA (4.5:1).

    Se recalcula desde los colores reales del tema en vez de tener el numero
    anotado a mano, asi que si alguien cambia un token sin mirar el contraste,
    el test dice cual fue el culpable.
    """
    def luminancia(hexcolor):
        h = hexcolor.lstrip("#")
        canales = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

        def lineal(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        r, g, b = (lineal(c) for c in canales)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def contraste(a, b):
        la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
        return (la + 0.05) / (lb + 0.05)

    # (texto, fondo, descripcion, minimo)
    pares = [
        ("#FFFFFF", "#0863C6", "texto del boton principal", 4.5),
        ("#FFFFFF", "#031A3E", "titulo del encabezado", 4.5),
        ("#9FB8D8", "#031A3E", "subtitulo del encabezado", 4.5),
        ("#2A1D00", "#F4A807", "texto del chip de homologacion", 4.5),
        ("#FFFFFF", "#C62F35", "texto del chip de produccion", 4.5),
        ("#0863C6", "#FFFFFF", "enlace o item activo sobre claro", 4.5),
        ("#1F2933", "#FFFFFF", "texto normal", 4.5),
        ("#52606D", "#FFFFFF", "texto secundario", 4.5),
    ]
    bajos = []
    for texto, fondo, que, minimo in pares:
        c = contraste(texto, fondo)
        if c < minimo:
            bajos.append("{}: {:.2f}:1 (min {}), {} sobre {}".format(
                que, c, minimo, texto, fondo))
    assert not bajos, "contraste insuficiente:\n  " + "\n  ".join(bajos)


def test_las_urls_del_tema_se_resuelven(app):
    """Un url() sin resolver deja los controles sin flecha ni icono.

    Qt las busca contra el cwd, que en el .exe compilado no es la carpeta de la
    app: por eso libs/tema.py las pasa a absolutas antes de aplicar.
    """
    from libs.tema import resolver_urls
    css = "QComboBox::down-arrow { image: url(@recursos/chevron-abajo.png); }"
    resuelto = resolver_urls(css)
    assert "url(@" not in resuelto, "quedo una url sin resolver: {}".format(resuelto)
    assert "chevron-abajo.png" in resuelto
    assert os.path.isfile(resuelto[resuelto.find("url(") + 4:resuelto.find(")")])


# -- 2) Las pantallas se construyen ----------------------------------------

@pytest.mark.parametrize("etiqueta,modulo,clase,ancho,alto,argumentos", VISTAS,
                         ids=[v[0] for v in VISTAS])
def test_la_vista_se_construye(app, etiqueta, modulo, clase, ancho, alto, argumentos):
    widget = _construir(app, modulo, clase, argumentos)
    if ancho and alto:
        widget.resize(ancho, alto)
    else:
        widget.adjustSize()
    widget.show()
    app.processEvents()
    assert widget is not None
    widget.close()


@pytest.mark.parametrize("etiqueta,modulo,clase,ancho,alto,argumentos", VISTAS,
                         ids=[v[0] for v in VISTAS])
def test_la_vista_no_desborda(app, etiqueta, modulo, clase, ancho, alto, argumentos):
    """La ventana tiene que entrar en una pantalla de notebook.

    Si el minimo del layout es mas ancho que la ventana, Qt no la achica: deja
    los controles del right fuera de la pantalla. Es el bug que tenia la
    pantalla principal, que pedia 1836 px y se abria en 620.
    """
    widget = _construir(app, modulo, clase, argumentos)
    if ancho and alto:
        widget.resize(ancho, alto)
    else:
        widget.adjustSize()
    widget.show()
    app.processEvents()

    minimo = widget.minimumSizeHint()
    limite = ancho or ANCHO_MINIMO
    assert minimo.width() <= limite, (
        "{} necesita {} px de ancho y se le pasaron {}: el contenido de la "
        "derecha se va a ver cortado".format(etiqueta, minimo.width(), limite))
    widget.close()


# -- 3) La pantalla de configuracion ---------------------------------------

def test_la_configuracion_no_ofrece_un_tema_que_no_hace_nada(app):
    """El selector de tema se elimino: ofrecia 7 .css que nunca se aplicaban.

    Si alguien lo vuelve a agregar, el usuario elige "dark" y no pasa nada.
    Este test avisa.
    """
    from libs.ComboBox import ComboTema

    combo = ComboTema()
    opciones = [combo.itemText(i) for i in range(combo.count())]
    from libs.Constantes import NOMBRE_PRODUCTO
    assert opciones == [NOMBRE_PRODUCTO], (
        "ComboTema deberia ofrecer solo el tema real; si hay mas de uno, "
        "hay que implementar el selector de verdad o sacarlo de la pantalla. "
        "Ofrece: {}".format(opciones))

    # Y que ningun controlador intente leer o guardar ese parametro.
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent
    for carpeta in ("vistas", "controladores"):
        for ruta in (raiz / carpeta).glob("*.py"):
            texto = ruta.read_text(encoding="utf-8", errors="replace")
            assert "controles['tema']" not in texto, (
                "{} todavia usa controles['tema'], que ya no existe".format(
                    ruta.name))
            assert 'GuardarParametro(parametro="TEMA"' not in texto, (
                "{} todavia guarda el parametro TEMA".format(ruta.name))


# -- 4) Comportamiento de los widgets base ---------------------------------

def test_la_tabla_avisa_cuando_no_tiene_filas(app):
    """El estado vacio se pone solo, sin que el controlador lo pida."""
    from libs.Grillas import Grilla
    grilla = Grilla()
    grilla.ArmaCabeceras(cabeceras=["Cant.", "Detalle", "SubTotal"])
    # Se muestra porque el cartel vive dentro de la tabla: un hijo solo es
    # visible si el padre tambien lo esta.
    grilla.resize(600, 200)
    grilla.show()
    grilla.textoVacio = "Todavia no hay productos"
    app.processEvents()
    assert grilla._etiquetaVacia.isVisible(), "con la tabla vacia no se ve el aviso"

    grilla.AgregaItem(["2", "Tornillo", "1500.00"])
    app.processEvents()
    assert not grilla._etiquetaVacia.isVisible(), "con filas deberia ocultar el aviso"

    grilla.setRowCount(0)
    app.processEvents()
    assert grilla._etiquetaVacia.isVisible(), "al vaciarse deberia volver el aviso"
    grilla.close()


def test_los_botones_aceptar_y_cancelar_estan_en_castellano(app):
    """Qt rotula 'OK' y 'Cancel' en ingles si no se cambian a mano."""
    from PyQt5.QtWidgets import QDialogButtonBox

    from libs.Botones import botonera_dialogo

    caja = botonera_dialogo()
    # Comparacion exacta: "Cancelar" contiene "Cancel", asi que un `in`
    # daria un falso positivo.
    assert caja.button(QDialogButtonBox.Ok).text() == "Aceptar"
    assert caja.button(QDialogButtonBox.Cancel).text() == "Cancelar"

    caja = botonera_dialogo("Guardar y continuar")
    assert caja.button(QDialogButtonBox.Ok).text() == "Guardar y continuar"


def test_los_iconos_de_botones_no_se_pierden_en_su_fondo(app):
    """Un boton primario tiene fondo azul: con el icono azul encima desaparece.

    Se resuelve mirando el archivo del que sale el icono, no comparando
    colores: lo que importa es que el boton Use la variante que corresponda a su
    clase.
    """
    import os

    from PyQt5.QtGui import QImage

    from libs.Botones import Boton
    from libs.recursos import icono, ruta_recurso

    blanco = ruta_recurso("imagenes/iconos/blanco/nuevo.svg")
    rojo = ruta_recurso("imagenes/iconos/peligro/borrar.svg")

    primario = Boton(texto="Nuevo", imagen=icono("nuevo"), estilo="primario")
    peligro = Boton(texto="Borrar", imagen=icono("borrar"), estilo="peligro")
    normal = Boton(texto="Editar", imagen=icono("editar"))

    def coinciden(boton, ruta_variante):
        """El icono del boton es pixel a pixel la variante esperada."""
        pix = boton.icon().pixmap(24, 24)
        if pix.isNull():
            return False
        # QPixmap no tiene pixel(): hay que pasar a QImage para leerlos.
        imagen_boton = pix.toImage()
        ref = QImage(ruta_variante)
        if ref.isNull() or imagen_boton.size() != ref.size():
            return False
        return all(imagen_boton.pixel(x, y) == ref.pixel(x, y)
                   for x in range(imagen_boton.width())
                   for y in range(imagen_boton.height()))

    assert coinciden(primario, blanco), (
        "el boton primario deberia usar el icono en blanco: con el azul sobre "
        "fondo azul el dibujo desaparece")
    assert coinciden(peligro, rojo), (
        "el boton de peligro deberia usar el icono en rojo")
    assert not normal.icon().pixmap(24, 24).isNull()
