"""El PDF de la factura se arma de verdad, no con dobles.

Que estaba pasando
------------------
`pyfpdf.AggregarDato(...)`, con doble g. El metodo se llama `AgregarDato`.
Con eso, ImprimeFactura revienta con AttributeError y la factura NO se
imprime: queda autorizada en ARCA y sin comprobante para entregar. Y en
Remitos.py, el mismo typo, con el mismo efecto en el remito.

La suite entera pasaba en verde. No porque el error fuera invisible, sino
porque ImprimeFactura necesita una factura en la base y ningun test la armaba:
todos los que tocan esta parte usan dobles, y un doble que envuelve a
ImprimeFactura no falla aunque adentro haya un metodo inexistente.

Estos tests arman la factura en memoria, sin base y sin ARCA, y dejan correr el
FEPDF de verdad. No es la prueba de que el PDF se vea bien, que es otra cosa y
tiene que ver con las plantillas: es la prueba de que el codigo no pide
metodos que no existen.

Si esto se vuelve fragile de mantener, la alternativa no es sacarlo sino
armar una factura real en la base de pruebas: lo que no puede volver es no
probar ImprimeFactura.
"""

import ast
import io
import os
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def qt():
    """FacturaController construye widgets, y sin QApplication el proceso
    muere con STATUS_STACK_BUFFER_OVERRUN sin dejar traceback."""
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


# -- 1. Que los metodos que se le piden al FEPDF existan --------------------

ARCHIVOS_CON_FEPDF = [
    "controladores/Facturas.py",
    "controladores/Remitos.py",
]


def _metodos_que_se_llaman(ruta, atributo):
    with io.open(os.path.join(RAIZ, ruta), encoding="utf-8") as f:
        arbol = ast.parse(f.read())

    llamados = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
            valor = nodo.func.value
            if isinstance(valor, ast.Name) and valor.id == atributo:
                llamados.add(nodo.func.attr)
    return llamados


@pytest.mark.parametrize("ruta", ARCHIVOS_CON_FEPDF)
def test_los_metodos_del_fepdf_existen(ruta):
    """Contra el bug, no contra el metodo concreto: los dos.

    Con un metodo escrito con doble g, el PDF entero deja de generarse y la
    suite no se enteraba. Este test revisa todos los llamados de una vez, asi
    que tambien agarra el siguiente que aparezca.
    """
    from pyafipws.pyfepdf import FEPDF

    metodos = _metodos_que_se_llaman(ruta, "pyfpdf")
    if not metodos:
        pytest.skip("el archivo ya no usa ningun metodo del FEPDF")

    faltan = sorted(m for m in metodos if not hasattr(FEPDF, m))
    assert not faltan, "{} llama a {} y el FEPDF no lo tiene".format(
        ruta, ", ".join(faltan))


@pytest.mark.parametrize("ruta", ARCHIVOS_CON_FEPDF)
def test_el_pie_de_pagina_no_tiene_typos(ruta):
    """El caso concreto, por si vuelve a colarse el doble g."""
    with io.open(os.path.join(RAIZ, ruta), encoding="utf-8") as f:
        texto = f.read()
    assert "AggregarDato" not in texto, \
        "{} tiene AggregarDato: el metodo se llama AgregarDato".format(ruta)


# -- 2. La prueba que faltaba: ImprimeFactura de verdad --------------------

class _Falso(object):
    """Un objeto con lo que el codigo le pide, y nada mas."""

    def __init__(self, **atributos):
        self.__dict__.update(atributos)


def _cabfact():
    """Una factura completa, en memoria.

    Las fechas van como date, no como string: el codigo las pasa por
    FechaMysql(), que les llama strftime.
    """
    import datetime

    cliente = _Falso(
        idcliente=1,
        nombre="ALGUN CLIENTE SA",
        cuit="20345678907",
        dni=11111111,
        tiporesp_id=1,
        tiporesp=_Falso(nombre="RESP. INSCRIPTO",
                         idtiporesp=1,
                         condicion_iva_receptor_id=1),
        localidad=_Falso(nombre="CAPITAL", provincia="CABA"),
        percepcion=_Falso(detalle="IIBB"),
    )
    return _Falso(
        idcabfact=1,
        numero="00010000000123",
        fecha=datetime.date(2026, 10, 1),
        concepto=1,               # productos
        # El concepto 1 hace que el pie pida el periodo facturado, asi que
        # desde y hasta tienen que ser fechas de verdad, no None.
        desde=datetime.date(2026, 10, 1),
        hasta=datetime.date(2026, 10, 1),
        nombre="",
        domicilio="Una calle 123",
        total=Decimal("121.00"),
        neto=Decimal("100.00"),
        iva=Decimal("21.00"),
        percepciondgr=Decimal("0.00"),
        # netoa y netob son los netos por alicuota, y son los que lee el pie
        # para agregar los subtotales de IVA. Los nombres van verificados
        # contra modelos/Cabfact.py, porque inventarse uno con las letras
        # transpuestas rompe el test por una razon que no es la que se quiere.
        netoa=Decimal("100.00"),
        netob=Decimal("0.00"),
        cae="71234567890123",
        venccae=datetime.date(2026, 10, 11),
        formapago=_Falso(detalle="CONTADO"),
        # El nombre importa: arma "facturas/<tipo>-<numero>.pdf" y es lo
        # que GenerarPDF recibe. Sin esto, la primera llamada se cae.
        tipocomp=_Falso(codigo=6, nombre="Factura B"),
        cliente=cliente,
    )


