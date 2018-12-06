# coding=utf-8
from controladores.ControladorBase import ControladorBase
from vistas.Localidades import LocalidadesView


class LocalidadesController(ControladorBase):

    def __init__(self):
        super(LocalidadesController, self).__init__()
        self.view = LocalidadesView()
        #self.view.exec_()
        self.conectarWidgets()