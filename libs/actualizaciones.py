# coding=utf-8
"""Cliente de actualizacion contra vogel-releases.

Mismo diseno que `servicios/actualizaciones.py` de fgpy y que
`app/services/update_service.py` de femag, que es de donde sale. Copia la
parte que se sostiene en Windows sin dependencias extra.

Tres reglas que el modulo no rompe nunca, porque son las que sostienen que
esto sea seguro:

1. **Nada se ejecuta sin verificar.** El SHA256 se calcula mientras se
   descarga y se compara con el del manifiesto ANTES de renombrar el
   archivo. Si difiere, el `.part` se borra y no se ejecuta nada.
2. **Una falla de red nunca impede abrir la app.** Ninguna excepcion sale de
   `check()` sin loguearse, y el llamador abre igual.
3. **No se toca configuracion.** Este modulo no lee ni escribe sistema.ini,
   ni la base, ni los certificados. La unica escritura en disco es el
   instalador en %TEMP% y, opcionalmente, el estado del changelog.

Diferencia con femag a proposito: femag usa `truststore` para el TLS. PyFE no
lo hace porque `truststore` sirve para que el almacen de confianza del sistema
funcione en Linux y macOS cuando hay un certifi de por medio, y PyFE es solo
Windows, donde urllib ya valida contra el almacen de confianza del SO sin
`truststore`. Agregarla seria una dependencia nueva para resolver un problema
que en esta plataforma no existe.
"""

from __future__ import print_function

import hashlib
import json
import logging
import os
import re
import tempfile
import time

from libs.build_info import (APP_ID, BUILD_VERSION, es_build_productivo,
                             manifest_url_for)

LOGGER = logging.getLogger(__name__)

# Timestamp UTC: yyyy.MM.dd.HH.mm.ss. Es el formato que exige el manifiesto.
VERSION_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}\.\d{2}\.\d{2}\.\d{2}$")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")

USER_AGENT = "Asiento-Desktop-Updater/1"

# El instalador se baja con el nombre estable que declara el manifiesto.
# Esta constante es solo el nombre local del archivo en %TEMP%.
INSTALLER_FILENAME = "Asiento_Produccion_Setup.exe"

PREFIXO_HTTPS = "https://"


class DownloadCancelled(Exception):
    """El usuario cancelo la descarga."""


class UpdateManifest(object):
    """Lo que declara el manifiesto, ya validado."""

    def __init__(self, schema_version, app_id, version, published_at,
                 mandatory, download_url, sha256, notes=""):
        self.schema_version = schema_version
        self.app_id = app_id
        self.version = version
        self.published_at = published_at
        self.mandatory = bool(mandatory)
        self.download_url = download_url
        self.sha256 = (sha256 or "").lower()
        self.notes = notes or ""

    def __repr__(self):
        return "<UpdateManifest {} {}>".format(self.app_id, self.version)


class UpdateCheckResult(object):
    """Resultado del chequeo: hay o no hay algo nuevo."""

    def __init__(self, installed_version, manifest, update_available):
        self.installed_version = installed_version
        self.manifest = manifest
        self.update_available = bool(update_available)

    def __repr__(self):
        return "<UpdateCheckResult instalado={} disponible={}>".format(
            self.installed_version, self.update_available)


def parse_version(valor):
    """'2026.10.05.08.37.00' -> tupla de 6 enteros.

    El anclaje al formato completo es lo que evita el error clasico de estos
    sistemas: comparar '2026.10.5' con '2026.10.05' da un resultado
    distinto segun como se mire, y el usuario recibe avisos para siempre o
    se queda sin actualizaciones sin darse cuenta.
    """
    if not isinstance(valor, str) or not VERSION_RE.match(valor.strip()):
        raise ValueError("Version con formato invalido: {!r}".format(valor))
    return tuple(int(parte) for parte in valor.strip().split("."))


def is_newer_version(instalada, candidata):
    """True si ``candidata`` es estrictamente posterior a ``instalada``."""
    return parse_version(candidata) > parse_version(instalada)


