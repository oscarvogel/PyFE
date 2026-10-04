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
archivo y no dice nada. Cerrar la ventana de Foxit no lo arregla, porque el
proceso sigue vivo en la bandeja del sistema. Verificado mirando las ventanas
del proceso antes y despues de llamar a `os.startfile`, con las dos variantes
(con y sin el verbo `''`): en las dos la ventana seguia siendo la del PDF
anterior.

Y un的错误 propio en el primer intento: usar `webbrowser.open` con una URL
`file://` para "usar el navegador". En Windows, `webbrowser.WindowsDefault.open`
es un `os.startfile(url)` envuelto en un try, asi que abria Foxit igual. Se ve
en el codigo de la libreria estandar, no hace falta adivinarlo. Este test es
el que evita volver a esa.
"""

import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import pytest  # noqa: E402

from libs import visor  # noqa: E402


class _Registro(object):
    def __init__(self):
        self.lanzados = []
        self.sistema = []
        self.respuesta_navegador = "chrome.exe"
        self.falla_navegador = False
        self.falla_sistema = False


@pytest.fixture
def pdf(tmp_path):
    ruta = tmp_path / "comprobante.pdf"
    ruta.write_bytes(b"%PDF-1.4\n%%EOF\n")
    return str(ruta)


@pytest.fixture
def spying(monkeypatch):
    reg = _Registro()

    def popen(lista, *args, **kwargs):
        reg.lanzados.append(lista)
        if reg.falla_navegador:
            raise OSError("no se pudo lanzar")
        return _Proceso()

    def startfile(ruta, operacion=''):
        reg.sistema.append((ruta, operacion))
        if reg.falla_sistema:
            raise OSError(2, "no se encontro el archivo")

    monkeypatch.setattr(visor.subprocess, "Popen", popen)
    monkeypatch.setattr(visor.os, "startfile", startfile)
    return reg


class _Proceso(object):
    pid = 1234


# ------------------------------------------------------- donde esta el navegador


def test_se_busca_en_las_tres_carpetas_de_instalacion(monkeypatch, tmp_path):
    """Chrome puede caer en cualquiera de las tres, segun como se instalo.

    Si se busca solo en `Program Files` se pierde la mitad de las maquinas.
    """
    chrome = tmp_path / "Google" / "Chrome" / "Application" / "chrome.exe"
    chrome.parent.mkdir(parents=True)
    chrome.write_text("")

    monkeypatch.setattr(visor.os.path, "isfile",
                        lambda ruta: str(ruta) == str(chrome))
    monkeypatch.setattr(visor.os, "environ", {"ProgramFiles": str(tmp_path)})

    assert visor.ruta_de_navegador() == str(chrome)


def test_tambien_busca_en_appdata_local(monkeypatch, tmp_path):
    """La instalacion por usuario deja el navegador en AppData, no en
    Program Files. Es el caso de las maquinas sin permisos de administrador.
    """
    chrome = tmp_path / "Google" / "Chrome" / "Application" / "chrome.exe"
    chrome.parent.mkdir(parents=True)
    chrome.write_text("")

    monkeypatch.setattr(visor.os.path, "isfile",
                        lambda ruta: str(ruta) == str(chrome))
    monkeypatch.setattr(visor.os, "environ", {"LOCALAPPDATA": str(tmp_path)})

    assert visor.ruta_de_navegador() == str(chrome)


def test_el_orden_es_por_preferencia(monkeypatch, tmp_path):
    """Con Chrome y Edge instalados, gana Chrome.

    El orden esta en NAVEGADORES a proposito: Edge es el que viene con
    Windows y su visor de PDF embebido no siempre abre una ventana nueva.
    """
    assert [nombre for nombre, _ in visor.NAVEGADORES] == [
        "chrome", "edge", "firefox"]


def test_sin_navegador_devuelve_none(monkeypatch):
    monkeypatch.setattr(visor.os.path, "isfile", lambda ruta: False)
    monkeypatch.setattr(visor.os, "environ", {})

    assert visor.ruta_de_navegador() is None


# ------------------------------------------------------------- la cadena


def test_el_navegador_es_el_primero(pdf, spying, monkeypatch):
    """Es lo que resuelve el problema: abre una ventana nueva siempre."""
    monkeypatch.setattr(visor, "ruta_de_navegador",
                        lambda: r"C:\Chrome\chrome.exe")

    assert visor.abrir_pdf(pdf) == 'navegador'

    assert spying.lanzados == [[r"C:\Chrome\chrome.exe",
                                os.path.abspath(pdf)]]
    assert spying.sistema == [], "no deberia haber llegado al visor del sistema"


def test_se_pasa_la_ruta_absoluta(pdf, spying, monkeypatch):
    """Con una ruta relativa el navegador puede abrir cualquier otra cosa."""
    monkeypatch.setattr(visor, "ruta_de_navegador", lambda: "chrome.exe")

    visor.abrir_pdf(pdf)

    assert os.path.isabs(spying.lanzados[0][1])


def test_sin_navegador_va_al_visor_del_sistema(pdf, spying, monkeypatch):
    """Una maquina sin navegador tiene que poder igual."""
    monkeypatch.setattr(visor, "ruta_de_navegador", lambda: None)

    assert visor.abrir_pdf(pdf) == 'sistema'
    assert spying.sistema == [(os.path.abspath(pdf), '')]
    assert spying.lanzados == []


def test_navegador_que_no_parte_cae_al_sistema(pdf, spying, monkeypatch):
    """Un navegador que no se puede lanzar no puede ser el unico camino."""
    monkeypatch.setattr(visor, "ruta_de_navegador", lambda: "chrome.exe")
    spying.falla_navegador = True

    assert visor.abrir_pdf(pdf) == 'sistema'
    assert spying.sistema


def test_sin_ninguno_devuelve_none(pdf, spying, monkeypatch):
    """Y si no se pudo con ninguno, que quede registrado.

    Devolver None es lo que hace que el que llama avise. Un `True` a ciegas
    es lo que dejo al operador creyendo que habia imprimido.
    """
    monkeypatch.setattr(visor, "ruta_de_navegador", lambda: None)
    spying.falla_sistema = True

    assert visor.abrir_pdf(pdf) is None


def test_un_archivo_que_no_existe_no_se_intenta_abrir(spying, monkeypatch):
    monkeypatch.setattr(visor, "ruta_de_navegador", lambda: "chrome.exe")

    assert visor.abrir_pdf(r"C:\no\esta\factura.pdf") is None
    assert visor.abrir_pdf("") is None
    assert spying.lanzados == [] and spying.sistema == []


def test_imprimir_no_va_por_el_navegador(pdf, spying, monkeypatch):
    """Imprimir se hace con el visor del sistema, y con el verbo de impresion.

    El navegador no se puede mandar a la impresora de forma confiable, y
    mandarla a la impresora que no es es peor que no mandar.
    """
    monkeypatch.setattr(visor, "ruta_de_navegador", lambda: "chrome.exe")

    assert visor.abrir_pdf(pdf, imprimir=True) == 'sistema'

    assert spying.lanzados == []
    assert spying.sistema == [(os.path.abspath(pdf), 'print')]


def test_webbrowser_no_se_usa():
    """`webbrowser.open` en Windows es un `os.startfile` de la URL.

    Es la trampa en la que se cae esta funcion la primera vez: devuelve True
    y abre el visor de PDF, que es justo lo que se queria esquivar. Si
    alguien lo vuelve a usar, este test lo dice.

    Se mira el atributo del modulo y no el texto del archivo: el docstring
    menciona `webbrowser.open` justamente para explicar la trampa, y buscar
    la palabra ahi daria un fallo falso.
    """
    assert not hasattr(visor, "webbrowser"), \
        "el modulo importa webbrowser: en Windows abre el visor de PDF"
    assert visor.subprocess is subprocess


# ----------------------------------------------------- quien lo llama


def test_la_factura_avisa_si_no_se_pudo_abrir():
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


def test_subprocess_se_importa():
    """Guarda contra un borrado accidental del import."""
    assert visor.subprocess is subprocess
