# coding=utf-8
"""Test de la navegacion: toda accion declarada tiene que existir de verdad.

Por que existe
--------------
Antes, la pantalla principal era una fila de 9 botones y cada uno abria un
QMenu que se comparaba con una cadena de if/elif. De ahi salio un bug que
llevo años oculto: los cinco modulos de Compras (Proveedores, Centros de costo,
Carga de comprobantes, IVA compras y RG 3685 compras) estaban escritos, con su
controlador y su vista, y NO habia ningun boton que los abriera. El codigo
funcionaba perfecto y era inalcanzable.

Nada en el codigo hacia ruido por eso, y no hay forma de detectarlo salvo
preguntandose "estapantalla, se abre?". Estos tests lo convierten en una
pregunta automatica:

  1. toda clave declarada en la vista tiene un destino en el controlador
  2. ningun destino sobra (o sea, no queda una accion huérfana al reescribir)
  3. toda accion tiene icono, y el icono existe de verdad
  4. las claves no se repiten
  5. Compras sigue exposure (si alguien la saca de nuevo, avisa)

No necesita base de datos ni ARCA: lee las listas y monta la vista offscreen.
"""

import ast
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from PyQt5.QtWidgets import QApplication  # noqa: E402

# Las cinco acciones que estuvieron inalcanzables. Si vuelven a desaparecer de
# la navegacion, este test lo dice.
COMPRAS = [
    "proveedores",
    "centro-costos",
    "carga-facturas",
    "iva-compras",
    "rg3685-compras",
]


@pytest.fixture(scope="module")
def app():
    aplicacion = QApplication.instance() or QApplication(sys.argv)
    from libs.tema import aplicar_tema
    aplicar_tema(aplicacion)
    return aplicacion


@pytest.fixture(scope="module")
def vista(app):
    from vistas.Main import MainView
    v = MainView()
    v.initUi()
    v.show()
    app.processEvents()
    return v


def _acciones_de_la_vista():
    from vistas.Main import SECCIONES
    acciones = []
    for _titulo, _icono, items in SECCIONES:
        for clave, texto, icono in items:
            acciones.append((clave, texto, icono))
    return acciones


def _claves_de_destinos():
    """Claves del mapa DESTINOS, leidas del fuente.

    Se lee el codigo y no se instancia Main: Main abre la base de datos en el
    __init__, y este test tiene que correr sin ella.
    """
    ruta = os.path.join(RAIZ, "controladores", "Main.py")
    with open(ruta, "r", encoding="utf-8", errors="replace") as f:
        arbol = ast.parse(f.read(), filename=ruta)

    claves = set()
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.FunctionDef) or nodo.name != "DESTINOS":
            continue
        for asginado in ast.walk(nodo):
            if (isinstance(asginado, ast.Dict) and asginado.keys):
                for clave in asginado.keys:
                    if isinstance(clave, ast.Constant) and isinstance(clave.value, str):
                        claves.add(clave.value)
    return claves


# -- Estructura de la navegacion -------------------------------------------

def test_hay_navegacion():
    acciones = _acciones_de_la_vista()
    assert len(acciones) >= 25, (
        "la navegacion deberia exponer unas 30 acciones, hay {}".format(len(acciones)))


def test_las_claves_no_se_repiten():
    acciones = _acciones_de_la_vista()
    claves = [c for c, _t, _i in acciones]
    repetidas = {c for c in claves if claves.count(c) > 1}
    assert not repetidas, "claves repetidas en la navegacion: {}".format(repetidas)


def test_toda_accion_tiene_destino(vista, app):
    """La comprobacion central: nada puede quedar sin conectar."""
    destinos = _claves_de_destinos()
    faltan = [clave for clave, _t, _i in _acciones_de_la_vista()
              if clave not in destinos]
    assert not faltan, (
        "acciones declaradas sin destino: {}. Es el bug que dejo Purchases "
        "escrito pero inalcanzable.".format(faltan))


def test_no_sobran_destinos():
    """Un destino que no esta en la vista es codigo muerto."""
    acciones = {clave for clave, _t, _i in _acciones_de_la_vista()}
    sobran = _claves_de_destinos() - acciones
    assert not sobran, "destinos que no corresponden a ninguna accion: {}".format(sobran)


def test_compras_esta_exposta():
    """Las cinco acciones de Compras tienen que estar en la navegacion."""
    acciones = {clave for clave, _t, _i in _acciones_de_la_vista()}
    faltan = [c for c in COMPRAS if c not in acciones]
    assert not faltan, (
        "acciones de Compras que volvieron a quedar inalcanzables: {}".format(faltan))


# -- Iconos ----------------------------------------------------------------

def test_toda_accion_tiene_un_icono_existente():
    from libs.recursos import ruta_recurso

    faltan = []
    for clave, texto, nombre in _acciones_de_la_vista():
        if not nombre:
            faltan.append("{} ({}) no declara icono".format(clave, texto))
            continue
        if not ruta_recurso("imagenes/iconos/{}.svg".format(nombre)):
            faltan.append("{} usa '{}', que no existe en imagenes/iconos/".format(
                clave, nombre))
    assert not faltan, "iconos de la navegacion:\n  " + "\n  ".join(faltan)


