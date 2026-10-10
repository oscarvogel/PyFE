# coding=utf-8
from controladores.ControladorBase import ControladorBase
from libs import Ventanas
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.Formaspago import Formapago
from vistas.ABMFormasPago import ABMFormasPagoView


class ABMFormasPagoController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = ABMFormasPagoView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnAceptar.clicked.connect(self.onClickBtnAceptar)
        self.view.btnCuotas.clicked.connect(self.abrir_cuotas)

    def _forma_actual(self):
        """Id de la forma sobre la que se esta parado, o None.

        Primero la del detalle en edicion, despues la fila seleccionada
        de la lista. Es lo que filtra la relacion de tarjetas al abrirla.
        """
        try:
            if self.view.tabDetalle.isEnabled():
                texto = self.view.controles[
                    Formapago.idformapago.column_name].text().strip()
                if texto:
                    return int(texto)
        except Exception:
            pass
        try:
            fila = self.view.tableView.currentRow()
            if fila >= 0:
                return int(self.view.tableView.ObtenerItem(
                    fila=fila, col='Idformapago'))
        except Exception:
            pass
        return None

    @inicializar_y_capturar_excepciones
    def abrir_cuotas(self, *args, **kwargs):
        """Abre las cuotas de la forma actual: una grilla y nada mas.

        Como la ficha desde clientes: se edita la tarjeta y sus planes en
        un dialogo ya parado donde corresponde, y al volver se refresca
        la lista, que puede haber cambiado del otro lado (nombre, %).
        """
        from PyQt5.QtWidgets import QDialog
        from vistas.CuotasTarjeta import CuotasTarjetaDialog
        forma_id = self._forma_actual()
        if not forma_id:
            Ventanas.showAlert("Formas de pago",
                               "Elegi una forma de pago para ver sus cuotas.")
            return
        dialogo = CuotasTarjetaDialog(forma_id)
        if dialogo.exec_() == QDialog.Accepted:
            self.view.ArmaTabla()

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

        # Los planes se editan en el dialogo de cuotas, no aca: se validan
        # ahi antes de guardar. Aca solo va la tarjeta.
        forma.save()
        self.view.btnAceptarClicked()