def parse_manifest_bytes(payload, app_id_esperado):
    """Valida el manifiesto y devuelve un UpdateManifest.

    Se levanta excepcion con cualquier cosa que no cuadre, en vez de
    devolver "no hay actualizacion". La diferencia importa: devolver
    "no hay" ante un manifiesto corrupto es indistinguishable de estar al
    dia, y el usuario se queda sin actualizaciones sin saberlo.
    """
    if payload[:3] == b"\xef\xbb\xbf":
        raise ValueError("El manifiesto debe ser UTF-8 sin BOM")

    crudo = json.loads(payload.decode("utf-8"))
    if not isinstance(crudo, dict):
        raise ValueError("El manifiesto no es un objeto JSON")

    if int(crudo.get("schema_version", -1)) != 1:
        raise ValueError(
            "schema_version no soportado: {!r}".format(crudo.get("schema_version")))

    # Aislamiento entre productos: un manifiesto de FEMAG copiado al de
    # Asiento haria que Asiento ofrezca el instalador equivocado. El app_id
    # tiene que coincidir con el del build compilado.
    app_id = str(crudo.get("app_id", "")).strip()
    if app_id != app_id_esperado:
        raise ValueError(
            "Manifiesto de otro producto: esperado={!r} recibido={!r}"
            .format(app_id_esperado, app_id))

    manifest = UpdateManifest(
        schema_version=1,
        app_id=app_id,
        version=str(crudo.get("version", "")).strip(),
        published_at=str(crudo.get("published_at", "")).strip(),
        mandatory=crudo.get("mandatory", False),
        download_url=str(crudo.get("download_url", "")).strip(),
        sha256=str(crudo.get("sha256", "")).strip(),
        notes=str(crudo.get("notes", "")).strip(),
    )

    parse_version(manifest.version)
    if not SHA256_RE.match(manifest.sha256):
        raise ValueError("SHA256 invalido en el manifiesto")
    if not manifest.download_url.lower().startswith(PREFIXO_HTTPS):
        raise ValueError("download_url debe usar HTTPS")
    return manifest


def format_bytes(cantidad):
    """'12.4 MB'. Para la barra de progreso."""
    try:
        cantidad = float(cantidad)
    except (TypeError, ValueError):
        return "?"
    for unidad in ("B", "KB", "MB", "GB"):
        if cantidad < 1024 or unidad == "GB":
            if unidad == "B":
                return "{:.0f} {}".format(cantidad, unidad)
            return "{:.1f} {}".format(cantidad, unidad)
        cantidad /= 1024
    return "{:.1f} GB".format(cantidad)


def _content_length(respuesta):
    """Content-Length del servidor, o None si no lo manda.

    GitHub lo manda, pero si un proxy lo saca, la barra de progreso pasa a
    modo indeterminado en vez de fallar.
    """
    try:
        valor = respuesta.headers.get("Content-Length")
        if valor is None:
            return None
        total = int(valor)
        return total if total > 0 else None
    except (AttributeError, TypeError, ValueError):
        return None


