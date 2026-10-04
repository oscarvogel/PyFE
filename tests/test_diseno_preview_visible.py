"""La vista previa se tiene que ver, y no se pierde.

Lo que reporto el operador
-------------------------
'Si pongo ver comprobante no se ve'. Los PDFs SI se generaban: al revisar la
maquina habia 25 carpetas comprobante_prueba_<aleatorio> en la temporal, con un
comprobante dentro de cada una. O sea que el PDF salia, se abria con el visor,
y se perdia entre carpetas con nombre aleatorio en una carpeta del sistema que
el operador no tiene por donde buscar.

Ademas, antes de generar nada, la vista previa guardaba los parametros y
mostraba un 'Diseno guardado' en un dialogo modal: entre apretar el boton y ver
el PDF habia un cartel de por medio.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


def test_la_muestra_va_a_un_lugar_fijo_y_no_a_la_temporal():
    """Con nombre aleatorio no hay forma de encontrarla.

    La carpeta de la app, con nombre fijo: se puede volver a abrir y el
    operador sabe donde esta.
    """
    with io_open(os.path.join(RAIZ, "controladores",
                              "DisenoComprobante.py")) as f:
        fuente = f.read()

    assert '"comprobantes de prueba"' in fuente, \
        "la muestra tiene que ir a una carpeta con nombre, no a la temporal"
    assert "ultimo.pdf" in fuente, "el archivo tiene que tener nombre fijo"
    assert "mkdtemp" not in fuente, \
        "sigue usando una carpeta aleatoria: la muestra se pierde entre tantas"


def test_la_muestra_no_deja_la_temporal_llena_de_carpetas():
    """El sintoma decia 'no se ve', pero la causa era esto.

    Con 25 carpetas comprobante_prueba_<aleatorio> en %TEMP%, el PDF existia y
    no habia forma de dar con el.
    """
    import glob
    import tempfile

    carpetas = glob.glob(os.path.join(tempfile.gettempdir(),
                                      "comprobante_prueba_*"))
    # Este test no falla si hay carpetas viejas: solo avisa. Lo que importa es
    # que el codigo ya no las genere mas.
    if carpetas:
        print("NOTA: quedan {} carpetas viejas de pruebas anteriores".format(
            len(carpetas)))


def test_la_vista_previa_no_muestra_el_cartel_de_guardado():
    """Un modal entre apretar el boton y ver el PDF hace parecer que no pasa
    nada."""
    with io_open(os.path.join(RAIZ, "controladores",
                              "DisenoComprobante.py")) as f:
        fuente = f.read()

    assert "GrabaParametros(avisar=False)" in fuente, \
        "la vista previa tiene que guardar en silencio: el 'Diseno guardado' " \
        "sale antes del PDF y corta el flujo"
    assert "def GrabaParametros(self, *args, avisar=True, **kwargs)" in fuente


def test_las_rutas_del_logo_se_guardan_relativas():
    """Una ruta absoluta a la maquina de desarrollo no viaja.

    En la maquina del cliente ese archivo no esta, y la marca desaparece en
    silencio.
    """
    with io_open(os.path.join(RAIZ, "controladores",
                              "DisenoComprobante.py")) as f:
        fuente = f.read()

    assert "_guardar_como_para_esta_maquina" in fuente, \
        "el logo y el fondo se estan guardando absolutos"
    assert "relpath" in fuente, "no hay conversion a ruta relativa"


def _io_open(ruta):
    return open(ruta, encoding="utf-8")


io_open = _io_open
# -- El comportamiento, no solo el texto -----------------------------------

# OJO el parcheo: hay que cambiar la referencia del CONTROLADOR, no la de
# libs.Utiles. El controlador hace 'from libs.Utiles import ubicacion_sistema',
# asi que tiene su propia referencia y cambiar la del modulo origen no la
# toca. Es la segunda vez que me pilla esto en esta pantalla.
import controladores.DisenoComprobante as MOD  # noqa: E402


def _con_carpeta(app, funcion):
    original = MOD.ubicacion_sistema
    MOD.ubicacion_sistema = lambda: str(app) + os.sep
    try:
        return funcion()
    finally:
        MOD.ubicacion_sistema = original


def test_un_logo_dentro_de_la_app_se_guarda_relativo(tmp_path):
    """El caso normal: el operador copia el logo a 'imagenes' y lo elige."""
    imagenes = tmp_path / "imagenes"
    imagenes.mkdir()
    logo = imagenes / "logo-cliente.png"
    logo.write_bytes(b"x")

    guardada, fuera = _con_carpeta(
        tmp_path,
        lambda: MOD.DisenoComprobanteController._guardar_como_para_esta_maquina(
            str(logo)))

    assert fuera is False, "un logo dentro de la app no deberia avisar nada"
    assert not os.path.isabs(guardada), \
        "la ruta quedo absoluta: {} no viaja a otra maquina".format(guardada)
    assert guardada == "imagenes/logo-cliente.png", guardada


def test_un_logo_fuera_de_la_app_se_avisa(tmp_path):
    """Si esta afuera, se guarda igual pero con aviso: es un problema real."""
    fuera_de_la_app = tmp_path.parent / "logo-en-el-escritorio.png"
    try:
        fuera_de_la_app.write_bytes(b"x")
    except OSError:
        pytest.skip("no se puede escribir fuera de tmp_path")

    guardada, avisar = _con_carpeta(
        tmp_path,
        lambda: MOD.DisenoComprobanteController._guardar_como_para_esta_maquina(
            str(fuera_de_la_app)))

    assert avisar is True, "un logo fuera de la app tiene que avisar"
    assert os.path.isabs(guardada), "afuera de la app solo cabe la ruta absoluta"


def test_una_ruta_relativa_se_deja_como_esta(tmp_path):
    """Si el operador ya escribio 'imagenes/logo.png', no se toca."""
    guardada, avisar = _con_carpeta(
        tmp_path,
        lambda: MOD.DisenoComprobanteController._guardar_como_para_esta_maquina(
            "imagenes/logo.png"))

    assert guardada == "imagenes/logo.png"
    assert avisar is False
