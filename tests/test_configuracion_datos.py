"""Configuracion: los datos de la empresa se pueden corregir despues.

Que estaba pasando
------------------
El asistente de primer arranque pregunta punto de venta e inicio de actividades
y los escribe en el .ini, pero Configuracion no los leia ni los escribia. Cargarlos
mal era cosa de editar el archivo a mano.

La condicion frente al IVA ([FACTURA] iva) no la escribia NADIE: ni el asistente
ni Configuracion. Se imprime en el pie de cada factura, asi que en una
instalacion nueva esa linea salia en blanco.

Y el combo de categoria de IVA tenia 3 codigos (1, 4, 6) mientras que ARCA define
diez. Con una categoria fuera de esos tres, que es lo normal en un estudio
contabile, setIndex no encontraba el dato, el combo se vaciaba, y al guardar el
cat_iva quedaba en blanco. O sea: abrir Configuracion y apretar Grabar le
boraba la categoria de IVA a la empresa. Ese es el bug que estos tests fijan.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def configuracion(qt, tmp_path, monkeypatch):
    """Una Configuracion real, con su .ini en una carpeta temporal.

    El archivo de configuracion se resuelve con la carpeta de trabajo, asi que
    sin cambiar a tmp_path cada prueba leeria y escribiria el sistema.ini de la
    maquina del desarrollador.
    """
    monkeypatch.chdir(tmp_path)

    import libs.Utiles as U
    monkeypatch.setattr(U, "carpeta_de_trabajo", lambda: str(tmp_path),
                        raising=False)

    from libs.Utiles import GrabarIni
    GrabarIni(clave="nombre_sistema", key="param", valor="Prueba")

    from controladores.Configuracion import ConfiguracionController
    c = ConfiguracionController()
    c.view.show()
    qt.processEvents()
    yield c
    c.view.Cerrar()


# -- Los dos campos que faltaban -------------------------------------------

def test_el_punto_de_venta_ida_y_vuelta(configuracion):
    from libs.Utiles import LeerIni

    configuracion.view.controles["pto_vta"].setText("3")
    configuracion.GrabaParametros()

    assert LeerIni(clave="pto_vta", key="WSFEv1") == "3"


def test_el_inicio_de_actividades_ida_y_vuelta(configuracion):
    from libs.Utiles import LeerIni

    configuracion.view.controles["inicio"].setText("01/03/2024")
    configuracion.GrabaParametros()

    assert LeerIni(clave="inicio", key="FACTURA") == "01/03/2024"


def test_cargar_devuelve_lo_que_esta_guardado(configuracion):
    """La vuelta: guardar, recargar y que siga ahi."""
    from libs.Utiles import GrabarIni, LeerIni

    GrabarIni(clave="pto_vta", key="WSFEv1", valor="7")
    GrabarIni(clave="inicio", key="FACTURA", valor="15/08/2020")

    configuracion.CargaDatos()

    assert configuracion.view.controles["pto_vta"].text() == "7"
    assert configuracion.view.controles["inicio"].text() == "15/08/2020"


# -- La condicion frente al IVA --------------------------------------------

def test_la_condicion_de_iva_se_arma_sola(configuracion):
    """Antes no la escribia nadie, y salia en blanco en cada comprobante."""
    from libs.Utiles import LeerIni

    configuracion.view.controles["cat_iva"].setIndex("1")
    configuracion.GrabaParametros()

    iva = LeerIni(clave="iva", key="FACTURA")
    assert iva, "la condicion de IVA quedo vacia"
    assert "Inscripto" in iva


def test_cambiar_la_categoria_cambia_la_condicion(configuracion):
    from libs.Utiles import GrabarIni, LeerIni

    GrabarIni(clave="iva", key="FACTURA", valor="")
    configuracion.view.controles["cat_iva"].setIndex("6")
    configuracion.GrabaParametros()

    assert "Monotributo" in LeerIni(clave="iva", key="FACTURA")


def test_no_una_condicion_que_alguien_ya_escribio_a_mano(configuracion):
    """Si esta escrito, se respeta: puede ser algo que la app no conoce."""
    from libs.Utiles import GrabarIni, LeerIni

    GrabarIni(clave="iva", key="FACTURA", valor="RESPONSABLE INCRIPC")
    configuracion.view.controles["cat_iva"].setIndex("1")
    configuracion.GrabaParametros()

    assert LeerIni(clave="iva", key="FACTURA") == "RESPONSABLE INCRIPC"


# -- El combo, que es donde estaba el bug ----------------------------------

def test_el_combo_tiene_los_diez_codigos_de_arca(configuracion):
    from libs.catalogos import CATEGORIAS_IVA_EMISOR

    combo = configuracion.view.controles["cat_iva"]
    assert combo.count() == len(CATEGORIAS_IVA_EMISOR)


@pytest.mark.parametrize("codigo", ["1", "4", "5", "6", "7", "8", "9", "10",
                                    "13", "16"])
def test_ninguna_categoria_se_borra_al_guardar(configuracion, codigo):
    """El bug: con una categoria fuera de {1,4,6} el combo se vaciaba.

    Grabar era lo que lo rompia, asi que el test graba: es el camino completo
    que hacia falta, y no solo un setIndex que podria pasar sin guardar.
    """
    from libs.Utiles import GrabarIni, LeerIni

    GrabarIni(clave="cat_iva", key="WSFEv1", valor=codigo)
    configuracion.CargaDatos()
    configuracion.GrabaParametros()

    assert LeerIni(clave="cat_iva", key="WSFEv1") == codigo, \
        "el cat_iva {} se perdio al guardar Configuracion".format(codigo)


def test_cargar_una_categoria_no_perdida_deja_el_combo_seleccionado(
        configuracion):
    from libs.Utiles import GrabarIni

    GrabarIni(clave="cat_iva", key="WSFEv1", valor="9")
    configuracion.CargaDatos()

    assert configuracion.view.controles["cat_iva"].text() == "9"


# -- El asistente de primer arranque usa la misma lista ---------------------

def test_el_asistente_ofrece_los_mismos_codigos_que_la_configuracion():
    """Dos pantallas distintos, el mismo catalogo.

    Antes tenian listas propias y distintas: la del asistente tenia 8 y la de
    Configuracion 3. Ninguna era fuente de verdad.
    """
    import os
    sys.path.insert(0, RAIZ)
    from vistas.PrimerArranque import _categorias_iva
    from libs.catalogos import CATEGORIAS_IVA_EMISOR

    del_asistente = sorted(valor for etiqueta, valor in _categorias_iva())
    del_catalogo = sorted(str(c) for c, etiqueta in CATEGORIAS_IVA_EMISOR)

    assert del_asistente == del_catalogo