def test_los_iconos_se_ven_en_la_barra_lateral(vista):
    """Un boton sin icono en la barra lateral se ve desalineado del resto.

    Conviene revisarlo sobre la vista armada, y no solo sobre la lista: asi se
    detecta el caso en que el archivo existe pero QIcon no lo carga.
    """
    from PyQt5.QtGui import QIcon

    sin_icono = []
    for clave, boton in vista.botonesNav.items():
        if boton.icon().isNull() or QIcon(boton.icon()).isNull():
            sin_icono.append(clave)
    assert not sin_icono, "botones de la barra lateral sin icono: {}".format(sin_icono)


# -- Armazon ---------------------------------------------------------------

def test_la_vista_expone_el_modo_homologacion(vista):
    """El modo tiene que estar escrito en pantalla, no solo en un print."""
    texto = vista.chipModo.text()
    assert texto, "el chip de modo esta vacio"
    assert ("HOMOLOGACIÓN" in texto) or ("PRODUCCIÓN" in texto), (
        "el chip de modo no dice en que modo esta: {!r}".format(texto))


def test_la_barra_de_estado_tiene_datos(vista):
    for etiqueta in (vista.lblPuntoVenta, vista.lblArca, vista.lblResguardo,
                     vista.lblVersion):
        assert etiqueta.objectName() == "datoEstado"
        assert etiqueta.minimumWidth() == 0, (
            "{} tiene minimumWidth fijo: un dato mas largo volveria a "
            "inflar la ventana".format(etiqueta.objectName()))
    assert vista.lblArca.text(), "la barra de estado no dice nada del estado de ARCA"


def test_la_barra_de_estado_no_repite_lo_del_encabezado(vista, app):
    """Modo y CUIT ya estan en el encabezado.

    Estaban tambien en la barra de estado, y con eso la barra sumaba 1094 px de
    ancho minimo: en una pantalla de 1024 empujaba el contenido de la derecha
    fuera de la vista.
    """
    assert not hasattr(vista, "lblModo"), (
        "el modo ya se ve en el chip del encabezado; si vuelve a la barra de "
        "estado, la ventana se agranda sin necesidad")
    assert not hasattr(vista, "lblCuit"), (
        "el CUIT ya se ve con la empresa en el encabezado; repetirlo agranda "
        "la ventana sin necesidad")


def test_el_panel_de_bienvenida_ofrece_solo_acciones_validas(vista):
    from vistas.Main import ACCIONES_RAPIDAS

    acciones = {clave for clave, _t, _i in _acciones_de_la_vista()}
    huerfanas = [clave for clave, _t, _d, _i in ACCIONES_RAPIDAS
                 if clave not in acciones]
    assert not huerfanas, (
        "la bienvenida ofrece acciones que no existen en la navegacion: {}".format(
            huerfanas))


def test_navegar_a_una_clave_inexistente_no_revienta(vista):
    """Una clave desconocida tiene que avisar, no romper con un AttributeError."""
    # No se conecta el controlador aca (abriria la base): se verifica que la
    # vista emita cualquier clave sin error.
    recibido = []
    vista.navegar.connect(recibido.append)
    vista.navegar.emit("una-clave-que-no-existe")
    assert recibido == ["una-clave-que-no-existe"]


# -- Interaccion -----------------------------------------------------------
#
# Estas pruebas existen por un bug concreto: los botones de la barra lateral se
# creaban y se dibujaban bien, pero nunca se conecto su clicked con la senal
# navegar. Clic no pasaba nada y no habia ningun error en ninguna parte: solo
# se descubria probando la aplicacion. Montar la vista no alcanza para
# encontrarlo, hay que hacer clic de verdad.

def test_todos_los_botones_de_la_barra_emiten_su_clave(vista, app):
    """Cada boton de la barra tiene que emitir SU clave, no una sola."""
    # Se reemplaza emitir por una espia para no abrir ninguna pantalla.
    emitted = []
    vista.navegar.disconnect()
    vista.navegar.connect(emitted.append)

    for clave, boton in vista.botonesNav.items():
        boton.click()
        app.processEvents()
        assert emitted == [clave], (
            "el boton {!r} emitio {} en vez de su propia clave".format(
                boton.text(), emitted))
        emitted.clear()


def test_el_grupo_de_la_barra_es_exclusivo(vista, app):
    """Solo una seccion puede quedar marcada a la vez."""
    primero = vista.botonesNav["nueva-venta"]
    segundo = vista.botonesNav["proveedores"]

    primero.setChecked(True)
    app.processEvents()
    segundo.setChecked(True)
    app.processEvents()

    assert not primero.isChecked(), "se pueden marcar dos secciones a la vez"
    assert segundo.isChecked()


def test_las_tarjetas_de_bienvenida_emiten_su_clave(vista, app):
    emitted = []
    vista.navegar.disconnect()
    vista.navegar.connect(emitted.append)

    from PyQt5.QtWidgets import QPushButton
    for boton in vista.panelBienvenida.findChildren(QPushButton):
        if boton.objectName() == "botonTarjeta":
            boton.click()
            app.processEvents()
    assert emitted, "las tarjetas de bienvenida no emitieron nada"
    acciones = {clave for clave, _t, _i in _acciones_de_la_vista()}
    assert all(c in acciones for c in emitted), (
        "las tarjetas emiten claves que no existen: {}".format(emitted))
