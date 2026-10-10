# coding=utf-8
from controladores.ControladorBase import ControladorBase
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.CuotasPago import CuotaPago
from vistas.ABMCuotasPago import ABMCuotasPagoView


class ABMCuotasPagoController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = ABMCuotasPagoView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnAceptar.clicked.connect(self.onClickBtnAceptar)

    @inicializar_y_capturar_excepciones
    def onClickBtnAceptar(self, *args, **kwargs):
        if self.view.tipo == 'M':
            cuota = CuotaPago.get_by_id(
                self.view.controles[CuotaPago.idcuota.column_name].text())
        else:
            cuota = CuotaPago()

        cuota.formapago = self.view.controles['formapago'].text()
        cuota.cuotas = int(self.view.controles[
            CuotaPago.cuotas.column_name].value())
        cuota.recargo = self.view.controles[
            CuotaPago.recargo.column_name].value()
        cuota.save()
        self.view.btnAceptarClicked()
