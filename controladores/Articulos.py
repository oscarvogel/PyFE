# coding=utf-8
from controladores.ControladorBase import ControladorBase
from controladores.FE import FEv1
from libs import Ventanas
from libs.Utiles import LeerIni
from vistas.Articulos import ArticulosView


class ArticulosController(ControladorBase):

    def __init__(self):
        super(ArticulosController, self).__init__()
        self.view = ArticulosView()
        self.conectarWidgets()
        #self.view.exec_()

    # def conectarWidgets(self):
    #     self.view.controles['concepto'].editingFinished.connect(self.SeleccionaConcepto)

    def SeleccionaConcepto(self):
        if self.view.controles['concepto'].text() not in [str(FEv1.SERVICIOS),
                                                          str(FEv1.PRODUCTOYSERVICIOS),
                                                          str(FEv1.PRODUCTOS)]:
            Ventanas.showAlert(LeerIni('nombre_sistema'), 'Concepto no valido. Unicamente 1 (Productos), 2 (Servicios)')