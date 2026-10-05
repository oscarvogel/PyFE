# coding=utf-8
"""Actualizador en PyQt5: aviso, descarga con progreso y novedades.

Se apoya en `libs/actualizaciones.py` y `libs/changelog.py`, que no saben
nada de Qt. Toda la UI esta en este archivo para que el nucleo se pueda
probar sin levantar una ventana.

Regla de la casa, del doc de fgpy y femag: **si algo falla, la app abre
igual**. Ninguna excepcion de este controlador llega al arranque. Un chequeo
de red que tira abajo la facturacion seria peor que no tener actualizador.
"""

from __future__ import print_function

import logging
import os
import subprocess

from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
                             QPushButton, QTextBrowser, QVBoxLayout,
                             QProgressDialog)

from libs.actualizaciones import (DownloadCancelled, UpdateService,
                                  format_bytes)
from libs.build_info import APP_ID, BUILD_VERSION, es_build_productivo
from libs.changelog import ChangelogService

LOGGER = logging.getLogger(__name__)

# Color de la marca, para los titulos de las novedades. El mismo navy que
# usa la placa del logo en el shell.
NAVY = "#031A3E"


class _ChequeoWorker(QObject):
    """Consulta manifiesto y changelog fuera del hilo grafico.

    Va en un QThread y no en un QRunnable a proposito: hace falta poder
    esperar su resultado antes de decidir si se muestra algo, y con
    QRunnable habria que resolverlo con senales encadenadas que dependen del
    orden de entrega. Un hilo con una senal de 'listo' es determinista.
    """

    listo = pyqtSignal(object, object)

    def __init__(self, service=None, changelog=None):
        super(_ChequeoWorker, self).__init__()
        self.service = service or UpdateService()
        self.changelog = changelog or ChangelogService()
        self.resultado = None
        self.pendientes = []
        self.error = None

    def run(self):
        """Cada consulta va en su propio try. Un changelog roto no puede
        tapar una actualizacion disponible, y al reves."""
        try:
            self.resultado = self.service.check()
        except Exception as exc:
            LOGGER.info("Actualizador: chequeo no concluyente (%s)", exc)
            self.error = str(exc)

        try:
            self.pendientes = self.changelog.pending(self.changelog.fetch())
        except Exception as exc:
            LOGGER.info("Actualizador: sin novedades (%s)", exc)

        self.listo.emit(self.resultado, self.pendientes)


class _DescargaWorker(QObject):
    """Descarga el instalador con progreso y cancelacion."""

    progreso = pyqtSignal(int, object)
    terminado = pyqtSignal(object)
    fallido = pyqtSignal(str)
    cancelado = pyqtSignal()

    def __init__(self, service, manifest):
        super(_DescargaWorker, self).__init__()
        self.service = service
        self.manifest = manifest
        self._cancelado = False

    def cancelar(self):
        self._cancelado = True

    def run(self):
        try:
            ruta = self.service.download(
                self.manifest,
                progress_callback=lambda b, t: self.progreso.emit(b, t),
                cancel_callback=lambda: self._cancelado)
            self.terminado.emit(ruta)
        except DownloadCancelled:
            self.cancelado.emit()
        except Exception as exc:
            LOGGER.exception("Actualizador: fallo la descarga")
            self.fallido.emit(str(exc))


class DialogoNovedades(QDialog):
    """Novedades acumuladas de todo lo que el usuario se salto.

    Si el usuario venia de la 10:00 y ahora esta en la 13:00, aca aparecen
    las de las 11:00, 12:00 y 13:00 juntas. Mostrar solo la ultima seria
    mostrarle justamente lo que ya se salte.
    """

    def __init__(self, pendientes, parent=None):
        super(DialogoNovedades, self).__init__(parent)
        self.setWindowTitle("Novedades de Asiento")
        self.setMinimumSize(520, 380)

        vertical = QVBoxLayout(self)
        titulo = QLabel("Que hay de nuevo")
        titulo.setStyleSheet("font-size: 15px; font-weight: 600; color: {};".format(NAVY))
        vertical.addWidget(titulo)

        navegador = QTextBrowser()
        navegador.setOpenExternalLinks(False)
        for entrada in pendientes:
            navegador.append(
                '<p style="margin-top:10px"><b style="color:{}">Version {}</b></p>'
                .format(NAVY, entrada["version"]))
            for nota in entrada["notes"]:
                navegador.append("<p style='margin-left:12px'>• {}</p>".format(nota))
            navegador.append("")
        vertical.addWidget(navegador, 1)

        fila = QHBoxLayout()
        fila.addStretch(1)
        # Boton propio y no QDialogButtonBox: el de la caja toma el idioma
        # del sistema y en una maquina en ingles salia "Close" en una
        # pantalla que esta toda en Castellano.
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.accept)
        fila.addWidget(cerrar)
        vertical.addLayout(fila)


