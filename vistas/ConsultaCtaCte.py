# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Fechas import Fecha
from libs.Grillas import Grilla
from modelos import Clientes
from vistas.VistaBase import VistaBase


class ConsultaCtaCteView(VistaBase):

    def __init__(self, *args, **kwargs):
        VistaBase.__init__(self, *args, **kwargs)
        self.initUi()

    def initUi(self):
        self.setWindowTitle("Resumen cuenta corriente cliente")
        self.layoutPpal = QVBoxLayout(self)
        self.lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        self.layoutPpal.addWidget(self.lblTitulo)

        self.layoutCliente = QHBoxLayout()
        self.lblCodigoCliente = Etiqueta(texto="Codigo")
        self.lineEditCliente = Clientes.Valida()
        self.lblNombreCliente = Etiqueta()
        self.lineEditCliente.widgetNombre = self.lblNombreCliente
        self.layoutCliente.addWidget(self.lblCodigoCliente)
        self.layoutCliente.addWidget(self.lineEditCliente)
        self.layoutCliente.addWidget(self.lblNombreCliente)
        self.layoutPpal.addLayout(self.layoutCliente)

        self.lblDesdeFecha = Etiqueta(texto="Desde Fecha")
        self.desdeFecha = Fecha()
        self.desdeFecha.setFecha(-30)
        self.lblHastaFecha = Etiqueta(texto="Hasta Fecha")
        self.hastaFecha = Fecha()
        self.hastaFecha.setFecha()
        self.layoutCliente.addWidget(self.lblDesdeFecha)
        self.layoutCliente.addWidget(self.desdeFecha)
        self.layoutCliente.addWidget(self.lblHastaFecha)
        self.layoutCliente.addWidget(self.hastaFecha)

        self.gridDatos = Grilla()
        self.gridDatos.enabled = True
        self.gridDatos.ArmaCabeceras(cabeceras=[
            'Cond Vta', 'Tipo', 'Numero', 'Fecha', 'Debe', 'Haber', 'Saldo'
        ])
        self.layoutPpal.addWidget(self.gridDatos)

        self.layoutBotones= QHBoxLayout()
        self.btnMostrar = Boton(texto="&Mostrar", imagen='imagenes/buscar.png')
        self.btnExcel = Boton(texto="&Exportar", imagen='imagenes/excel.png')
        self.btnCerrar = BotonCerrarFormulario()
        self.layoutBotones.addWidget(self.btnMostrar)
        self.layoutBotones.addWidget(self.btnExcel)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.layoutPpal.addLayout(self.layoutBotones)

    def MostrarDeuda(self, data):
        self.gridDatos.setRowCount(0)
        for d in data:
            item = d
            self.gridDatos.AgregaItem(item)