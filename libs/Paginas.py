# coding=utf-8
from PyQt4.QtGui import QTabWidget, QWidget


class Pagina(QTabWidget):

    def __init__(self, *args, **kwargs):
        QTabWidget.__init__(self)

class TabPagina(QWidget):

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self)