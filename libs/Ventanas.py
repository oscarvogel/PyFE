# coding=utf-8
"""Avisos, confirmaciones y progreso.

Que cambia respecto de antes
---------------------------
showAlert se usaba para TODO: para informar, para preguntar y para avisar un
error. Con el icono de "información" y un solo botón Ok, un rechazo de AFIP se
veía igual que un "grabado correctamente", y el usuario no tenia forma de
saber si algo habia salido mal ni de llevarse el texto para pasarlo a soporte.

Ahora hay tres cosas distintas:

  showAlert       informar. Contexto.
  showError       Algo fallo: que paso, QUE HACER, y un detalle que se puede
                  copiar para pasarlo a soporte.
  showConfirmation  Preguntar antes de algo que no se puede deshacer. El boton
                  por defecto es el que cancela.

Y Progreso, que va diciendo en que etapa va una operacion larga. Emitir una
factura contra AFIP tarda, y sin esto la ventana queda muerta sin explicacion.
"""
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import (QApplication, QMessageBox, QPushButton, QWidget)

from libs.Utiles import icono_sistema


def hay_interfaz():
    """Hay una ventana donde mostrar algo?

    Sin esto, armar un QMessageBox sin QApplication revienta el proceso con
    0xC0000409 en vez de dar un error de Python: los tests y las herramientas de
    linea de comandos (armar_sandbox, render_ui) morian sin dejar rastro.
    """
    return QApplication.instance() is not None


def _sin_interfaz(titulo, mensaje):
    """No hay donde mostrarlo: que quede en la consola, no desaparecer."""
    sys.stderr.write("\n[{}] {}\n".format(titulo, mensaje))


def _base(titulo, icono):
    msg = QMessageBox()
    msg.setWindowIcon(icono_sistema())
    msg.setWindowTitle(titulo)
    msg.setIcon(icono)
    return msg


def showAlert(titulo, mensaje):
    """Informar. Para avisos y resultados, NO para errores."""
    if not hay_interfaz():
        _sin_interfaz(titulo, mensaje)
        return None
    msg = _base(titulo, QMessageBox.Information)
    msg.setText(mensaje)
    return msg.exec_()


def showError(titulo, mensaje, que_hacer=None, detalle=None):
    """Aviso de error: que paso, que hacer y el detalle tecnico.

    `que_hacer` es la parte que hace la diferencia: "El certificado vencio.
    Renovar los certificados" le sirve al usuario; el codigo 1005 de AFIP no.

    `detalle` es para soporte: va en un area de texto que se puede copiar, no
    mostrado de entrada, porque a nadie le sirve leer un traceback de entrada.
    """
    if not hay_interfaz():
        _sin_interfaz(titulo, "{}\n{}\n{}".format(mensaje, que_hacer or "",
                                                 detalle or ""))
        return None
    msg = _base(titulo, QMessageBox.Critical)
    msg.setText(mensaje)
    msg.setInformativeText(que_hacer or "")
    if detalle:
        msg.setDetailedText(detalle)
        # Un boton propio para copiar: el texto seleccionado a mano de un
        # traceback de 40 lineas es un FASTIDIO.
        copiar = QPushButton("Copiar detalle")
        copiar.setToolTip("Pega este texto si llamás a soporte")
        copiar.clicked.connect(lambda: QGuiApplication.clipboard().setText(
            "{}\n\n{}".format(mensaje, detalle)))
        msg.addButton(copiar, QMessageBox.ActionRole)
    msg.addButton(QMessageBox.Ok)
    msg.setDefaultButton(QMessageBox.Ok)
    return msg.exec_()


def showConfirmation(titulo, mensaje, textoOk="Sí", textoCancelar="Cancelar",
                     por_defecto_cancelar=True):
    """Pregunta antes de algo que no se puede deshacer.

    Devuelve True solo si la persona confirmo. El boton por defecto es
    cancelar: en una pantalla con botones pegados, la tecla Enter no deberia
    autorizar una factura.

    `textoOk` se acepta con guion o sin, por las dos formas de llamarlo.

    Sin interfaz devuelve False. Es el default que corresponde: si no se puede
    preguntar, no se autoriza.
    """
    if not hay_interfaz():
        _sin_interfaz(titulo, "{} -> SIN RESPUESTA, se toma como NO".format(mensaje))
        return False
    msg = _base(titulo, QMessageBox.Question)
    msg.setText(mensaje)
    ok = msg.addButton(textoOk.replace("-", ""), QMessageBox.AcceptRole)
    cancelar = msg.addButton(textoCancelar, QMessageBox.RejectRole)
    msg.setDefaultButton(cancelar if por_defecto_cancelar else ok)
    msg.exec_()
    return msg.clickedButton() is ok


