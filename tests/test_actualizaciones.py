# coding=utf-8
"""Tests del cliente de actualizacion y del historial de novedades.

Que se prueba y que no
----------------------
Se prueba el mecanismo REAL: se le da un manifiesto o unos bytes de
instalador y se mira que pasa. No se mira que "el shim este puesto".

Eso no es arbitrario. El mecanismo de actualizacion de femag paso months
funcionando con tests en verde que solo comprobaban que el modulo estaba
importado, y el dia que se publico el primer release fallo entero. Un test
que no llega a `check()` ni a `download()` no dice nada de si el usuario va a
recibir su actualizacion.

Los tres caminos que tienen que estar cubiertos y se cubren aca:

1. La red falla -> el error se propaga (para que el llamador no lo confunda
   con "estoy al dia") y el `.part` no queda tirado en TEMP.
2. El SHA256 no coincide -> no se ejecuta nada y no queda archivo.
3. El manifiesto es de otro producto -> se rechaza (si no, Asiento ofrece
   el instalador de FEMAG).
"""

import hashlib
import json
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from libs.actualizaciones import (DownloadCancelled, UpdateService,  # noqa: E402
                                  format_bytes, is_newer_version,
                                  parse_manifest_bytes, parse_version)
from libs.build_info import (APP_ID, BUILD_VERSION,  # noqa: E402
                             es_build_productivo, manifest_url_for)

SHA = "a" * 64
VERSION_NUEVA = "2026.10.05.08.37.00"


# --------------------------------------------------------------------- apoyo


class FakeResponse(object):
    """Lo que devuelve urlopen: contexto, read() y headers."""

    def __init__(self, payload, headers=None):
        self._datos = payload
        self._pos = 0
        self.headers = headers if headers is not None else {
            "Content-Length": str(len(payload))}

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


def manifiesto_bytes(**cambios):
    datos = {
        "schema_version": 1,
        "app_id": "asiento",
        "version": VERSION_NUEVA,
        "published_at": "2026-10-05T11:42:25Z",
        "mandatory": False,
        "download_url": ("https://github.com/oscarvogel/vogel-releases/"
                         "releases/download/latest/Asiento_Produccion_Setup.exe"),
        "sha256": SHA,
        "notes": "Manejo de stock.",
    }
    datos.update(cambios)
    return json.dumps(datos).encode("utf-8")


def opener_que_responde(*respuestas):
    """Devuelve un opener que responde con lo que se le pasa, en orden."""
    restantes = list(respuestas)

    def _abrir(peticion, timeout=None):
        if not restantes:
            raise AssertionError("se pidio una request de mas: {}".format(peticion.full_url))
        return restantes.pop(0)

    return _abrir


# ----------------------------------------------------------------- versiones


def test_parse_version_rechaza_formatos_sueltos():
    """El error clasico de estos sistemas.

    Sin el anclaje al formato completo, '2026.10.5' y '2026.10.05' se
    comparan distinto segun la funcion, y el resultado es un cliente que
    avisa para siempre o que se queda sin actualizaciones.
    """
    with pytest.raises(ValueError):
        parse_version("2026.10.5")
    with pytest.raises(ValueError):
        parse_version("0.9.0")
    with pytest.raises(ValueError):
        parse_version("2026.10.05.08.37.00.EXTRA")
    with pytest.raises(ValueError):
        parse_version("")


def test_parse_version_descompone_en_seis_enteros():
    assert parse_version("2026.10.05.08.37.00") == (2026, 10, 5, 8, 37, 0)


def test_is_newer_version_compara_como_numero_y_no_como_texto():
    # '2026.10.5' > '2026.10.05.08.37.00' como texto, y no como version.
    assert is_newer_version("2026.09.30.10.00.00", "2026.10.05.08.37.00")
    assert not is_newer_version("2026.10.05.08.37.00", "2026.10.05.08.37.00")
    assert not is_newer_version("2026.10.05.08.37.00", "2026.09.30.10.00.00")


# ------------------------------------------------------------------ manifiesto


def test_manifiesto_valido_se_parsea():
    manifest = parse_manifest_bytes(manifiesto_bytes(), "asiento")
    assert manifest.app_id == "asiento"
    assert manifest.version == VERSION_NUEVA
    assert manifest.sha256 == SHA


