# coding=utf-8
from controladores.ControladorBaseABM import ControladorBaseABM
from modelos.Formaspago import Formapago
from vistas.ABMFormasPago import ABMFormasPagoView


class ABMFormasPagoController(ControladorBaseABM):

    model = Formapago
    campoclave = Formapago.idformapago.name
    vistaClase = ABMFormasPagoView

    def __init__(self):
        super().__init__()
        self.conectarWidgets()
