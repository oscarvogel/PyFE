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

    # Piso de tamano de una ventana de trabajo. Mas chico que esto, las
    # pantallas quedan "apretadas": la grilla se come el ancho, las columnas
    # quedan en su minimo de 56 px y el operador ve una franja de numeros.
    #
    # El piso esta aca y no ventana por ventana porque en veinticuatro
    # pantallas queda viejo apenas se agrega una, y nadie lo va a notar.
    ANCHO_MINIMO = 900
    ALTO_MINIMO = 560

    # Un dialogo chico --configurar el correo, el primer arranque-- no
    # necesita una pantalla entera. Lo que decide es si tiene grilla, que es lo
    # que de verdad necesita ancho.
    ANCHO_MINIMO_CHICO = 620
    ALTO_MINIMO_CHICO = 420

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

    def _piso_de_tamano(self):
        """(ancho, alto) que esta ventana no deberia bajar."""
        from PyQt5.QtWidgets import QTableWidget

        if self.findChildren(QTableWidget):
            return self.ANCHO_MINIMO, self.ALTO_MINIMO
        return self.ANCHO_MINIMO_CHICO, self.ALTO_MINIMO_CHICO

    def declara_tamano(self, ancho, alto):
        """El tamano que esta ventana quiere, y con el mismo numero el piso.

        `ajusta_tamano` agranda la ventana hasta que el contenido entre y el
        piso se cumpla. El piso por omision (620x420) esta bien para las 40
        pantallas del menu, que se recortaban, pero se comia a los dialogos
        chicos: uno que pide 420x160 se abria de 620x420.

        Diez dialogos caian en eso. El que mas duele es el de cantidad y
        precio: pide 420x160 y recibia 620x420, o sea casi el triple de alto
        para dos campos.

        Con esto el dialogo dice su tamano UNA sola vez y el piso queda en ese
        numero, en vez de estar escrito dos veces y desincronizado.

        El contenido sigue mandando por encima del piso, porque
        `minimumSizeHint` se aplica igual en `ajusta_tamano`: declarar un
        tamano chico nunca termina con algo cortado.

        Solo affecta al piso de los dialogos SIN grilla. Con grilla manda
        `ANCHO_MINIMO`/`ALTO_MINIMO` (900x560), que es el que arreglo las
        pantallas grandes y no se toca aca.
        """
        self.resize(ancho, alto)
        self.ANCHO_MINIMO_CHICO = ancho
        self.ALTO_MINIMO_CHICO = alto

    def ajusta_tamano(self):
        """Agranda la ventana hasta que el contenido entre y el piso se cumpla.

        Se usa `minimumSizeHint` y NO `sizeHint`. El minimo es lo que el layout
        NECESITA para no cortar nada; el sizeHint se infla con cualquier
        contenedor sin layout (una pestana vacia pide 640x480 de default y
        empuja la ventana a 2678 px, que no lo quiere nadie).
        """
        from PyQt5.QtWidgets import QApplication

        ancho_min, alto_min = self._piso_de_tamano()
        minimo = self.minimumSizeHint()

        ancho = max(self.width(), minimo.width(), ancho_min)
        alto = max(self.height(), minimo.height(), alto_min)

        # Nunca mas grande que la pantalla: un piso de 900 en una pantalla de
        # 800 deja la ventana colgando, que es peor que chica.
        pantalla = QApplication.primaryScreen()
        if pantalla is not None:
            area = pantalla.availableGeometry()
            ancho = min(ancho, int(area.width() * 0.92))
            alto = min(alto, int(area.height() * 0.92))

        if (ancho, alto) != (self.width(), self.height()):
            self.resize(ancho, alto)

    def showEvent(self, event):
        """Ajusta el tamano la primera vez que se muestra, y solo esa.

        En `__init__` todavia no se armo el contenido, asi que
        `minimumSizeHint` no dice nada. `showEvent` es el primer momento en que
        el layout esta armado de verdad.
        """
        QDialog.showEvent(self, event)
        if not getattr(self, "_ajustado", False):
            self._ajustado = True
            self.ajusta_tamano()

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
        # Antes, aca, se llamaba a `self.Center()` y se hacia un `print` en
        # cada movimiento del mouse. Dos cosas malas: la ventana se iba para
        # otro lado mientras el usuario la agranda con el borde (que es como
        # falla el gesto entero), y cada redimensionado escribia una linea en
        # la consola. El centrado va en `Center()`, que lo llama `exec_()`.
        QDialog.resizeEvent(self, QResizeEvent)

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
