# coding=utf-8
"""Tests del controlador PyQt5 del actualizador.

Van con `QT_QPA_PLATFORM=offscreen` y una sqlite en memoria: no tocan la base
ni muestran nada en pantalla.

El foco no es el pixel del dialogo, es el camino que puede dejar al usuario
colgado o sin actualizaciones:

- la descarga fallida tiene que LLEGAR a la UI como error, no quedar
  esperando en un hilo que nadie escucha;
- en desarrollo no se puede ni intentar la red;
- un instalador que no existe no se ejecuta;
- las novedades no se pueden marcar como vistas si el dialogo no se mostro.
"""

import hashlib
import json
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from libs.actualizaciones import (DownloadCancelled,  # noqa: E402
                                  UpdateService, parse_manifest_bytes)
from libs.build_info import APP_ID  # noqa: E402

V12 = "2026.10.05.12.00.00"
V13 = "2026.10.05.13.00.00"

SHA = "a" * 64


@pytest.fixture(scope="module")
def aplicacion():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


def _manifiesto(sha=SHA, app_id="asiento"):
    return parse_manifest_bytes(json.dumps({
        "schema_version": 1,
        "app_id": app_id,
        "version": V13,
        "published_at": "2026-10-05T12:00:00Z",
        "mandatory": False,
        "download_url": "https://github.com/oscarvogel/vogel-releases/releases/download/latest/Asiento_Produccion_Setup.exe",
        "sha256": sha,
        "notes": "Manejo de stock.",
    }).encode("utf-8"), app_id)


def test_el_controlador_no_hace_nada_en_desarrollo():
    """La guarda mas importante del modulo.

    El archivo versionado de build_info tiene app_id 'development'. Sin esta
    guarda, abrir la app desde el repo bajaria el instalador de produccion
    encima de una base de pruebas.
    """
    from controladores.Actualizador import ActualizadorController

    assert APP_ID == "development"
    controlador = ActualizadorController()
    assert controlador.habilitado() is False
    # Y el chequeo del arranque ni siquiera arranca un hilo.
    assert controlador.chequear_al_arranque() is None


def test_construir_el_controlador_no_dispara_la_red():
    """El cuelgue que aparecio en el primer release.

    El chequeo estaba en `Main.__init__`. Con el build en estado de
    produccion, cualquier test que armara el controlador (los hay:
    test_componentes.py construye el Main real para leer sus DESTINOS)
    lanzaba una descarga de verdad y se quedaba esperando el hilo.

    El chequeo de version es del arranque de la app, no de construir sus
    piezas: por eso lo llama `main.py` y no el constructor.
    """
    import inspect

    import controladores.Main as main_controlador

    fuente = inspect.getsource(main_controlador.Main.__init__)
    assert "chequearActualizaciones" not in fuente, (
        "el chequeo de actualizaciones no puede estar en Main.__init__: "
        "armar el controlador dispararia la red")

    # Y el metodo existe igual, para que main.py lo pueda llamar.
    assert callable(getattr(main_controlador.Main, "chequearActualizaciones"))


def test_el_enganche_del_arranque_no_hace_nada_en_desarrollo():
    """`main.py::_chequear_actualizaciones` en desarrollo es un no-op.

    Es el camino que corre en cada arranque: tiene que devolver sin dejar
    un controlador colgado ni intentar una request.
    """
    import main as arranque

    assert APP_ID == "development"
    arranque._ACTUALIZADOR = None
    arranque._chequear_actualizaciones(None)
    assert arranque._ACTUALIZADOR is None, (
        "en desarrollo no deberia quedar ningun actualizador creado")


def test_el_worker_de_descarga_avisa_el_error_en_vez_de_colgarse(tmp_path, monkeypatch):
    """Un SHA que no coincide tiene que llegar a la UI.

    Si el worker se limitara a loguear, el dialogo de progreso quedaria
    esperando para siempre y el usuario creeria que se esta descargando.
    """
    from controladores.Actualizador import _DescargaWorker

    monkeypatch.setattr("libs.actualizaciones.tempfile.gettempdir",
                        lambda: str(tmp_path))
    instalador = b"MZ" + b"\x01" * 2048
    service = UpdateService(
        app_id="asiento", installed_version="2026.09.30.10.00.00",
        opener=lambda p, timeout=None: FakeRespuesta(instalador))
    # El manifiesto declara un hash que no es el del archivo.
    manifest = _manifiesto(sha=hashlib.sha256(b"otra cosa").hexdigest())

    worker = _DescargaWorker(service, manifest)
    received = []
    worker.terminado.connect(lambda ruta: received.append(("terminado", ruta)))
    worker.fallido.connect(lambda err: received.append(("fallido", err)))

    worker.run()

    assert received, "el worker no emitio nada: el dialogo quedaria colgado"
    assert received[0][0] == "fallido"
    assert "SHA256" in received[0][1]
    # Y no se ejecuta nada.
    assert received[0][0] != "terminado"


