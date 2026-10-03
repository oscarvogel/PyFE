# -*- coding: utf-8 -*-
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDesktopWidget, QHBoxLayout, QVBoxLayout

from libs.BarraProgreso import Avance
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import Etiqueta
from libs.Utiles import icono_sistema
# ParamSist ya no se usa en este archivo (lo usaba EstablecerTema, que se
# desactivo). El import se deja a proposito: importar el modulo registra el
# modelo en peewee, y como Formulario lo importan casi todas las vistas, sacarlo
# podria cambiar el orden de registro y romper algo en otra pantalla.
from modelos.ParametrosSistema import ParamSist  # noqa: F401


class Formulario(QDialog):

    lblStatusBar = None

    controles = {}

    def __init__(self, parent=None):
        QDialog.__init__(self, parent=None)
        self.Exception = self.Traceback = ""
        self.LanzarExcepciones = False
        self.setWindowIcon(icono_sistema())
        self.setWindowModality(Qt.ApplicationModal)
        # El tema se aplica una sola vez, de forma global, sobre la
        # QApplication (ver libs/tema.py y main.py). Antes cada dialogo
        # intentaba cargar por su cuenta un .css desde el parametro TEMA de la
        # base, dentro de un except: pass: si el archivo no estaba, el dialogo
        # se quedaba sin estilo y ademas tapaba el global con lo que hubiera
        # cargado. Ese metodo quedo desactivado.

    def Cerrar(self):
        self.close()

    def exec_(self):
        self.Center()
        QDialog.exec_(self)

    def Center(self):
        qr = self.frameGeometry()

        # center point of screen
        cp = QDesktopWidget().availableGeometry().center()

        # move rectangle's center point to screen's center point
        qr.moveCenter(cp)

        # top left of rectangle becomes top left of window centering it
        self.move(qr.topLeft())

    def resizeEvent(self, QResizeEvent):
        self.Center()
        QDialog.resizeEvent(self, QResizeEvent)
        print(f"Alto {self.height()} Ancho {self.width()}")

    def addStatusBar(self, layout=None):
        if layout:
            self.lblStatusBar = Etiqueta()
            layout.addWidget(self.lblStatusBar)

    def setTextStatusBar(self, text=''):
        if self.lblStatusBar:
            self.lblStatusBar.setText(text)

    def ArmaEntrada(self, nombre="", boxlayout=None, texto='', *args, **kwargs):
        if not boxlayout:
            boxlayout = QHBoxLayout()
            lAgrega = True
        else:
            lAgrega = False

        if not texto:
            texto = nombre.capitalize()

        labelNombre = Etiqueta(texto=texto)
        labelNombre.setObjectName("labelNombre")
        boxlayout.addWidget(labelNombre)

        if 'control' in kwargs:
            lineEditNombre = kwargs['control']
        else:
            lineEditNombre = EntradaTexto()

        if 'relleno' in kwargs:
            lineEditNombre.relleno = kwargs['relleno']

        lineEditNombre.setObjectName(nombre)
        boxlayout.addWidget(lineEditNombre)
        if 'enabled' in kwargs:
            lineEditNombre.setEnabled(kwargs['enabled'])

        self.controles[nombre] = lineEditNombre

        if lAgrega:
            self.verticalLayoutDatos.addLayout(boxlayout)
        return boxlayout

    def setupUi(self, Form):
        pass

    def ConectarWidgets(self):
        pass

    def EstablecerTema(self):
        """Obsoleto: el tema es global, se aplica en main.py.

        Se deja el metodo para no romper a nadie que lo llame, pero ya no hace
        nada. La version anterior leia el parametro TEMA de la base y aplicaba
        el .css solo a ese dialogo, dentro de un except: pass.
        """
        return
