# coding=utf-8
from PyQt5 import QtCore
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel


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
        self.setStyleSheet("* {color: qlineargradient(spread:pad, x1:0 y1:0, x2:1 y2:0, stop:0 rgba(0, 0, 0, 255), "
                            "stop:1 rgba(255, 255, 255, 255));"
                            "background: qlineargradient( x1:0 y1:0, x2:1 y2:0, stop:0 blue, stop:1 cyan);}")