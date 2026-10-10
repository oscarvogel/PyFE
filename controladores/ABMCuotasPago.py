# coding=utf-8
from controladores.ControladorBaseABM import ControladorBaseABM
from modelos.CuotasPago import CuotaPago
from vistas.ABMCuotasPago import ABMCuotasPagoView


class ABMCuotasPagoController(ControladorBaseABM):

    model = CuotaPago
    campoclave = CuotaPago.idcuota.name
    vistaClase = ABMCuotasPagoView

    def __init__(self):
        super().__init__()
        self.conectarWidgets()
