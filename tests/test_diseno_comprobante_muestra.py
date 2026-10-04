# coding=utf-8
"""La vista previa genera un PDF sin tocar la base.

Por que esta prueba es la importante
-----------------------------------
La vista previa existe para que el cliente vea si le gusta su diseno sin
emitir. Si tocara la base dejaria un comprobante fantasma en cabfact, que
despues aparece en los listados, en los libros de IVA y en los informes. Y si
probara con una factura real dejaria rastro fiscal contra ARCA, que no se
puede deshacer.

Que usa el codigo de la impresion real
--------------------------------------
La muestra la arma FacturaController._armar_comprobante, el mismo metodo que
imprime una factura. Si la vista previa usara otro camino, mostraria un diseno
que la app no usa, que es justo el problema que viene a resolver.
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


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def mundo(qt, tmp_path, monkeypatch):
    """La pantalla con TODO alrededor real: base, plantillas y archivos.

    Menos cosas falseadas, mas chances de que la prueba sirva.
    """
    from peewee import SqliteDatabase
    import modelos.ParametrosSistema as MP
    from modelos.ParametrosSistema import ParamSist

    shutil.copytree(os.path.join(RAIZ, "plantillas"),
                    str(tmp_path / "plantillas"), dirs_exist_ok=True)
    # Un logo de mentira para probar la capa de marca de verdad.
    import PIL.Image
    logo = tmp_path / "plantillas" / "logo_prueba.png"
    PIL.Image.new("RGBA", (120, 40), (15, 42, 68, 255)).save(str(logo))

    # El sistema.ini va ANTES de importar los modelos: ModeloBase decide entre
    # sqlite y mysql AL IMPORTARSE, leyendo 'base' del .ini. Sin el archivo
    # cae en la rama de mysql, que no conecta, y todo lo que lea la base
    # revienta con 'database must be initialized'. En la app real el archivo
    # siempre esta: lo escribe el asistente.
    # Con CUIT, como en una instalacion de verdad: lo carga el asistente de
    # primer arranque y el codigo del QR lo necesita.
    (tmp_path / "sistema.ini").write_text(
        "[param]\nbase = sqlite\nusa_nombre_db = S\n"
        "basedatos = muestra\nhomo = S\n"
        "nombre_sistema = Prueba\nconfigurado = S\n"
        "\n[FACTURA]\nempresa = MI ESTUDIO\nmembrete1 = Una calle 123\n"
        "membrete2 = \ncuit = 20-23347203-5\niibb = 20233472035\n"
        "iva = Responsable Inscripto\ninicio = 01/01/2020\n",
        encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    original = MP.ParamSist._meta.database
    db = SqliteDatabase(":memory:")
    MP.ParamSist._meta.set_database(db)
    db.create_tables([ParamSist])
    # connect() y no alcanza con crear las tablas: _armar_comprobante LEE
    # parametros (el fondo, la marca) a traves de ParamSist, y sin una conexion
    # peewee tira 'database must be initialized'. Leer no es escribir: la base
    # sigue sin filas.
    db.connect(reuse_if_open=True)

    # Los avisos se anotan en vez de abrirse: en un test no hay operador que
    # los cierre, y ademas son la unica explicacion de un False.
    import libs.Ventanas as V
    mostrados = []
    originales = (V.showAlert, V.showError, V.showConfirmation)
    V.showAlert = lambda t, m, *a, **k: mostrados.append(("alert", t, m))
    V.showError = lambda t, m, que_hacer=None, detalle=None: mostrados.append(
        ("error", t, "{} :: {}".format(m, detalle)))
    V.showConfirmation = lambda t, m, **kw: mostrados.append(("confirm", t, m)) or True

    # ubicacion_sistema() deduce la carpeta de donde corre el ejecutable. Bajo
    # pytest eso es la carpeta de pytest, y el codigo busca plantillas/ en el
    # lugar equivocado. En la app real siempre da bien, asi que se parchea
    # solo para el test.
    import libs.Utiles as U
    import controladores.Facturas as FACMOD
    original_ubicacion = (U.ubicacion_sistema, FACMOD.ubicacion_sistema)
    U.ubicacion_sistema = lambda: str(tmp_path) + os.sep
    FACMOD.ubicacion_sistema = lambda: str(tmp_path) + os.sep

    import controladores.DisenoComprobante as MOD
    original_abrir = MOD.DisenoComprobanteController._abrir_muestra
    MOD.DisenoComprobanteController._abrir_muestra = staticmethod(
        lambda salida: True)          # no abrir un visor en un test
    c = MOD.DisenoComprobanteController()
    c.view.Cerrar = lambda: None
    yield c, db, mostrados
    MOD.DisenoComprobanteController._abrir_muestra = original_abrir
    MP.ParamSist._meta.set_database(original)
    V.showAlert, V.showError, V.showConfirmation = originales
    U.ubicacion_sistema, FACMOD.ubicacion_sistema = original_ubicacion


def test_la_muestra_genera_un_pdf(mundo):
    """Sin marca y sin tocar nada mas: tiene que salir un PDF."""
    controlador, _db, avisos = mundo

    assert controlador.VerComprobanteDePrueba() is True, \
        "la vista previa fallo y no dijo por que: {}".format(avisos)


def test_la_muestra_no_toca_la_base(mundo):
    """Lo unico que no puede pasar: dejar un comprobante en la base.

    Se mira el archivo, no un doble: si la vista previa escribiera en la base,
    en el archivo de sqlite Habria un cabfact.db.
    """
    controlador, db, _avisos = mundo

    controlador.VerComprobanteDePrueba()

    # La base del test es un :memory:, asi que se consulta por el mismo camino.
    assert _contar_cabfact(db) == 0, \
        "la vista previa escribio {} filas en cabfact".format(
            _contar_cabfact(db))


def _contar_cabfact(db):
    try:
        return db.execute_sql("select count(*) from cabfact").fetchone()[0]
    except Exception:
        return 0


def test_la_muestra_no_toca_la_base_real(mundo, tmp_path):
    """La comprobacion de verdad: el archivo sqlite en disco, sin dobles.

    El otro test mira la base en memoria. Este mira el ARCHIVO, que es donde
    una escritura real caeria, asi que aunque el codigo usara otra conexion
    se veria.
    """
    import sqlite3

    controlador, db, _avisos = mundo
    ruta = str(tmp_path / "muestra.db")
    db.close()
    import sqlite3 as s
    conexion = s.connect(ruta)
    conexion.execute(
        "create table if not exists cabfact (idcabfact integer primary key, "
        "numero text)")
    conexion.commit()
    conexion.close()

    antes = os.path.getsize(ruta)

    controlador.VerComprobanteDePrueba()

    assert os.path.getsize(ruta) == antes, \
        "la vista previa escribo en la base de datos"


def test_guarda_la_marca_antes_de_generar_la_muestra(mundo):
    """Si no guarda antes, la muestra sale con el diseno de antes.

    Y el operador no ve diferencia entre el boton que no hizo nada y el que
    fallo. Es el error mas silencioso posible de esta pantalla.
    """
    from modelos.ParametrosSistema import ParamSist

    controlador, _db, _avisos = mundo
    controlador.view.controles['activa'].setIndex("S")
    controlador.view.controles['logo'].setText("plantillas/logo_prueba.png")
    controlador.view.controles['web'].setText("www.miprueba.com")

    controlador.VerComprobanteDePrueba()

    activa = ParamSist.get(ParamSist.parametro == "FACTURA_MARCA_ACTIVA")
    assert activa.valor == "S", "la muestra no guardo la marca antes de generar"
    logo = ParamSist.get(ParamSist.parametro == "FACTURA_MARCA_LOGO")
    assert logo.valor == "plantillas/logo_prueba.png"


def test_el_pdf_de_la_muestra_queda_en_la_temporal(mundo):
    """No en la carpeta facturas/, que es donde van las facturas de verdad."""
    import glob

    controlador, _db, avisos = mundo
    assert controlador.VerComprobanteDePrueba() is True, \
        "la vista previa fallo: {}".format(avisos)

    assert not os.path.isdir("facturas"), \
        "la muestra escribio en la carpeta de facturas de verdad"
    muestras = glob.glob(os.path.join(tempfile.gettempdir(),
                                      "comprobante_prueba_*", "*.pdf"))
    assert muestras, "no se encontro ningun PDF de muestra"
