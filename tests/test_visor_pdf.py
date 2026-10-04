"""El PDF se genera pero no se abria, y no habia forma de saber por que.

El sintoma
----------
El operador le daba Imprimir a una factura de la reimpresion y no se abria
nada. El PDF estaba: `facturas/FACTURA_C-000500000031.pdf`, 64 KB. El boton
no fallaba y no habia ningun aviso.

Por que
-------
`os.startfile` le pasa el archivo al programa que Windows tenga asociado a
`.pdf`. En la maquina de prueba ese programa es Foxit PDF Reader, que corre
como instancia unica: si ya tiene un documento abierto, ignora el segundo
archivo y no dice nada. Verificado mirando las ventanas del proceso antes y
despues de llamar a `os.startfile`, y con las dos variantes (con y sin el
verbo `''`): en las dos la ventana seguia siendo la del PDF anterior.

Este test fija la cadena que reemplaza eso: primero el navegador, que abre una
ventana nueva siempre, y si no se puede, el visor del sistema. Y si tampoco,
que se avise, porque un `None` silencioso deja al operador creyendo que
imprimio.
"""

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import pytest  # noqa: E402

from libs import visor  # noqa: E402


class _Registro(object):
    def __init__(self):
        self.navegador = []
        self.sistema = []


@pytest.fixture
def pdf(monkeypatch, tmp_path):
    ruta = tmp_path / "comprobante.pdf"
    ruta.write_bytes(b"%PDF-1.4\n%%EOF\n")
    return str(ruta)


@pytest.fixture
def spying(monkeypatch):
    reg = _Registro()

    def navegador(url, new=0):
        reg.navegador.append(url)
        return reg.respuesta_navegador

    def startfile(ruta, operacion=''):
        reg.sistema.append((ruta, operacion))
        if reg.falla_sistema:
            raise OSError(2, "no se encontro el archivo")

    reg.respuesta_navegador = True
    reg.falla_sistema = False
    monkeypatch.setattr(visor.webbrowser, "open", navegador)
    monkeypatch.setattr(visor.os, "startfile", startfile)
    return reg


# ------------------------------------------------------------------ la URL


def test_la_url_no_le_queda_una_barra_de_mas():
    """`pathname2url` en Windows ya devuelve `///C:/...`.

    Si se le pone `file:///` adelante quedan seis barras y la URL no la
    entiende cualquiera. Esto se ve en la URL que se manda, no en el archivo.
    """
    url = visor.url_de_archivo(r"C:\Programacion\PyFE\facturas\a.pdf")

    assert url.count("///") == 1, url
    assert url.startswith("file:///C:/"), url
    assert url.endswith("/facturas/a.pdf"), url


def test_la_url_escapa_los_espacios(pdf, tmp_path):
    """Una carpeta con espacio rompe la URL si no va escapada."""
    carpeta = tmp_path / "mis comprobantes"
    carpeta.mkdir()
    ruta = carpeta / "a.pdf"
    ruta.write_bytes(b"%PDF-1.4\n")

    assert "%20" in visor.url_de_archivo(str(ruta))


# ------------------------------------------------------------- la cadena


def test_el_navegador_es_el_primero(pdf, spying):
    """Es lo que resuelve el problema: abre una ventana nueva siempre."""
    assert visor.abrir_pdf(pdf) == 'navegador'

    assert len(spying.navegador) == 1
    assert spying.navegador[0].startswith("file:///")
    assert spying.sistema == [], "no deberia haber llegado al visor del sistema"


def test_sin_navegador_va_al_visor_del_sistema(pdf, spying):
    """Una maquina sin navegador configurado tiene que poder igual."""
    spying.respuesta_navegador = False

    assert visor.abrir_pdf(pdf) == 'sistema'
    assert spying.sistema == [(pdf, '')]


def test_sin_ninguno_devuelve_none(pdf, spying):
    """Y si no se pudo con ninguno, que quede registrado.

    Devolver None es lo que hace que el que llama avise. Un `True` a ciegas
    es lo que dejo al operador creyendo que habia imprimido.
    """
    spying.respuesta_navegador = False
    spying.falla_sistema = True

    assert visor.abrir_pdf(pdf) is None


def test_un_archivo_que_no_existe_no_se_intenta_abrir(monkeypatch):
    reg = _Registro()
    monkeypatch.setattr(visor.webbrowser, "open",
                        lambda url, new=0: reg.navegador.append(url) or True)
    monkeypatch.setattr(visor.os, "startfile",
                        lambda ruta, operacion='': reg.sistema.append(ruta))

    assert visor.abrir_pdf(r"C:\no\esta\factura.pdf") is None
    assert visor.abrir_pdf("") is None
    assert reg.navegador == [] and reg.sistema == []


def test_imprimir_no_va_por_el_navegador(pdf, spying):
    """Imprimir se hace con el visor del sistema, y con el verbo de impresion.

    El navegador no se puede mandar a la impresora de forma confiable, y
    mandarla a la impresora que no es es peor que no mandar.
    """
    assert visor.abrir_pdf(pdf, imprimir=True) == 'sistema'

    assert spying.navegador == []
    assert spying.sistema == [(pdf, 'print')]


# ----------------------------------------------------- quien lo llama


def test_la_factura_avisa_si_no_se_pudo_abrir(monkeypatch, spying):
    """El cartel tiene que decir DONDE quedo el archivo.

    El PDF se genera igual: la factura esta autorizada en ARCA y no se puede
    volver a emitir. Lo que se perdio es la pantalla de muestra, no el
    comprobante, asi que la salida es la ruta.
    """
    import inspect

    import controladores.Facturas as MOD

    fuente = inspect.getsource(MOD.FacturaController._armar_comprobante)

    assert "abrir_pdf" in fuente, "la factura sigue abriendo el PDF por su cuenta"
    assert "MostrarPDF" not in fuente, \
        "quedo el os.startfile de pyfepdf, que es el que no abre"
    assert "no se pudo abrir" in fuente, "no avisa cuando no se pudo abrir"
    assert "os.path.abspath" in fuente, "el aviso no dice donde quedo el archivo"


def test_el_remito_avisa_si_no_se_pudo_abrir():
    import inspect

    import controladores.Remitos as MOD

    fuente = inspect.getsource(MOD)
    assert "MostrarPDF" not in fuente, "el remito sigue abriendo el PDF por su cuenta"
    assert "no se pudo abrir" in fuente


def test_la_muestra_del_diseno_va_por_el_navegador():
    import inspect

    import controladores.DisenoComprobante as MOD

    fuente = inspect.getsource(MOD)
    assert "os.startfile" not in fuente, \
        "la muestra del diseno sigue yendo al visor del sistema"
    assert "abrir_pdf" in fuente
