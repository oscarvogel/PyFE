# coding=utf-8
from controladores.ControladorBase import ControladorBase
from vistas.Articulos import ArticulosView


class ArticulosController(ControladorBase):

    def __init__(self):
        super(ArticulosController, self).__init__()
        self.view = ArticulosView()
        #self.view.exec_()