def test_el_worker_entrega_la_ruta_cuando_todo_anda(tmp_path, monkeypatch):
    from controladores.Actualizador import _DescargaWorker

    monkeypatch.setattr("libs.actualizaciones.tempfile.gettempdir",
                        lambda: str(tmp_path))
    instalador = b"MZ" + b"\x02" * 2048
    service = UpdateService(
        app_id="asiento", installed_version="2026.09.30.10.00.00",
        opener=lambda p, timeout=None: FakeRespuesta(instalador))
    manifest = _manifiesto(sha=hashlib.sha256(instalador).hexdigest())

    worker = _DescargaWorker(service, manifest)
    received = []
    progreso = []
    worker.terminado.connect(lambda ruta: received.append(("terminado", ruta)))
    worker.fallido.connect(lambda err: received.append(("fallido", err)))
    worker.progreso.connect(lambda b, t: progreso.append((b, t)))

    worker.run()

    assert received and received[0][0] == "terminado"
    assert os.path.isfile(received[0][1])
    # La barra de progreso recibio datos reales, no un unico 0.
    assert progreso and progreso[-1][0] == len(instalador)


def test_cancelar_llega_al_worker(tmp_path, monkeypatch):
    from controladores.Actualizador import _DescargaWorker

    monkeypatch.setattr("libs.actualizaciones.tempfile.gettempdir",
                        lambda: str(tmp_path))
    instalador = b"MZ" + b"\x03" * 400000
    service = UpdateService(
        app_id="asiento", installed_version="2026.09.30.10.00.00",
        opener=lambda p, timeout=None: FakeRespuesta(instalador))
    manifest = _manifiesto(sha=hashlib.sha256(instalador).hexdigest())

    worker = _DescargaWorker(service, manifest)
    recibidos = []
    worker.cancelado.connect(lambda: recibidos.append("cancelado"))
    worker.fallido.connect(lambda err: recibidos.append(("fallido", err)))
    worker.cancelar()
    worker.run()

    assert recibidos == ["cancelado"]


def test_no_se_ejecuta_un_instalador_inexistente(tmp_path):
    """Ruta que no existe: se avisa y no se lanza nada.

    Es el camino que se recorre si el antivirus borra el instalador entre la
    descarga y el momento de ejecutarlo.
    """
    from controladores.Actualizador import ActualizadorController

    assert ActualizadorController.lanzar_instalador(
        str(tmp_path / "no-existe.exe")) is False


def test_las_novedades_se_marcan_solo_si_se_mostraron(tmp_path, monkeypatch):
    """La marca de 'ya lo vi' va despues del dialogo, nunca antes.

    Con un `finally` alrededor del exec_, cualquier excepcion marcaria las
    novedades como vistas y el usuario no las veria nunca mas.
    """
    from controladores import Actualizador as modulo

    mostrados = []
    marcados = []

    class DialogoFalso(object):
        def __init__(self, pendientes, parent=None):
            mostrados.append(pendientes)

        def exec_(self):
            if modo["fallar"]:
                raise RuntimeError("no se pudo mostrar")

    class ChangelogFalso(object):
        installed_version = modulo.BUILD_VERSION

        def mark_seen(self, version=None):
            marcados.append(version or self.installed_version)

    class ServiceFalso(object):
        app_id = "asiento"
        channel = "latest"

        def check(self):
            return None

    modo = {"fallar": False}
    monkeypatch.setattr(modulo, "DialogoNovedades", DialogoFalso)
    monkeypatch.setattr(modulo, "es_build_productivo", lambda: True)

    pendientes = [{"version": V13, "notes": ["Novedad"]}]
    controlador = modulo.ActualizadorController(
        service=ServiceFalso(), changelog=ChangelogFalso())

    controlador._procesar(None, pendientes, None)
    assert mostrados and marcados == [modulo.BUILD_VERSION]

    mostrados.clear()
    marcados.clear()
    modo["fallar"] = True
    # La excepcion sube: el llamador (el callback del hilo) la loguea y
    # sigue, y la app abre igual. Lo que no puede pasar es que el changelog
    # quede marcado como visto.
    with pytest.raises(RuntimeError):
        controlador._procesar(None, pendientes, None)
    assert mostrados, "no se intento mostrar el dialogo"
    assert marcados == []


def test_el_dialogo_de_novedades_muestra_todas_las_pendientes(aplicacion):
    """El texto que ve el usuario, con todo lo que se salteo."""
    from controladores.Actualizador import DialogoNovedades

    pendientes = [
        {"version": V13, "notes": ["Inventario inicial", "Avisos de faltante"]},
        {"version": V12, "notes": ["Pantalla de emision rediseñada"]},
    ]
    dialogo = DialogoNovedades(pendientes)
    try:
        from PyQt5.QtWidgets import QTextBrowser
        navegador = dialogo.findChild(QTextBrowser)
        assert navegador is not None
        html = navegador.toHtml()
        for version in (V13, V12):
            assert version in html
        for nota in ("Inventario inicial", "Avisos de faltante",
                     "Pantalla de emision rediseñada"):
            assert nota in html
    finally:
        dialogo.deleteLater()


class FakeRespuesta(object):
    def __init__(self, payload):
        self._datos = payload
        self._pos = 0
        self.headers = {"Content-Length": str(len(payload))}

    def read(self, cantidad=-1):
        if cantidad is None or cantidad < 0:
            trozo = self._datos[self._pos:]
            self._pos = len(self._datos)
            return trozo
        trozo = self._datos[self._pos:self._pos + cantidad]
        self._pos += len(trozo)
        return trozo

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False
