# coding=utf-8
from vistas.VistaBase import VistaBase

class ControladorBase(object):

    view = None #vista asociada
    model = None #modelo asociado
    LanzarExcepciones = False

    def __init__(self):
        self.view = VistaBase()

    def run(self):
        self.view.show()

    def conectarWidgets(self):
        pass

    def exec_(self):
        self.view.exec_()