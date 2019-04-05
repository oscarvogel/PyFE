# coding=utf-8
from controladores.ControladorBase import ControladorBase
from vistas.RindeCAEAIndividual import RindeCAEAIndividualView


class RindeCAEAIndividualController(ControladorBase):

    def __init__(self):
        super(RindeCAEAIndividualController, self).__init__()
        self.view = RindeCAEAIndividualView()
        #self.view.exec_()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnConsultar.clicked.connect(self.RindeCAEA)

    def RindeCAEA(self):
        pass