def _detfact():
    articulo = _Falso(idarticulo=1)
    return _Falso(idarticulo=articulo,
                  descad="Mantenimiento",
                  cantidad=Decimal("1"),
                  precio=Decimal("100.00"),
                  montoiva=Decimal("21.00"),
                  tipoiva=_Falso(iva=Decimal("21")))


@pytest.fixture
def limpio():
    """Se lleva lo que la prueba genere en la carpeta de trabajo.

    ImprimeFactura escribe el PDF en el cwd, y pytest ya corre desde la raiz
    del repo. Cambiar de carpeta rompia la resolucion de datos, asi que la
    prueba se queda aca y esta fixture limpia despues.
    """
    # El PDF sale en facturas/, no en la raiz, asi que se mira en las dos.
    carpetas = [RAIZ, os.path.join(RAIZ, "facturas")]
    antes = {c: set(os.listdir(c)) for c in carpetas if os.path.isdir(c)}
    yield RAIZ
    for carpeta, previas in antes.items():
        for nombre in set(os.listdir(carpeta)) - previas:
            ruta = os.path.join(carpeta, nombre)
            if os.path.isfile(ruta):
                try:
                    os.remove(ruta)
                except OSError:
                    pass


@pytest.fixture
def sin_arca(monkeypatch):
    """Sin base, sin ARCA y sin mostrar ventanas.

    Se parchea lo unico que ImprimeFactura toma del exterior: la cabecera, el
    detalle y la muestra del PDF. El FEPDF queda intacto, que es justamente
    lo que se quiere probar.
    """
    import controladores.Facturas as FAC
    import libs.Ventanas as V

    class CabfactFalsa(object):
        def get_by_id(self, idcabecera):
            return _cabfact()

    class DetfactFalsa(object):
        # El codigo arma el filtro con Detfact.idcabfact, asi que la clase
        # necesita el atributo aunque el where de mentira lo ignore.
        idcabfact = None

        def select(self):
            return self

        def where(self, condicion):
            return [_detfact()]

    class CpbteRelFalsa(object):
        idcabfact = None

        def select(self):
            return self

        def where(self, condicion):
            return []

    monkeypatch.setattr(FAC, "Cabfact", CabfactFalsa)
    monkeypatch.setattr(FAC, "Detfact", DetfactFalsa)
    monkeypatch.setattr(FAC, "CpbteRel", CpbteRelFalsa)
    # La plantilla del formato: se usa la de FCE, que es la que hay.
    monkeypatch.setattr(FAC, "ubicacion_sistema", lambda: RAIZ + os.sep)
    monkeypatch.setattr(V, "showError",
                        lambda *a, **k: pytest.fail("showError: {}".format(a)))
    return None


def test_imprimir_una_factura_no_revienta(qt, sin_arca, limpio):
    """El test que faltaba: la factura se imprime de punta a punta.

    Falla si un metodo esta mal escrito, si un dato falta, o si el FEPDF
    protesta. Antes no habia nada que lo cubriera, y por eso un typo de una
    letra en el pie de pagina dejo la app entera sin comprobante sin que la
    suite dijera nada.
    """
    from controladores.Facturas import FacturaController

    # Primero el controlador, que llena combos contra la base de la carpeta de
    # trabajo. Despues se cambia de carpeta, que es donde tiene que caer el PDF.
    controlador = FacturaController()
    carpeta = os.path.join(RAIZ, "facturas")
    antes = set(os.listdir(carpeta)) if os.path.isdir(carpeta) else set()

    controlador.ImprimeFactura(idcabecera=1, mostrar=False)

    generados = (set(os.listdir(carpeta)) - antes) if os.path.isdir(carpeta) \
        else set()
    assert not getattr(controlador, "Excepcion", ""), \
        "ImprimeFactura fallo: {}".format(controlador.Excepcion[-800:])
    assert generados, "no se genero ningun PDF en facturas/:\n{}".format(
        getattr(controlador, "Traceback", "")[-800:])


def test_el_pdf_generado_es_un_pdf(qt, sin_arca, limpio):
    """Y que lo que sale es un PDF de verdad, con su firma y su paginas.

    Esto va mas alla del nombre del metodo: si el archivo se generara vacio o
    corrupto, aqui se veria. Comparar el tamano y el encabezado %PDF- es lo que
    se sostiene entre versiones de fpdf2, porque el hash lleva la fecha de
    creacion y cambia siempre.
    """
    from controladores.Facturas import FacturaController

    controlador = FacturaController()
    carpeta = os.path.join(RAIZ, "facturas")
    antes = set(os.listdir(carpeta)) if os.path.isdir(carpeta) else set()
    controlador.ImprimeFactura(idcabecera=1, mostrar=False)

    assert not getattr(controlador, "Excepcion", ""), \
        "ImprimeFactura fallo: {}".format(controlador.Excepcion)

    nuevos = (set(os.listdir(carpeta)) - antes) if os.path.isdir(carpeta) \
        else set()
    pdfs = [n for n in nuevos if n.lower().endswith(".pdf")]
    assert pdfs, "no se genero ningun PDF (se generaron: {})".format(nuevos)

    with open(os.path.join(carpeta, pdfs[0]), "rb") as f:
        contenido = f.read()
    assert contenido.startswith(b"%PDF-"), "el archivo no es un PDF"
    assert len(contenido) > 1000, "el PDF salio demasiado chico: {} bytes".format(
        len(contenido))
