# coding=utf-8
from controladores.ControladorBase import ControladorBase
from vistas.Proveedores import ProveedoresView


class ProveedoresController(ControladorBase):

    def __init__(self):
        super(ProveedoresController, self).__init__()
        self.view = ProveedoresView()
        #self.view.exec_()
        self.conectarWidgets()
