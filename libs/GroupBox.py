# coding=utf-8
from PyQt5.QtWidgets import QGroupBox


class Agrupacion(QGroupBox):

    def __init__(self, parent=None, *args, **kwargs):
        QGroupBox.__init__(self, *args)
        if 'tamanio' in kwargs:
            self.setStyleSheet('font-size: ' + str(kwargs['tamanio']) + 'px;')
        else:
            self.setStyleSheet('font-size: 12px;')

        if 'titulo' in kwargs:
            self.setTitle(kwargs['titulo'])
