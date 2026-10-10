# coding=utf-8
"""Cuotas de una tarjeta: una grilla y nada mas.

Por que un dialogo y no un ABM
------------------------------
Los planes de una tarjeta se miran y se tocan juntos: que % lleva cada
cantidad de cuotas y cual sigue vigente. Un ABM (buscar en lista, abrir
detalle, guardar, volver) es tres pasos para algo que es una sola tabla,
y por eso los % terminaban en un papel al lado en vez de cargados.

Aca esta todo lo de UNA tarjeta: sus datos (detalle, descuento y recargo
base) y sus planes (cuotas, recargo %, activa). Se abre desde Formas de
pago con la tarjeta ya elegida.
"""
from decimal import Decimal, InvalidOperation

from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout

from libs import Ventanas
from libs.Botones import Boton, botonera_dialogo
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import Etiqueta, EtiquetaTitulo
from libs.Formulario import Formulario
from libs.Grillas import Grilla
from libs.Spinner import Spinner
from libs.Utiles import icono


class CuotasTarjetaDialog(Formulario):

    def __init__(self, forma_id, parent=None):
        Formulario.__init__(self, parent)
        self.forma_id = forma_id
        self.setupUi(self)
        self.cargar()

    def setupUi(self, Form):
        from modelos.Formaspago import Formapago
        try:
            detalle = Formapago.get_by_id(int(self.forma_id)).detalle
        except Exception:
            detalle = ""
        self.setWindowTitle("Cuotas de {}".format(detalle or "la tarjeta"))
        self.declara_tamano(520, 420)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        self.layoutPpal.addWidget(self.lblTitulo)

        datos = QGridLayout()
        self.textDetalle = EntradaTexto()
        self.spinDescuento = Spinner(decimales=2)
        self.spinRecargo = Spinner(decimales=2)
        datos.addWidget(Etiqueta(texto="Tarjeta"), 0, 0)
        datos.addWidget(self.textDetalle, 0, 1)
        datos.addWidget(Etiqueta(texto="Descuento %"), 1, 0)
        datos.addWidget(self.spinDescuento, 1, 1)
        datos.addWidget(Etiqueta(texto="Recargo base %"), 2, 0)
        datos.addWidget(self.spinRecargo, 2, 1)
        self.layoutPpal.addLayout(datos)

        self.layoutPpal.addWidget(
            Etiqueta(texto="Planes: cuotas, recargo y si sigue vigente"))
        self.gridPlanes = Grilla()
        self.gridPlanes.enabled = True
        self.gridPlanes.columnasHabilitadas = [0, 1, 2]
        self.gridPlanes.ArmaCabeceras(cabeceras=['Cuotas', 'Recargo %',
                                                 'Activa'],
                                      formatos=['Entero', 'Moneda', 'Bool'])
        self.layoutPpal.addWidget(self.gridPlanes)

        fila = QHBoxLayout()
        self.btnAgregarPlan = Boton(texto='Agregar plan',
                                    imagen=icono('agregar'))
        self.btnQuitarPlan = Boton(texto='Quitar plan',
                                   imagen=icono('borrar'))
        fila.addWidget(self.btnAgregarPlan)
        fila.addWidget(self.btnQuitarPlan)
        self.layoutPpal.addLayout(fila)
        self.btnAgregarPlan.clicked.connect(self._agregar_plan)
        self.btnQuitarPlan.clicked.connect(self._quitar_plan)

        self.layoutPpal.addStretch(1)
        self.botones = botonera_dialogo()
        self.botones.accepted.connect(self.guardar)
        self.botones.rejected.connect(self.reject)
        self.layoutPpal.addWidget(self.botones)

    def _agregar_plan(self, *args):
        self.gridPlanes.AgregaItem(items=[1, Decimal("0"), True])

    def _quitar_plan(self, *args):
        fila = self.gridPlanes.currentRow()
        if fila >= 0:
            self.gridPlanes.removeRow(fila)

    def cargar(self):
        """Trae los datos de la tarjeta y sus planes a la pantalla."""
        from modelos.CuotasPago import CuotaPago
        from modelos.Formaspago import Formapago
        forma = Formapago.get_by_id(int(self.forma_id))
        self.textDetalle.setText(forma.detalle or "")
        self.spinDescuento.setValue(float(forma.descuento or 0))
        self.spinRecargo.setValue(float(forma.recargo or 0))
        self.gridPlanes.setRowCount(0)
        filas = (CuotaPago.select()
                 .where(CuotaPago.formapago == int(self.forma_id))
                 .order_by(CuotaPago.cuotas))
        for fila in filas:
            try:
                activa = bool(fila.activo)
            except Exception:
                activa = True
            self.gridPlanes.AgregaItem(
                items=[int(fila.cuotas), Decimal(str(fila.recargo)),
                       activa])

    def planes_editados(self):
        """[(cuotas, recargo, activa)] validados desde la grilla.

        Tira ValueError si una fila no es un plan valido: quien llama
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
            try:
                activa = bool(self.gridPlanes.ObtenerItemNumerico(fila=fila,
                                                                  col=2))
            except Exception:
                activa = True
            planes[cuotas] = (recargo, activa)
        return sorted(planes.items())

    def guardar(self, *args):
        """Valida, guarda tarjeta + planes y cierra con Accepted.

        Devuelve True si guardo. Conectado al boton de aceptar del dialogo,
        asi que tambien corre al dar Enter.
        """
        from modelos.CuotasPago import CuotaPago
        from modelos.Formaspago import Formapago
        detalle = (self.textDetalle.text() or "").strip()
        if not detalle:
            Ventanas.showAlert("Cuotas de la tarjeta",
                               "La tarjeta necesita un nombre.")
            return False
        try:
            planes = self.planes_editados()
        except ValueError as e:
            Ventanas.showAlert("Cuotas de la tarjeta", str(e))
            return False
        forma = Formapago.get_by_id(int(self.forma_id))
        forma.detalle = detalle[:30]
        forma.descuento = self.spinDescuento.value()
        forma.recargo = self.spinRecargo.value()
        forma.save()
        (CuotaPago.delete()
         .where(CuotaPago.formapago == int(self.forma_id))).execute()
        for cuotas, (recargo, activa) in planes:
            CuotaPago.create(formapago=int(self.forma_id), cuotas=int(cuotas),
                             recargo=recargo, activo=bool(activa))
        try:
            self.accept()
        except Exception:
            pass
        return True
