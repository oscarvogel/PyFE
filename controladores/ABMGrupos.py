# coding=utf-8
from controladores.ControladorBase import ControladorBase
from vistas.ABMGrupos import ABMGruposView


class ABMGruposController(ControladorBase):

    def __init__(self):
        super(ABMGruposController, self).__init__()
        self.view = ABMGruposView()
        #self.view.exec_()
        self.conectarWidgets()