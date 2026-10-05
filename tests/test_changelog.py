# coding=utf-8
"""Tests del historial de novedades.

La regla que se prueba aca es la del doc de releases: si el usuario salta
varias versiones, al primer inicio de la nueva tiene que ver **todas** las
novedades que se salteo, no solo la ultima. Mostrar solo la ultima es
exactamente mostrarle lo que ya se salte.

La segunda regla es la frontera de configuracion: la marca de "ya lo vi" vive
en %LOCALAPPDATA%\\<app_id> y **nunca** en sistema.ini. Un test lo verifica,
porque el ini lo escribe la app, lo copia el asistente de primer arranque y
guarda los datos de facturacion: escribir ahi desde un chequeo de red seria
tocar la configuracion del usuario.
"""

import json
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from libs.changelog import ChangelogService  # noqa: E402

V10 = "2026.10.05.10.00.00"
V11 = "2026.10.05.11.00.00"
V12 = "2026.10.05.12.00.00"
V13 = "2026.10.05.13.00.00"


class FakeResponse(object):
    def __init__(self, payload):
        self._datos = payload

    def read(self, cantidad=-1):
        return self._datos

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _historial(versiones, app_id="asiento"):
    return json.dumps({
        "schema_version": 1,
        "app_id": app_id,
        "versions": [
            {"version": v, "published_at": "2026-10-05T12:00:00Z",
             "notes": ["Novedad de la {}".format(v)]}
            for v in versiones
        ],
    }).encode("utf-8")


def _servicio(versiones, instalada=V13, app_id="asiento", state_root=None):
    return ChangelogService(app_id=app_id, installed_version=instalada,
                            opener=lambda p, timeout=None: FakeResponse(
                                _historial(versiones, app_id)),
                            state_root=state_root)


def test_muestra_todas_las_novedades_salteadas(tmp_path):
    """El caso del doc: vio las 10:00, y ahora esta en las 13:00."""
    servicio = _servicio([V10, V11, V12, V13], state_root=str(tmp_path))
    servicio.mark_seen(V10)

    pendientes = servicio.pending(servicio.fetch())
    assert [e["version"] for e in pendientes] == [V13, V12, V11]
    # De mas nueva a mas vieja: es el orden en que se leen.
    assert pendientes[0]["notes"] == ["Novedad de la {}".format(V13)]


def test_no_vuelve_a_mostrar_lo_ya_visto(tmp_path):
    servicio = _servicio([V10, V11, V12, V13], state_root=str(tmp_path))
    servicio.mark_seen(V13)
    assert servicio.pending(servicio.fetch()) == []


def test_sin_estado_previo_muestra_todo_hasta_la_version_instalada(tmp_path):
    """Installacion nueva: se ve el historial completo hasta donde esta.

    Si se limitara a 'lo posterior a la ultima vista', una instalacion
    limpia no veria nunca las novedades de la version que esta corriendo.
    """
    servicio = _servicio([V10, V11, V12, V13], state_root=str(tmp_path))
    pendientes = servicio.pending(servicio.fetch())
    assert [e["version"] for e in pendientes] == [V13, V12, V11, V10]


def test_no_muestra_lo_publicado_para_una_version_que_no_esta_instalada(tmp_path):
    """Una entrada de una version futura no se anticipa."""
    servicio = _servicio([V10, V11, V12, V13, "2026.10.06.09.00.00"],
                         instalada=V12, state_root=str(tmp_path))
    pendientes = servicio.pending(servicio.fetch())
    assert [e["version"] for e in pendientes] == [V12, V11, V10]


def test_el_estado_no_se_escribe_en_la_carpeta_del_programa(tmp_path):
    """La frontera de configuracion, verificada.

    La carpeta del programa la borra y reemplaza el instalador en cada
    actualizacion: un estado guardado ahi se perderia con cada version y el
    usuario veria las mismas novedades indefinidamente.
    """
    os.environ["LOCALAPPDATA"] = str(tmp_path / "localappdata")
    try:
        servicio = ChangelogService(app_id="asiento", installed_version=V13)
        ruta = servicio.state_path
        assert os.path.abspath(ruta).startswith(
            os.path.abspath(str(tmp_path / "localappdata")))
        assert "sistema.ini" not in ruta
        assert not os.path.abspath(ruta).startswith(os.path.abspath(RAIZ))
    finally:
        os.environ.pop("LOCALAPPDATA", None)


def test_mark_seen_sobrevive_un_archivo_de_otro_producto(tmp_path):
    """Un estado de femag en la misma carpeta no se trusts para asiento."""
    carpeta = tmp_path / "asiento"
    carpeta.mkdir()
    (carpeta / "update-state.json").write_text(json.dumps({
        "schema_version": 1,
        "app_id": "femag",
        "last_changelog_version_seen": V13,
    }), encoding="utf-8")

    servicio = ChangelogService(app_id="asiento", installed_version=V13,
                                state_root=str(tmp_path))
    assert servicio.last_seen_version() is None


def test_fetch_sin_red_devuelve_lista_vacia_y_no_rompe(tmp_path):
    """Sin conexion no hay novedades y no hay excepcion.

    El changelog es opcional: una falla aca no puede impedir abrir la app.
    """
    def _fallar(peticion, timeout=None):
        raise OSError("sin internet")

    servicio = ChangelogService(app_id="asiento", installed_version=V13,
                                opener=_fallar, state_root=str(tmp_path))
    assert servicio.fetch() == []
    assert servicio.pending([]) == []


def test_changelog_de_otro_producto_se_ignora(tmp_path):
    """Un changelog de femag en la URL de asiento no muestra nada."""
    servicio = ChangelogService(
        app_id="asiento", installed_version=V13,
        opener=lambda p, timeout=None: FakeResponse(_historial([V10, V11], "femag")),
        state_root=str(tmp_path))
    assert servicio.fetch() == []


def test_entradas_corruptas_no_impiden_ver_las_buenas(tmp_path):
    """Una version con formato raro se descarta sola; el resto se muestra.

    Se descarta en vez de propagar: una entrada vieja rota no puede
    impedir que el usuario vea las novedades de la version que instalo.
    """
    crudo = json.dumps({
        "schema_version": 1,
        "app_id": "asiento",
        "versions": [
            {"version": "0.9.0", "notes": ["vieja, formato roto"]},
            {"version": V13, "notes": []},
            {"version": V12, "notes": ["esta si"]},
            {"version": V12, "notes": ["duplicada"]},
        ],
    }).encode("utf-8")

    servicio = ChangelogService(
        app_id="asiento", installed_version=V13,
        opener=lambda p, timeout=None: FakeResponse(crudo),
        state_root=str(tmp_path))
    pendientes = servicio.pending(servicio.fetch())
    assert [e["version"] for e in pendientes] == [V12]
    assert pendientes[0]["notes"] == ["esta si"]


def test_mark_seen_escribe_utf8_sin_bom(tmp_path):
    """El archivo de estado se lee igual en la proxima version de Python.

    Un JSON con BOM rompe `json.load` en algunos casos y `utf-8-sig` lo
    disimula; el archivo se escribe sin BOM a proposito.
    """
    servicio = _servicio([V13], state_root=str(tmp_path))
    servicio.mark_seen(V13)
    crudo = open(servicio.state_path, "rb").read()
    assert not crudo.startswith(b"\xef\xbb\xbf")
    assert json.loads(crudo.decode("utf-8"))["last_changelog_version_seen"] == V13
