# coding=utf-8
from controladores.ControladorBase import ControladorBase
from vistas.Ctacte import CtaCteView


class CtaCteController(ControladorBase):

    def __init__(self):
        super(CtaCteController, self).__init__()
        self.view = CtaCteView()