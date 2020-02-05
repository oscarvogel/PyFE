# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Fechas import Fecha
from libs.Grillas import Grilla
from libs.Utiles import imagen
from modelos import Clientes
from vistas.VistaBase import VistaBase

class EmiteReciboView(VistaBase):

    def __init__(self, *args, **kwargs):
        VistaBase.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Emision de recibos de cta cte")
        self.resize(750, 550)
        self.verticalLayoutDatos = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        self.verticalLayoutDatos.addWidget(self.lblTitulo)

        self.layoutCliente = self.ArmaEntrada(nombre='cliente', control=Clientes.Valida())
        self.lblNombreCliente = Etiqueta()
        self.controles['cliente'].widgetNombre = self.lblNombreCliente
        self.layoutCliente.addWidget(self.lblNombreCliente)
        self.ArmaEntrada(nombre='fecha', control=Fecha(enabled=False), boxlayout=self.layoutCliente)
        self.controles['fecha'].setFecha()

        self.gridDeuda = Grilla()
        self.gridDeuda.enabled = True
        cabecera = [
            'Tipo Comprobante', 'Comprobante', 'Fecha', 'Saldo', 'a Saldar', 'id'
        ]
        self.gridDeuda.columnasHabilitadas = [4,]
        self.gridDeuda.ArmaCabeceras(cabeceras=cabecera)
        self.verticalLayoutDatos.addWidget(self.gridDeuda)
        self.layoutDeudas = self.ArmaEntrada('deuda', enabled=False)
        self.ArmaEntrada(boxlayout=self.layoutDeudas, nombre='saldo', enabled=False)

        self.gridPagos = Grilla()
        self.gridPagos.columnasHabilitadas = [0, 1, 2, 3, 4, 5, 6]
        self.gridPagos.enabled = True
        cabecera = [
            'TipoComp', 'Importe', 'Banco', 'Sucursal', 'Numero', 'Vence', 'CUIT', 'id'
        ]
        self.gridPagos.ArmaCabeceras(cabeceras=cabecera)
        self.gridPagos.columnasOcultas = [7,]
        self.gridPagos.OcultaColumnas()
        self.verticalLayoutDatos.addWidget(self.gridPagos)

        self.layoutPagos = self.ArmaEntrada('pagos', enabled=False)
        self.layoutBotones = QHBoxLayout()
        self.btnGraba = Boton(texto='Aceptar', imagen=imagen('Accept.png'), autodefault=False)
        self.btnCerra = BotonCerrarFormulario(autodefault=False)
        self.btnAgrega = Boton(texto='Agrega Pago', imagen=imagen('Add_create_new.png'), autodefault=False)
        self.layoutBotones.addWidget(self.btnAgrega)
        self.layoutBotones.addWidget(self.btnGraba)
        self.layoutBotones.addWidget(self.btnCerra)
        self.verticalLayoutDatos.addLayout(self.layoutBotones)