class Progreso(object):
    """Ventana de progreso con las etapas REALES de una operacion.

    Se usa asi:

        with Progreso("Emitiendo la factura", [
                "Comprobando los datos",
                "Autenticando en AFIP",
                "Enviando la factura",
                "Obteniendo el CAE",
                "Generando el PDF"]) as pasos:
            pasos.avanzar("Comprobando los datos")
            ...

    Se cierra solo al salir del bloque, haya terminatingado bien o mal.

    Un detalle importante: la operacion sigue siendo SINCRONICA, asi que entre
    etapas hay que llamar `refrescar()` para que Qt pinte el cambio. Sin eso la
    ventana de progreso aparece pero no se mueve, que es peor que nada.

    Sin interfaz (tests, herramientas de linea de comandos) no dibuja nada pero
    sigue anotando las etapas, para poder verificarlas.
    """

    def __init__(self, titulo, etapas, cancelable=False):
        from PyQt5.QtWidgets import QProgressDialog
        self.etapas = list(etapas)
        self.cancelado = False
        self.actual = None
        self.dialogo = None
        if not hay_interfaz():
            return
        self.dialogo = QProgressDialog(titulo, "Cancelar" if cancelable else "", 0,
                                       max(1, len(self.etapas)))
        self.dialogo.setWindowTitle(titulo)
        self.dialogo.setWindowModality(Qt.WindowModal)
        self.dialogo.setMinimumDuration(0)      # que aparezca de entrada
        self.dialogo.setAutoClose(False)
        self.dialogo.setAutoReset(False)
        self.dialogo.setValue(0)
        if cancelable:
            self.dialogo.canceled.connect(self._al_cancelar)
        else:
            # Sin boton de cancelar: una emision ya empezada no se puede
            # deshacer, y ofrecer un cancelar que no hace nada es peor que no
            # ofrecerlo.
            self.dialogo.setCancelButton(None)
        self.dialogo.show()
        QApplication.processEvents()

    def _al_cancelar(self):
        self.cancelado = True

    def avanzar(self, etapa=None, detalle=None):
        """Pasa a la etapa siguiente. `detalle` va en el subtitulo."""
        self.actual = etapa
        if self.dialogo is None:
            return
        self.dialogo.setValue(min(self.dialogo.value() + 1,
                                   len(self.etapas)))
        if etapa:
            self.dialogo.setLabelText(
                "{} ({} de {})".format(etapa, self.dialogo.value(),
                                       len(self.etapas)))
        if detalle:
            self.dialogo.setLabelText("{} — {}".format(etapa or "", detalle))
        self.refrescar()

    def refrescar(self):
        """Deja que Qt pinte. Hay que llamarlo entre etapas."""
        if self.dialogo is not None:
            QApplication.processEvents()

    def error(self, mensaje):
        """Cambia el dialogo a estado de error sin cerrarlo."""
        self.actual = mensaje
        if self.dialogo is None:
            return
        self.dialogo.setLabelText(mensaje)
        self.refrescar()

    def cerrar(self):
        if self.dialogo is None:
            return
        self.dialogo.reset()
        self.dialogo.close()
        self.dialogo = None

    def __enter__(self):
        return self

    def __exit__(self, tipo, valor, traza):
        self.cerrar()
        return False


def window():
    app = QApplication(sys.argv)
    w = QWidget()
    b = QPushButton(w)
    b.setText("Show message!")
    b.move(50, 50)
    b.clicked.connect(showdialog)
    w.setWindowTitle("PyQt Dialog demo")
    w.show()
    sys.exit(app.exec_())


def showdialog():
    if showConfirmation("Sistema", "Desea imprimir el presupuesto?"):
        print("Valor de retorno {}".format(True))


if __name__ == "__main__":
    window()
