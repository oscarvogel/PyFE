# coding=utf-8
from controladores.ControladorBase import ControladorBase
from libs import Ventanas
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.CuotasPago import CuotaPago
from modelos.Formaspago import Formapago
from vistas.ABMFormasPago import ABMFormasPagoView


class ABMFormasPagoController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = ABMFormasPagoView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnAceptar.clicked.connect(self.onClickBtnAceptar)

    @inicializar_y_capturar_excepciones
    def onClickBtnAceptar(self, *args, **kwargs):
        if self.view.tipo == 'M':
            forma = Formapago.get_by_id(self.view.controles[
                Formapago.idformapago.column_name].text())
        else:
            forma = Formapago()

        forma.detalle = self.view.controles[
            Formapago.detalle.column_name].text()[:30]
        forma.descuento = self.view.controles[
            Formapago.descuento.column_name].value()
        forma.recargo = self.view.controles[
            Formapago.recargo.column_name].value()
        forma.ctacte = self.view.controles[
            Formapago.ctacte.column_name].isChecked()
        forma.tarjeta = self.view.controles[
            Formapago.tarjeta.column_name].isChecked()
        forma.mensual = self.view.controles[
            Formapago.mensual.column_name].isChecked()

        # Los planes se validan ANTES de guardar la forma: si la grilla
        # tiene una fila rota, se avisa y no se guarda nada, en vez de
        # guardar la forma y perder lo escrito en los planes.
        planes = []
        if forma.tarjeta:
            try:
                planes = self.view.planes_editados()
            except ValueError as e:
                Ventanas.showAlert("Formas de pago", str(e))
                return

        forma.save()
        self._grabar_planes(forma.idformapago, planes)
        self.view.btnAceptarClicked()

    @staticmethod
    def _grabar_planes(forma_id, planes):
        """Deja los planes de la forma exactamente como la grilla.

        Son pocas filas por tarjeta: se borran y se recrean, que es
        idempotente y no deja planes huerfanos de ediciones anteriores.
        """
        (CuotaPago.delete()
         .where(CuotaPago.formapago == forma_id)).execute()
        for cuotas, recargo in planes:
            CuotaPago.create(formapago=forma_id, cuotas=int(cuotas),
                             recargo=recargo)
