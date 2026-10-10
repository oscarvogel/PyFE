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
        """Abre la relacion de tarjetas, filtrada por la forma actual.

        Como la ficha desde clientes: se abre el otro ABM ya parado donde
        corresponde, y al volver se refresca la lista y los planes
        embebidos, que pueden haber cambiado del otro lado.
        """
        from controladores.ABMCuotasPago import ABMCuotasPagoController
        forma_id = self._forma_actual()
        cuotas = ABMCuotasPagoController()
        if forma_id:
            cuotas.view.forma_fija = forma_id
            cuotas.view.ArmaTabla()
        cuotas.exec_()
        self.view.ArmaTabla()
        try:
            if (self.view.tipo == 'M' and forma_id
                    and int(self.view.controles[
                        Formapago.idformapago.column_name].text()) == int(forma_id)):
                self.view.cargar_planes(forma_id)
        except Exception:
            pass

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
