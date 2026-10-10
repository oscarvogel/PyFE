# coding=utf-8
"""Historial de novedades: que se le muestra al usuario y que ya vio.

Mismo diseno que `servicios/changelog.py` de fgpy, que es de donde sale, con
las rutas de PyFE. La idea del contrato:

- El historial es ACUMULABLE. Cada publicacion agrega una entrada y no borra
  las anteriores.
- Si el usuario salta de la 10:00 a la 13:00, al primer inicio de la 13:00
  ve juntas las novedades de las 11:00, 12:00 y 13:00. Mostrar solo la
  ultima pierde justo lo que el usuario se salto.
- Que version se vio se guarda en un archivo de estado propio, en
  %LOCALAPPDATA%\\<app_id>\\update-state.json. NUNCA en sistema.ini: ese
  archivo lo escribe la app, lo copia el asistente de primer arranque y
  pertenece al usuario. Mezclarse ahi seria escribir sobre la
  configuracion de facturacion desde un chequeo de red.
"""

from __future__ import print_function

import json
import logging
import os
import tempfile

from libs.actualizaciones import USER_AGENT, parse_version
from libs.build_info import APP_ID, BUILD_VERSION, changelog_url_for

LOGGER = logging.getLogger(__name__)


class ChangelogService(object):
    """Consulta del historial y de que falta mostrar."""

    def __init__(self, app_id=APP_ID, installed_version=BUILD_VERSION,
                 timeout=8.0, opener=None, state_root=None):
        self.app_id = app_id
        self.installed_version = installed_version
        self.timeout = timeout
        self._opener = opener
        self._state_root = state_root

    @property
    def state_path(self):
        """Donde queda la marca de 'ya lo vi'. Fuera de la carpeta del programa.

        Que este fuera de {app} no es cosmetico: el instalador reemplaza
        entera la carpeta de instalacion en cada actualizacion, y un estado
        guardado adentro se perderia con cada version nueva (el usuario
        volveria a ver las mismas novedades indefinidamente).
        """
        if self._state_root is not None:
            raiz = self._state_root
        else:
            local = os.environ.get("LOCALAPPDATA")
            raiz = local if local else os.path.join(
                os.path.expanduser("~"), ".local", "share")
        return os.path.join(raiz, self.app_id, "update-state.json")

    def _request(self, url):
        import urllib.request

        peticion = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT})
        if self._opener is not None:
            return self._opener(peticion, timeout=self.timeout)
        return urllib.request.urlopen(peticion, timeout=self.timeout)

    def fetch(self):
        """Devuelve el historial, o [] si no hay nada publicado todavia.

        Un `apps/<app_id>/changelog.json` ausente no es un error: es lo que
        pasa con el primer release. Se devuelve lista vacia para que el
        llamador pueda mostrar un dialogo de novedades sin novedades.

        Y un `app_id` sin changelog registrado (el demo) tampoco: antes la URL
        se resolvia FUERA del try y el ValueError subia. No lo mata hoy
        porque el demo tiene `es_build_productivo()` False y nunca llega
        aca, pero es la clase de fragilidad que aparece sola cuando se agrega
        una app mas.
        """
        try:
            url = changelog_url_for(self.app_id)
        except ValueError:
            LOGGER.info("Changelog: %s no tiene historial publicado",
                        self.app_id)
            return []
        try:
            with self._request(url) as respuesta:
                payload = respuesta.read()
        except Exception:
            LOGGER.info("Changelog: no se pudo leer %s", url)
            return []

        try:
            crudo = json.loads(payload.decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError):
            LOGGER.warning("Changelog: respuesta ilegible en %s", url)
            return []

        if not isinstance(crudo, dict):
            return []
        if int(crudo.get("schema_version", 0) or 0) != 1:
            return []

        # Que el changelog sea del producto de esta app. Sin esto, un
        # manifiesto copiado de otra app haria que Asiento muestre las
        # novedades de FEMAG.
        if str(crudo.get("app_id", "")).strip() != self.app_id:
            LOGGER.warning("Changelog: app_id no corresponde (%r)", crudo.get("app_id"))
            return []

        return self._parse_entries(crudo.get("versions") or [])

    @staticmethod
    def _parse_entries(items):
        """Normaliza entradas y descarta las que no se pueden usar.

        Se descarta en vez de propagar el error: una entrada corrupta de una
        version vieja no puede impedir mostrar las novedades de las nuevas.
        """
        entradas = []
        vistas = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            version = str(item.get("version", "")).strip()
            notas = [str(n).strip() for n in (item.get("notes") or [])
                     if str(n).strip()]
            if not version or not notas or version in vistas:
                continue
            try:
                parse_version(version)
            except ValueError:
                LOGGER.warning("Changelog: version invalida %r, se descarta", version)
                continue
            vistas.add(version)
            entradas.append({
                "version": version,
                "published_at": str(item.get("published_at", "")).strip(),
                "notes": notas,
            })

        # De mas nueva a mas vieja: es el orden en que se leen.
        entradas.sort(key=lambda e: parse_version(e["version"]), reverse=True)
        return entradas

    def last_seen_version(self):
        """Ultima version cuyo changelog ya se mostro, o None."""
        ruta = self.state_path
        try:
            if not os.path.isfile(ruta):
                return None
            with open(ruta, "r", encoding="utf-8-sig") as fh:
                crudo = json.load(fh)
        except Exception:
            LOGGER.info("Changelog: no se pudo leer el estado local")
            return None

        if not isinstance(crudo, dict):
            return None
        if str(crudo.get("app_id", "")).strip() != self.app_id:
            # Estado de otra app: se ignora en vez de confiar en el.
            return None
        version = str(crudo.get("last_changelog_version_seen", "")).strip()
        if not version:
            return None
        try:
            parse_version(version)
        except ValueError:
            return None
        return version

    def pending(self, entradas):
        """Entradas que hay que mostrarle al usuario todavia.

        Son las que estan entre la ultima vista y la version instalada,
        ambas inclusive: la de la version instalada se incluye, porque si
        acaba de actualizar es la que todavia no vio.
        """
        if not entradas:
            return []
        try:
            instalada = parse_version(self.installed_version)
        except ValueError:
            return []

        try:
            vista = self.last_seen_version()
        except Exception:
            vista = None
        vista_tuple = None
        if vista:
            try:
                vista_tuple = parse_version(vista)
            except ValueError:
                vista_tuple = None

        pendientes = []
        for entrada in entradas:
            version = parse_version(entrada["version"])
            if version > instalada:
                # Publicada para una version que todavia no se instalo.
                continue
            if vista_tuple is not None and version <= vista_tuple:
                continue
            pendientes.append(entrada)
        return pendientes

    def mark_seen(self, version=None):
        """Guarda que version se mostro. Escritura atomica.

        Se escribe a un temporal y se renombra: si la app se cierra a mitad
        de escritura, el archivo de estado queda entero o no existe. Un
        JSON truncadoeria hacer perder el historial visto para siempre.
        """
        version = version or self.installed_version
        parse_version(version)
        ruta = self.state_path
        carpeta = os.path.dirname(ruta)
        if not os.path.isdir(carpeta):
            os.makedirs(carpeta)

        payload = {
            "schema_version": 1,
            "app_id": self.app_id,
            "last_changelog_version_seen": version,
        }
        fd, temporal = tempfile.mkstemp(
            prefix="update-state-", suffix=".tmp", dir=carpeta)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            if os.path.exists(ruta):
                os.remove(ruta)
            os.rename(temporal, ruta)
        except Exception:
            try:
                os.remove(temporal)
            except OSError:
                pass
            raise