class ActualizadorController(object):
    """Orquesta el chequeo, la descarga y el aviso. Sin estado global."""

    def __init__(self, service=None, changelog=None):
        # En desarrollo no se crea nada: el service se construye perezoso
        # para que correr la app desde el repo no intente actualizarse.
        self.service = service
        self.changelog_service = changelog

    # --- infraestructura -------------------------------------------------

    def _get_service(self):
        if self.service is None:
            self.service = UpdateService()
        return self.service

    def _get_changelog(self):
        if self.changelog_service is None:
            self.changelog_service = ChangelogService()
        return self.changelog_service

    def habilitado(self):
        return es_build_productivo()

    # --- arranque --------------------------------------------------------

    def chequear_al_arranque(self, parent=None, al_terminar=None):
        """Lanza el chequeo en segundo plano y no bloquea el arranque.

        Devuelve el QThread para que el llamador pueda mantenerlo con vida.
        Si el usuario cierra la app antes de que termine, el worker se
        descarta solo: el hilo termina y el objeto se borra con el.
        """
        if not self.habilitado():
            LOGGER.info("Actualizador omitido: build de desarrollo")
            return None

        hilo = QThread()
        worker = _ChequeoWorker(self._get_service(), self._get_changelog())
        worker.moveToThread(hilo)

        def terminado(resultado, pendientes):
            try:
                self._procesar(resultado, pendientes, parent)
            except Exception:
                LOGGER.exception("Actualizador: fallo al procesar el resultado")
            if al_terminar is not None:
                try:
                    al_terminar()
                except Exception:
                    LOGGER.exception("Actualizador: fallo en el callback de fin")
            hilo.quit()

        worker.listo.connect(terminado)
        hilo.started.connect(worker.run)
        worker.listo.connect(worker.deleteLater)
        hilo.finished.connect(hilo.deleteLater)
        hilo.start()
        return hilo

    def _procesar(self, resultado, pendientes, parent):
        """Primero las novedades, despues la actualizacion.

        El orden es a proposito: si el usuario acaba de instalar una
        version nueva, lo primero que quiere saber es que cambio, no que
        hay otra para bajar.
        """
        if pendientes:
            dialogo = DialogoNovedades(pendientes, parent)
            dialogo.exec_()
            # Se marca recien DESPUES de cerrar el dialogo, y sin `finally` a
            # proposito: si el dialogo no llega a mostrarse, la app se
            # quiere cerrar o la UI falla, el usuario no lo vio y al proximo
            # arranque tiene que volver a aparecer. Con un finally, cualquier
            # excepcion marcaria las novedades como vistas para siempre.
            try:
                self._get_changelog().mark_seen()
            except Exception:
                LOGGER.exception("Actualizador: no se pudo marcar el changelog")

        if resultado is None or not resultado.update_available:
            return False

        manifest = resultado.manifest
        mensaje = (
            "Hay una version nueva disponible.\n\n"
            "Version instalada: {}\n"
            "Version nueva: {}\n\n"
            "{}\n\nDesea descargarla ahora?"
        ).format(resultado.installed_version, manifest.version, manifest.notes)

        from libs.Ventanas import showConfirmation

        if not showConfirmation("Actualizacion disponible", mensaje,
                                textoOk="Descargar", textoCancelar="Ahora no"):
            return False

        return self.descargar_e_instalar(manifest, parent)

    # --- descarga --------------------------------------------------------

    def _descargar_con_progreso(self, manifest, parent=None):
        service = self._get_service()
        dialogo = QProgressDialog("Descargando actualizacion...", "Cancelar",
                                  0, 100, parent)
        dialogo.setWindowTitle("Actualizacion")
        dialogo.setAutoClose(False)
        dialogo.setAutoReset(False)
        dialogo.setMinimumDuration(0)
        dialogo.setValue(0)

        hilo = QThread()
        worker = _DescargaWorker(service, manifest)
        worker.moveToThread(hilo)

        resultado = {"ruta": None, "error": None, "cancelado": False}

        def on_progreso(descargado, total):
            if total:
                porcentaje = max(0, min(100, int(descargado * 100 / total)))
                dialogo.setRange(0, 100)
                dialogo.setValue(porcentaje)
                dialogo.setLabelText(
                    "Descargando actualizacion... {}%\n{} de {}".format(
                        porcentaje, format_bytes(descargado), format_bytes(total)))
            else:
                # Sin Content-Length no hay porcentaje, pero tampoco hay
                # motivo para dejar la barra quieta.
                dialogo.setRange(0, 0)
                dialogo.setLabelText("Descargando actualizacion...\n{} descargados"
                                     .format(format_bytes(descargado)))

        def on_terminado(ruta):
            resultado["ruta"] = ruta
            dialogo.setLabelText("Verificando archivo...\nActualizacion verificada.")

        def on_fallido(mensaje_error):
            resultado["error"] = mensaje_error
            dialogo.close()

        def on_cancelado():
            resultado["cancelado"] = True
            dialogo.close()

        worker.progreso.connect(on_progreso)
        worker.terminado.connect(on_terminado)
        worker.terminado.connect(dialogo.close)
        worker.fallido.connect(on_fallido)
        worker.cancelado.connect(on_cancelado)
        dialogo.canceled.connect(worker.cancelar)
        hilo.started.connect(worker.run)
        worker.terminado.connect(hilo.quit)
        worker.fallido.connect(hilo.quit)
        worker.cancelado.connect(hilo.quit)
        worker.terminado.connect(worker.deleteLater)
        worker.fallido.connect(worker.deleteLater)
        worker.cancelado.connect(worker.deleteLater)
        hilo.finished.connect(hilo.deleteLater)
        hilo.start()

        dialogo.exec_()
        # Por si el usuario cerro el dialogo a mano sin pasar por Cancelar.
        hilo.quit()
        hilo.wait(3000)

        if resultado["cancelado"]:
            return None
        if resultado["error"]:
            raise RuntimeError(resultado["error"])
        return resultado["ruta"]

    def descargar_e_instalar(self, manifest, parent=None):
        """Descarga, verifica y ofrece instalar. Devuelve True si lanzo."""
        from libs.Ventanas import showAlert, showConfirmation

        try:
            instalador = self._descargar_con_progreso(manifest, parent)
        except Exception as exc:
            LOGGER.exception("Actualizador: no se pudo descargar")
            showAlert("Actualizacion",
                      "No se pudo descargar o validar la actualizacion.\n\n"
                      "{}\n\nEl sistema sigue funcionando normalmente.".format(exc))
            return False

        if instalador is None:
            return False

        if not showConfirmation(
                "Actualizacion descargada",
                "El instalador se descargo y se verifico con SHA256.\n\n"
                "Se va a cerrar Asiento para instalarlo. Esto no afecta la base "
                "de datos ni la configuracion.\n\nDesea instalar ahora?",
                textoOk="Instalar", textoCancelar="Ahora no"):
            return False

        return self.lanzar_instalador(instalador, parent)

    @staticmethod
    def lanzar_instalador(ruta, parent=None):
        """Ejecuta el instalador y cierra la app.

        El cierre es obligatorio, no una cortesia: el instalador de Inno
        reemplaza el .exe que esta corriendo y con `CloseApplications=yes`
        intenta cerrarlo. Si la app sigue viva, el reemplazo falla y el
        usuario ve un error de instalador en el mejor de los casos.
        """
        if not os.path.isfile(ruta):
            LOGGER.warning("Actualizador: el instalador no existe: %s", ruta)
            return False
        try:
            LOGGER.info("Actualizador: lanzando %s", ruta)
            # shell=False: la ruta viene de un manifiesto remoto, y con
            # shell=True un nombre con espacios pasaria a ser un comando.
            subprocess.Popen([ruta], shell=False)
        except Exception:
            LOGGER.exception("Actualizador: no se pudo lanzar el instalador")
            from libs.Ventanas import showAlert
            showAlert("Actualizacion",
                      "No se pudo abrir el instalador. El sistema sigue "
                      "funcionando normalmente.")
            return False

        # Salir despues de arrancar el instalador: al revés, la app se
        # cierra antes de que el proceso hijo quede bien agarrado.
        aplicacion = QApplication.instance()
        if aplicacion is not None:
            aplicacion.quit()
        return True


def version_instalada_visible():
    """La version que se le muestra al usuario, con el prefijo v.

    Prefiere build_info (la del build) y cae a lo que haya en version.txt.
    """
    from libs.actualizaciones import VERSION_RE

    version = (BUILD_VERSION or "").strip()
    if VERSION_RE.match(version):
        return "v" + version
    return version or ""