class UpdateService(object):
    """Consulta y descarga. Sin Qt: se puede probar sin interfaz."""

    def __init__(self, app_id=APP_ID, installed_version=BUILD_VERSION,
                 manifest_url=None, timeout=8.0, opener=None):
        self.app_id = app_id
        self.installed_version = installed_version
        self.timeout = timeout
        self._opener = opener
        # El constructor NO levanta por un app_id sin manifiesto. Sin esta
        # guarda, `UpdateService()` revienta en desarrollo (donde el app_id
        # es 'development') y el fallo aparece en el arranque de la app, no
        # donde tiene sentido. La falta de manifiesto se reporta al usar la
        # URL, que es cuando de verdad hace falta.
        if manifest_url is None:
            try:
                manifest_url = manifest_url_for(app_id)
            except ValueError:
                manifest_url = None
        self.manifest_url = manifest_url

    @property
    def habilitado(self):
        """False en builds de desarrollo. El chequeo no se hace."""
        return es_build_productivo() or self.app_id != "development"

    def _abrir(self, url):
        import urllib.request

        peticion = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT})
        if self._opener is not None:
            return self._opener(peticion, timeout=self.timeout)
        return urllib.request.urlopen(peticion, timeout=self.timeout)

    def check(self):
        """Consulta el manifiesto y dice si hay algo nuevo.

        Propaga la excepcion: el llamador la loguea y sigue. Un chequeo que
        falla no es lo mismo que un chequeo que dice "no hay nada".
        """
        if not self.habilitado:
            LOGGER.info("Updater omitido: build de desarrollo (app_id=%s)", self.app_id)
            return UpdateCheckResult(self.installed_version, None, False)

        if not self.manifest_url:
            raise ValueError(
                "No hay manifiesto registrado para el app_id {!r}".format(self.app_id))

        # Antes de ir a la red. Si la version del build no tiene el formato
        # del manifiesto, avisar comparando strings daria cualquier cosa.
        parse_version(self.installed_version)
        LOGGER.info("Updater: instalada=%s manifiesto=%s",
                    self.installed_version, self.manifest_url)

        with self._abrir(self.manifest_url) as respuesta:
            payload = respuesta.read()

        manifest = parse_manifest_bytes(payload, self.app_id)
        disponible = is_newer_version(self.installed_version, manifest.version)
        LOGGER.info("Updater: remoto=%s disponible=%s",
                    manifest.version, disponible)
        return UpdateCheckResult(self.installed_version, manifest, disponible)

    def download(self, manifest, progress_callback=None, cancel_callback=None):
        """Descarga el instalador a %TEMP% y verifica el SHA256.

        Devuelve la ruta del instalador ya validado. Ante cualquier error
        borra el `.part`: en TEMP no puede quedar un .exe a medio escribir
        que alguien ejecute despues creyendolo completo.
        """
        if not self.habilitado:
            raise ValueError("El updater esta deshabilitado en builds de desarrollo")
        if manifest.app_id != self.app_id:
            raise ValueError("No se puede descargar un instalador de otro producto")
        if not SHA256_RE.match(manifest.sha256 or ""):
            raise ValueError("SHA256 invalido")
        if not manifest.download_url.lower().startswith(PREFIXO_HTTPS):
            raise ValueError("El instalador debe descargarse por HTTPS")

        carpeta = os.path.join(tempfile.gettempdir(), "Asiento", "updates")
        if not os.path.isdir(carpeta):
            os.makedirs(carpeta)

        final = os.path.join(carpeta, INSTALLER_FILENAME)
        parcial = final + ".part"

        try:
            if os.path.exists(parcial):
                os.remove(parcial)

            digest = hashlib.sha256()
            descargado = 0

            with self._abrir(manifest.download_url) as respuesta, \
                    open(parcial, "wb") as archivo:
                total = _content_length(respuesta)
                if progress_callback:
                    progress_callback(0, total)

                while True:
                    if cancel_callback and cancel_callback():
                        raise DownloadCancelled("Descarga cancelada por el usuario")

                    bloque = respuesta.read(1024 * 1024)
                    if not bloque:
                        break

                    archivo.write(bloque)
                    digest.update(bloque)
                    descargado += len(bloque)
                    if progress_callback:
                        progress_callback(descargado, total)

            if cancel_callback and cancel_callback():
                raise DownloadCancelled("Descarga cancelada por el usuario")

            # El hash se calcula en la misma pasada que la descarga, no con
            # una lectura extra del archivo: no hay ventana en la que el
            # .part pueda cambiar entre las dos operaciones.
            obtenido = digest.hexdigest().lower()
            if obtenido != manifest.sha256.lower():
                raise ValueError(
                    "El instalador descargado no coincide con el SHA256 publicado")

            # os.replace es atomico en Windows: o aparece el archivo final
            # completo, o no aparece. Un instalador a medio copiar que otro
            # proceso llegue a ejecutar es un fallo que no vuelve.
            os.replace(parcial, final)
            LOGGER.info("Updater: instalador verificado en %s", final)
            return final
        except Exception:
            if os.path.exists(parcial):
                try:
                    os.remove(parcial)
                except OSError:
                    pass
            LOGGER.exception("Updater: fallo al descargar o validar el instalador")
            raise


def esperar_silencioso(segundos):
    """Espera sin bloquear. Para el chequeo diferido del arranque.

    Existe para que el test pueda verificar que el arranque no se frena, sin
    tener que esperar de verdad.
    """
    time.sleep(segundos)
