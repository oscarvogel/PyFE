# coding=utf-8
from decimal import Decimal, InvalidOperation

from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout

from libs.Botones import Boton
from libs.Checkbox import CheckBox
from libs.Grillas import Grilla
from libs.Spinner import Spinner
from libs.Etiquetas import Etiqueta
from libs.Utiles import icono, inicializar_y_capturar_excepciones
from modelos.Formaspago import Formapago
from vistas.ABM import ABM


class ABMFormasPagoView(ABM):

    model = Formapago()
    camposAMostrar = [Formapago.idformapago, Formapago.detalle,
                      Formapago.descuento, Formapago.recargo,
                      Formapago.tarjeta]
    ordenBusqueda = Formapago.detalle
    campoClave = Formapago.idformapago

    def __init__(self, *args, **kwargs):
        self.forma_en_edicion = None
        ABM.__init__(self, *args, **kwargs)

    def BotonesAdicionales(self):
        # Va en la fila de botones de la lista, como "Ficha" en clientes:
        # abre la relacion de tarjetas (los planes de cuotas) sin salir.
        self.btnCuotas = Boton(texto='Cuotas', imagen=icono('documento'),
                               tooltip='Planes de cuotas de la forma de pago')
        self.btnCuotas.setObjectName("btnCuotas")
        self.horizontalLayout.addWidget(self.btnCuotas)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        self.layoutID = self.ArmaEntrada(Formapago.idformapago.column_name,
                                         texto='Codigo')
        self.ArmaEntrada(Formapago.detalle.column_name,
                         boxlayout=self.layoutID)
        lineaNum = self.ArmaEntrada(Formapago.descuento.column_name,
                                    texto='Descuento %',
                                    control=Spinner(decimales=2))
        self.ArmaEntrada(Formapago.recargo.column_name, texto='Recargo %',
                         control=Spinner(decimales=2), boxlayout=lineaNum)
        lineaFlags = self.ArmaEntrada(Formapago.ctacte.column_name,
                                      texto='Cta cte', control=CheckBox())
        self.ArmaEntrada(Formapago.tarjeta.column_name, texto='Tarjeta',
                         control=CheckBox(), boxlayout=lineaFlags)
        self.ArmaEntrada(Formapago.mensual.column_name, texto='Mensual',
                         control=CheckBox(), boxlayout=lineaFlags)
        self._arma_planes()
        try:
            self.controles[Formapago.tarjeta.column_name].toggled.connect(
                self._al_cambiar_tarjeta)
        except Exception:
            pass

    # -- Planes de cuotas embebidos --------------------------------------
    # Si la forma es tarjeta, sus planes se editan aca mismo: es donde el
    # operador esta parado cuando le pasan los % del banco, y obligarlo a
    # salir a otro ABM es como se terminan cargando en un papel al lado.

    def _arma_planes(self):
        caja = QVBoxLayout()
        caja.addWidget(Etiqueta(texto="Planes de cuotas de esta tarjeta"))
        self.gridPlanes = Grilla()
        self.gridPlanes.enabled = True
        self.gridPlanes.columnasHabilitadas = [0, 1]
        self.gridPlanes.ArmaCabeceras(cabeceras=['Cuotas', 'Recargo %'],
                                      formatos=['Entero', 'Moneda'])
        caja.addWidget(self.gridPlanes)
        fila = QHBoxLayout()
        self.btnAgregarPlan = Boton(texto='Agregar plan',
                                    imagen=icono('agregar'))
        self.btnQuitarPlan = Boton(texto='Quitar plan',
                                   imagen=icono('borrar'))
        fila.addWidget(self.btnAgregarPlan)
        fila.addWidget(self.btnQuitarPlan)
        caja.addLayout(fila)
        self.layoutPlanes = caja
        self.verticalLayoutDatos.addLayout(caja)
        self.btnAgregarPlan.clicked.connect(self._agregar_plan)
        self.btnQuitarPlan.clicked.connect(self._quitar_plan)
        self.layoutPlanesVisible(False)

    def _al_cambiar_tarjeta(self, *args):
        try:
            es = bool(self.controles[Formapago.tarjeta.column_name]
                      .isChecked())
        except Exception:
            es = False
        self.layoutPlanesVisible(es)

    def layoutPlanesVisible(self, visible):
        for i in range(self.layoutPlanes.count()):
            item = self.layoutPlanes.itemAt(i)
            widget = item.widget()
            layout = item.layout()
            if widget is not None:
                widget.setVisible(visible)
            if layout is not None:
                for j in range(layout.count()):
                    sub = layout.itemAt(j).widget()
                    if sub is not None:
                        sub.setVisible(visible)

    def _agregar_plan(self, *args):
        self.gridPlanes.AgregaItem(items=[1, Decimal("0")])

    def _quitar_plan(self, *args):
        fila = self.gridPlanes.currentRow()
        if fila >= 0:
            self.gridPlanes.removeRow(fila)

    def cargar_planes(self, forma_id):
        """Trae los planes de la forma a la grilla."""
        from modelos.CuotasPago import CuotaPago
        self.forma_en_edicion = forma_id
        self.gridPlanes.setRowCount(0)
        if not forma_id:
            return
        try:
            filas = (CuotaPago.select()
                     .where(CuotaPago.formapago == int(forma_id))
                     .order_by(CuotaPago.cuotas))
            for fila in filas:
                self.gridPlanes.AgregaItem(
                    items=[int(fila.cuotas), Decimal(str(fila.recargo))])
        except Exception:
            pass

    def planes_editados(self):
        """[(cuotas, recargo)] validados desde la grilla.

        Tira ValueError si una fila no es un plan valido: el controlador
        avisa y no guarda nada, para no hacer desaparecer lo escrito.
        """
        planes = {}
        for fila in range(self.gridPlanes.rowCount()):
            try:
                cuotas = int(Decimal(
                    str(self.gridPlanes.ObtenerItem(fila=fila, col=0))))
                recargo = Decimal(
                    str(self.gridPlanes.ObtenerItem(fila=fila, col=1)))
            except (InvalidOperation, ValueError, TypeError,
                    ArithmeticError):
                raise ValueError(
                    "La fila {} no es un plan valido: cuotas enteras y "
                    "recargo numerico.".format(fila + 1))
            if not 1 <= cuotas <= 99:
                raise ValueError(
                    "La fila {}: las cuotas van de 1 a 99.".format(fila + 1))
            if not Decimal("0") <= recargo <= Decimal("999"):
                raise ValueError(
                    "La fila {}: el recargo va de 0 a 999.".format(fila + 1))
            planes[cuotas] = recargo
        return sorted(planes.items())

    def PostAgrega(self):
        self.forma_en_edicion = None
        self.gridPlanes.setRowCount(0)
        self._al_cambiar_tarjeta()

    def PostModifica(self):
        try:
            forma_id = int(self.controles[
                Formapago.idformapago.column_name].text())
        except Exception:
            forma_id = None
        self.cargar_planes(forma_id)
        self._al_cambiar_tarjeta()