def test_manifiesto_de_otro_producto_se_rechaza():
    """Aislamiento entre apps.

    Sin esto, un manifiesto de FEMAG o FGPY copiado al de Asiento haria que
    Asiento ofrezca el instalador equivocado. Es el fallo mas caro que puede
    tener este mecanismo: el usuario instala otra app creyendo que actualiza
    esta.
    """
    with pytest.raises(ValueError) as error:
        parse_manifest_bytes(manifiesto_bytes(app_id="femag"), "asiento")
    assert "otro producto" in str(error.value)


def test_manifiesto_rechaza_lo_que_falta_o_esta_mal():
    # schema_version desconocido: el formato podria cambiar.
    with pytest.raises(ValueError):
        parse_manifest_bytes(manifiesto_bytes(schema_version=2), "asiento")
    # SHA256 que no es un hash.
    with pytest.raises(ValueError):
        parse_manifest_bytes(manifiesto_bytes(sha256="no-es-un-hash"), "asiento")
    # download_url sin HTTPS: el hash no protege de un manifiesto que te
    # manda el instalador por http.
    with pytest.raises(ValueError):
        parse_manifest_bytes(
            manifiesto_bytes(download_url="http://ejemplo/setup.exe"), "asiento")
    # Version que no es timestamp.
    with pytest.raises(ValueError):
        parse_manifest_bytes(manifiesto_bytes(version="0.9.0"), "asiento")
    # BOM: el schema dice UTF-8 sin BOM y femag lo rechaza explicitamente.
    with pytest.raises(ValueError):
        parse_manifest_bytes(b"\xef\xbb\xbf" + manifiesto_bytes(), "asiento")


# ------------------------------------------------------------------- chequeo


def test_check_detecta_version_nueva():
    servicio = UpdateService(app_id="asiento",
                             installed_version="2026.09.30.10.00.00",
                             opener=opener_que_responde(FakeResponse(manifiesto_bytes())))
    resultado = servicio.check()
    assert resultado.update_available is True
    assert resultado.manifest.version == VERSION_NUEVA


def test_check_no_avisa_cuando_ya_se_esta_al_dia():
    servicio = UpdateService(app_id="asiento",
                             installed_version=VERSION_NUEVA,
                             opener=opener_que_responde(FakeResponse(manifiesto_bytes())))
    assert servicio.check().update_available is False


def test_check_propaga_el_error_de_red():
    """Un fallo de red NO es lo mismo que 'no hay actualizacion'.

    Si check() devolviera 'no hay' ante un error, el usuario se quedaria sin
    actualizaciones sin enterarse de por que. Por eso propaga: el llamador
    loguea y abre igual.
    """
    def _fallar(peticion, timeout=None):
        raise OSError("no hay internet")

    servicio = UpdateService(app_id="asiento",
                             installed_version="2026.09.30.10.00.00",
                             opener=_fallar)
    with pytest.raises(OSError):
        servicio.check()


def test_el_chequeo_se_habilita_solo_en_build_productivo():
    """El archivo versionado tiene app_id de desarrollo.

    Sin esta guarda, correr la app desde el repo avisaria de las versiones
    de produccion y abriria el instalador encima de una base de pruebas.
    """
    assert APP_ID == "development"
    assert es_build_productivo() is False
    servicio = UpdateService()
    assert servicio.habilitado is False
    # Y el chequeo no toca la red: no hay opener, y sin estar habilitado
    # tiene que volver sin error.
    assert servicio.check().update_available is False


def test_manifest_url_solo_para_app_id_registrados():
    assert "apps/asiento/latest.json" in manifest_url_for("asiento")
    with pytest.raises(ValueError):
        manifest_url_for("inventada")


# ------------------------------------------------------------------ descarga


def _servicio_para_descarga(payload, app_id="asiento"):
    return UpdateService(app_id=app_id,
                         installed_version="2026.09.30.10.00.00",
                         opener=opener_que_responde(FakeResponse(payload)))


