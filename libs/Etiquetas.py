# coding=utf-8
from PyQt5 import QtCore
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel, QSizePolicy


class Etiqueta(QLabel):

    def __init__(self, parent=None, texto='', *args, **kwargs):
        QLabel.__init__(self, *args)
        self.setText(texto)
        font = QFont()
        if 'tamanio' in kwargs:
            font.setPointSizeF(kwargs['tamanio'])
        else:
            font.setPointSizeF(12)

        if 'alineacion' in kwargs:
            if kwargs['alineacion'].upper() == 'DERECHA':
                self.setAlignment(QtCore.Qt.AlignRight)
            elif kwargs['alineacion'].upper() == 'IZQUIERDA':
                self.setAlignment(QtCore.Qt.AlignLeft)
            elif kwargs['alineacion'].upper() == 'CENTRO':
                self.setAlignment(QtCore.Qt.AlignCenter)

        self.setFont(font)

class EtiquetaTitulo(Etiqueta):

    def __init__(self, parent=None, texto='', *args, **kwargs):
        Etiqueta.__init__(self, parent, texto, *args, **kwargs)
        # Antes llevaba un degradado azul->cian en cada pantalla. Era el
        # recurso que hace que la app se lea como algo de la era Windows Vista.
        # Ahora la jerarquia la pone el tema (temas/pyfe.css) a traves del
        # objectName: mismo resultado en todas las pantallas y sin que cada
        # titulo lleve su propio color pegado.
        self.setObjectName("tituloPantalla")

        # Un titulo es UNA linea y no crece nunca. Sin esto su politica
        # vertical es Expanding y el QVBoxLayout le pasa todo el sobrante:
        # medido, en el dialogo de "Cantidad y precio" ocupaba 307 px de alto
        # para 20 px de texto, y el nombre del producto quedaba flotando en
        # el medio de la ventana con los dos campos abajo de todo.
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

class EtiquetaRoja(Etiqueta):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("color: red;")