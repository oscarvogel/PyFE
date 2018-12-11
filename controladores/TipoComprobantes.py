# coding=utf-8
from controladores.ControladorBase import ControladorBase
from vistas.TipoComprobantes import TipoComprobantesView


class TipoComprobantesController(ControladorBase):

    def __init__(self):
        super(TipoComprobantesController, self).__init__()
        self.view = TipoComprobantesView()
        #self.view.exec_()
        self.conectarWidgets()