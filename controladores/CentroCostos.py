# coding=utf-8
from controladores.ControladorBase import ControladorBase
from vistas.CentroCostos import CentroCostosView


class CentroCostoController(ControladorBase):

    def __init__(self):
        super(CentroCostoController, self).__init__()
        self.view = CentroCostosView()
        #self.view.exec_()
        self.conectarWidgets()