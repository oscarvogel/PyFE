"""Los tres problemas que reporto el operador al usar la pantalla.

1. Al apretar el boton del logo se abria un dialogo de GUARDAR, que preguntaba
   si pisaba el archivo. Para elegir una imagen que ya esta tiene que ser de
   ABRIR. Inversion mia: puse guardar=True en los dos.

2. Los botones no tenian icono. Dos errores encadenados:

   a) Boton toma el icono por el kwarg 'imagen', no 'icono'. El segundo lo
      ignora en silencio: el boton queda pelado y no dice nada.
   b) icono('nombre') busca en imagenes/iconos/<nombre>.svg, el set NUEVO
      monoline. Los PNG de imagenes/ son el set VIEJO y no los mira salvo que
      se le pase un 'alterno'. Asi que icono('print') devuelve '' aunque
      exista imagenes/print.png.

   Los tests miran el icono YA PUESTO en el boton, no el argumento con el que
   se creo: un kwarg mal escrito deja el boton pelado sin dar ningun error, y
   un test que mirara el codigo pasaria.

3. La vista previa salio SIN las lineas de la grilla ni los cuadros de los
   totales. No era un falla del preview: activar la marca cambiaba la plantilla
   del comprobante por factura_marca.csv, que es un diseno mas pobre. O sea
   que 'usar diseno propio' hacia perder el formato fiscal.
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
def vista(qt):
    from vistas.DisenoComprobante import DisenoComprobanteView
    v = DisenoComprobanteView()
    yield v
    v.close()


# -- 1. Los botones de archivo abren ---------------------------------------

@pytest.mark.parametrize("boton", ["btnArchivoLogo", "btnArchivoFondo"])
def test_el_boton_de_imagen_abre_y_no_guarda(vista, boton):
    """Elegir una imagen que ya existe, no crear una.

    Con guardar=True el dialogo es de guardar: Windows pregunta si pisa el
    archivo y el nombre viene precargado con algo inventado. Eso es al reves
    de lo que quiere el operador.
    """
    assert getattr(vista, boton).guardar is False, \
        "{} esta en modo guardar: deberia abrir".format(boton)


# -- 2. Los iconos ----------------------------------------------------------

@pytest.mark.parametrize("nombre", ["btnArchivoLogo", "btnArchivoFondo",
                                    "btnProbar", "btnGrabar", "btnCerrar"])
def test_los_botones_tienen_icono(vista, nombre):
    """Que el icono no este no se ve en ningun lado: se mira el boton."""
    boton = getattr(vista, nombre)
    assert not boton.icon().isNull(), \
        "{} quedo sin icono. Recordar: el kwarg es 'imagen', no 'icono'; y " \
        "icono() busca en imagenes/iconos/<nombre>.svg, no en los PNG " \
        "de imagenes/.".format(nombre)


@pytest.mark.parametrize("nombre", ["carpeta", "imprimir", "guardar",
                                    "editar", "cerrar"])
def test_los_iconos_que_usa_la_pantalla_existen(nombre):
    """Que el nombre este en el set nuevo.

    Si el nombre no existe, icono() devuelve cadena vacia y el boton queda sin
    icono sin decir nada. Estos son los que usa la pantalla.
    """
    from libs.recursos import icono
    assert icono(nombre), \
        "el icono {!r} no existe en imagenes/iconos/".format(nombre)


# -- 3. La marca no cambia la plantilla del comprobante --------------------

class _Config(object):
    activa = True
    formato = ""          # vacio = usar la plantilla fiscal de siempre
    logo = ""
    fondo = ""
    web = ""
    leyenda = ""
    color_primario = "#0F2A44"
    color_secundario = "#0B2035"
    color_acento = "#F2A900"
    color_texto_secundario = "#8EA8C3"


def test_activar_la_marca_no_cambia_la_plantilla(tmp_path):
    """Con la marca activa y sin plantilla a proposito, se usa la de siempre.

    Este es el que arregla lo que vio el operador: la vista previa salia sin
    las lineas de la grilla porque factura_marca.csv, un diseno mas pobre,
    reemplazaba a la plantilla fiscal.
    """
    from controladores.FacturaBranding import obtener_formato_factura

    por_defecto = "plantillas/factura_qr.csv"
    elegido = obtener_formato_factura(str(tmp_path), _Config(), por_defecto)

    assert os.path.basename(str(elegido)) == os.path.basename(por_defecto), \
        "activar la marca cambio la plantilla a {}: el comprobante pierde las " \
        "lineas y los cuadros del formato fiscal".format(elegido)


def test_una_plantilla_elegida_a_proposito_si_se_usa(tmp_path):
    """Si el operador pone una ruta, esa gana. Para el que quiera otro reparto."""
    from controladores.FacturaBranding import obtener_formato_factura

    alternativa = tmp_path / "mi_plantilla.csv"
    alternativa.write_text("campo;texto\n", encoding="utf-8")

    config = _Config()
    config.formato = str(alternativa)
    elegido = obtener_formato_factura(str(tmp_path), config,
                                      "plantillas/factura_qr.csv")
    assert os.path.samefile(str(elegido), str(alternativa))


def test_una_plantilla_que_no_existe_cae_en_la_de_siempre(tmp_path):
    """Si la ruta puesta no existe, no se queda sin comprobante."""
    from controladores.FacturaBranding import obtener_formato_factura

    config = _Config()
    config.formato = "no/existe/plantilla.csv"
    elegido = obtener_formato_factura(str(tmp_path), config,
                                      "plantillas/factura_qr.csv")
    assert os.path.basename(str(elegido)) == "factura_qr.csv"


def test_el_default_de_la_plantilla_es_vacio():
    """El default de la pantalla tiene que ser vacio.

    Si volviera a 'plantillas/factura_marca.csv', guardar con el campo vacio no
    serviria de nada: al recargar, la config diria que la plantilla es la de
    marca y el comprobante volveria a salir sin las lineas ni los cuadros.
    """
    from peewee import SqliteDatabase
    import modelos.ParametrosSistema as MP
    from modelos.ParametrosSistema import ParamSist

    db = SqliteDatabase(":memory:")
    original = MP.ParamSist._meta.database
    MP.ParamSist._meta.set_database(db)
    try:
        db.create_tables([ParamSist])
        db.connect(reuse_if_open=True)
        # Sin filas: es lo que hay en una base recien creada, con la marca
        # todavia sin configurar.
        assert ParamSist.select().count() == 0

        from controladores.FacturaBranding import cargar_config_marca_factura
        config = cargar_config_marca_factura()
    finally:
        MP.ParamSist._meta.set_database(original)

    assert config.formato == "", \
        "el default sigue siendo {!r}: activar la marca va a seguir " \
        "cambiando la plantilla del comprobante por una sin lineas ni " \
        "cuadros".format(config.formato)
