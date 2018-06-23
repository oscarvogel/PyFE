# coding=utf-8
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QWidget, QDialog

from libs.Formulario import Formulario
from libs.Utiles import icono_sistema


class VistaBase(Formulario):

    LanzarExcepciones = False

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self)
        self.setWindowIcon(icono_sistema())

    def initUi(self):
        pass

    def cerrarformulario(self):
        self.close()

    def ConectarWidgets(self):
        pass