def _archivos_debajo(raiz):
    """Los archivos que quedaron, en cualquier subcarpeta.

    Se recorre porque el servicio crea `Asiento/updates/` dentro de TEMP: la
    carpeta vacia esta bien, lo que no puede quedar es un archivo.
    """
    encontrados = []
    for carpeta, _dirs, archivos in os.walk(str(raiz)):
        for nombre in archivos:
            encontrados.append(os.path.join(carpeta, nombre))
    return encontrados


def test_download_verifica_el_sha_y_deja_el_instalador(tmp_path, monkeypatch):
    """El camino feliz completo: descarga, verifica y renombra."""
    instalador = b"MZ" + b"\x00" * 5000
    sha_real = hashlib.sha256(instalador).hexdigest()
    monkeypatch.setattr("libs.actualizaciones.tempfile.gettempdir",
                        lambda: str(tmp_path))

    servicio = _servicio_para_descarga(instalador)
    progreso = []
    ruta = servicio.download(parse_manifest_bytes(
        manifiesto_bytes(sha256=sha_real), "asiento"),
        progress_callback=lambda b, t: progreso.append((b, t)))

    assert os.path.isfile(ruta)
    with open(ruta, "rb") as fh:
        assert fh.read() == instalador
    # El .part no puede quedar: en TEMP seria un .exe a medio escribir que
    # alguien podria ejecutar despues.
    assert not os.path.exists(ruta + ".part")
    # Y la barra recibio progreso de verdad.
    assert progreso and progreso[-1][0] == len(instalador)


def test_download_rechaza_sha_que_no_coincide_y_no_deja_archivo(tmp_path, monkeypatch):
    """El caso que de verdad importa: un instalador manipulado en tránsito."""
    instalador = b"MZ" + b"\x00" * 100
    monkeypatch.setattr("libs.actualizaciones.tempfile.gettempdir",
                        lambda: str(tmp_path))
    sha_mentiroso = hashlib.sha256(b"otro contenido cualquiera").hexdigest()
    manifest = parse_manifest_bytes(manifiesto_bytes(sha256=sha_mentiroso), "asiento")

    servicio = _servicio_para_descarga(instalador)
    with pytest.raises(ValueError) as error:
        servicio.download(manifest)
    assert "SHA256" in str(error.value)

    # Ni el final ni el parcial.
    assert _archivos_debajo(tmp_path) == []


def test_download_cancelado_no_deja_el_parcial(tmp_path, monkeypatch):
    instalador = b"MZ" + b"\x00" * 200000
    monkeypatch.setattr("libs.actualizaciones.tempfile.gettempdir",
                        lambda: str(tmp_path))
    manifest = parse_manifest_bytes(
        manifiesto_bytes(sha256=hashlib.sha256(instalador).hexdigest()), "asiento")

    servicio = _servicio_para_descarga(instalador)
    with pytest.raises(DownloadCancelled):
        servicio.download(manifest, cancel_callback=lambda: True)
    assert _archivos_debajo(tmp_path) == []


def test_download_no_acepta_el_instalador_de_otra_app(tmp_path, monkeypatch):
    """Aun con el SHA bien, no se descarga lo de otro producto.

    El manifiesto se parsea como femag a proposito, para simular el caso real
    (un manifiesto de otro producto publicado en la URL de Asiento) en vez de
    un caso que el parser ya habria descartado.
    """
    monkeypatch.setattr("libs.actualizaciones.tempfile.gettempdir",
                        lambda: str(tmp_path))
    manifest_femag = parse_manifest_bytes(
        manifiesto_bytes(app_id="femag"), "femag")

    servicio = UpdateService(app_id="asiento",
                             installed_version="2026.09.30.10.00.00",
                             opener=opener_que_responde(FakeResponse(b"")))
    with pytest.raises(ValueError) as error:
        servicio.download(manifest_femag)
    assert "otro producto" in str(error.value)
    assert _archivos_debajo(tmp_path) == []


def test_format_bytes_para_la_barra_de_progreso():
    assert format_bytes(0) == "0 B"
    assert format_bytes(1536) == "1.5 KB"
    assert format_bytes(5 * 1024 * 1024).endswith("MB")
    assert format_bytes(None) == "?"
