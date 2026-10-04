"""La pantalla de diseno del comprobante.

Que resuelve
------------
La capa de marca (FacturaBranding.py, los diez parametros FACTURA_MARCA_*)
existia y funcionaba, pero NADA escribia esos parametros: la marca estaba
desactivada en toda instalacion y para activarla habia que escribir diez filas
en paramsist a mano. El cliente no tenia nada para tocar el diseno de su
factura. Esta pantalla es ese 'algo que los escribe'.

Lo que mas importa probar
-------------------------
La vista previa. Genera un PDF con datos de mentira usando el MISMO metodo que
imprime una factura real, y no puede tocar la base: un comprobante de muestra
que deja una fila en cabfact seria un comprobante fantasma, y uno emitido de
verdad dejaria rastro fiscal contra ARCA, que no se deshace.
"""

import os
import shutil
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

PREFIXO = "FACTURA_MARFA_".replace("MARFA", "MARCA")   # el typo se ve


# -- El color, que es lo que el operador escribe a mano --------------------

@pytest.mark.parametrize("entrada,esperado", [
    ("#0F2A44", "#0F2A44"),
    ("0F2A44", "#0F2A44"),
    ("0f2a44", "#0F2A44"),
    ("  #0f2a44  ", "#0F2A44"),
    ("#F2A900", "#F2A900"),
])
def test_un_color_se_normaliza(entrada, esperado):
    """Se acepta con o sin # y en minusculas: se pega de donde se pueda."""
    from vistas.DisenoComprobante import normalizar_color
    assert normalizar_color(entrada) == esperado


@pytest.mark.parametrize("entrada", ["", "   ", "#12345", "rojo", "#GGGGGG",
                                    "0F2A4", "#0F2A44BB", None])
def test_un_color_invalido_se_rechaza(entrada):
    """Un color que no se puede convertir tiene que verse raro antes de
    guardarse, no pasar al comprobante."""
    from vistas.DisenoComprobante import normalizar_color
    assert normalizar_color(entrada) is None


# -- Los parametros --------------------------------------------------------

@pytest.fixture
def controlador(qt, tmp_path, monkeypatch):
    """La pantalla real, con su base propia y la carpeta de trabajo en tmp."""
    from peewee import SqliteDatabase
    from modelos.ParametrosSistema import ParamSist
    import modelos.ParametrosSistema as MP

    shutil.copytree(os.path.join(RAIZ, "plantillas"),
                    str(tmp_path / "plantillas"), dirs_exist_ok=True)
    monkeypatch.chdir(tmp_path)

    original = MP.ParamSist._meta.database
    db = SqliteDatabase(":memory:")
    MP.ParamSist._meta.set_database(db)
    db.create_tables([ParamSist])

    from controladores.DisenoComprobante import DisenoComprobanteController
    c = DisenoComprobanteController()
    c.view.Cerrar = lambda: None
    yield c
    MP.ParamSist._meta.set_database(original)


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_los_parametros_se_guardan(controlador):
    from modelos.ParametrosSistema import ParamSist

    controlador.view.controles['activa'].setIndex("S")
    controlador.view.controles['web'].setText("www.miestudio.com")
    controlador.view.controles['leyenda'].setText("MI ESTUDIO")
    controlador.view.controles['logo'].setText("")
    controlador.view.controles['fondo'].setText("")
    controlador.view.controles['color_primario'].setText("112233")

    assert controlador.GrabaParametros() is True

    leidos = {p.parametro: p.valor
              for p in ParamSist.select()
              if p.parametro.startswith(PREFIXO)}
    assert leidos[PREFIXO + "ACTIVA"] == "S"
    assert leidos[PREFIXO + "WEB"] == "www.miestudio.com"
    assert leidos[PREFIXO + "COLOR_PRIMARIO"] == "#112233", \
        "el color se guardó sin la almohadilla: {}".format(
            leidos[PREFIXO + "COLOR_PRIMARIO"])


def test_se_guardan_los_diez(controlador):
    """La capa de marca lee diez. Si se guarda menos, la marca no anda."""
    from modelos.ParametrosSistema import ParamSist

    controlador.GrabaParametros()

    for clave in ("ACTIVA", "FORMATO", "LOGO", "FONDO", "WEB", "LEYENDA",
                  "COLOR_PRIMARIO", "COLOR_SECUNDARIO", "COLOR_ACENTO",
                  "COLOR_TEXTO_SECUNDARIO"):
        nombre = PREFIXO + clave
        assert ParamSist.get_or_none(ParamSist.parametro == nombre) is not None, \
            "no se guardo {}".format(nombre)


def test_la_ida_y_la_vuelta(controlador):
    """Guardar y recargar tiene que dar lo mismo."""
    from modelos.ParametrosSistema import ParamSist

    controlador.view.controles['web'].setText("www.vuelta.com")
    controlador.view.controles['color_acento'].setText("#ABCDEF")
    controlador.GrabaParametros()
    ParamSist.delete().where(ParamSist.parametro == PREFIXO + "ACTIVA").execute()

    controlador.CargaDatos()

    assert controlador.view.controles['web'].text() == "www.vuelta.com"
    assert controlador.view.controles['color_acento'].text() == "#ABCDEF"


def test_un_color_invalido_no_se_guarda(controlador):
    """Con un color roto no se guarda nada: partly guardado es peor que nada."""
    from modelos.ParametrosSistema import ParamSist

    controlador.view.controles['web'].setText("www.miestudio.com")
    controlador.view.controles['color_primario'].setText("no soy un color")

    assert controlador.GrabaParametros() is False
    assert ParamSist.get_or_none(
        ParamSist.parametro == PREFIXO + "WEB") is None, \
        "guardo la mitad de los parametros con un color roto"


def test_un_logo_inexistente_no_se_guarda(controlador):
    from modelos.ParametrosSistema import ParamSist

    controlador.view.controles['logo'].setText("no/existe/logo.png")

    assert controlador.GrabaParametros() is False
    assert ParamSist.get_or_none(
        ParamSist.parametro == PREFIXO + "LOGO") is None


def test_los_textos_se_cortan_al_largo_que_aguenta(controlador):
    """La web y la leyenda van en el encabezado del comprobante."""
    from modelos.ParametrosSistema import ParamSist
    from vistas.DisenoComprobante import LIMITE_LEYENDA, LIMITE_WEB

    controlador.view.controles['web'].setText("w" * (LIMITE_WEB + 20))
    controlador.view.controles['leyenda'].setText("l" * (LIMITE_LEYENDA + 20))
    controlador.GrabaParametros()

    web = ParamSist.get(ParamSist.parametro == PREFIXO + "WEB").valor
    leyenda = ParamSist.get(ParamSist.parametro == PREFIXO + "LEYENDA").valor
    assert len(web) == LIMITE_WEB
    assert len(leyenda) == LIMITE_LEYENDA
