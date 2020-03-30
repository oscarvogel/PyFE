# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Fechas import Fecha
from libs.Formulario import Formulario
from libs.Grillas import Grilla
from libs.Utiles import imagen
from modelos import Clientes


class ReImprimeFacturaView(Formulario):

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Re impresion de facturas")
        self.verticalLayoutDatos = QVBoxLayout(Form)

        self.lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        self.verticalLayoutDatos.addWidget(self.lblTitulo)
        self.layoutCliente = self.ArmaEntrada('cliente',control=Clientes.Valida())
        self.lblNombreCliente = Etiqueta()
        self.controles['cliente'].widgetNombre = self.lblNombreCliente
        self.layoutCliente.addWidget(self.lblNombreCliente)
        self.ArmaEntrada(boxlayout=self.layoutCliente,nombre='fecha', control=Fecha())
        self.controles['fecha'].setFecha(-30)
        self.gridDatos = Grilla()
        self.gridDatos.enabled = True
        cabeceras = [
            'Fecha', 'Comprobante', 'Total', 'idcabecera'
        ]
        self.verticalLayoutDatos.addWidget(self.gridDatos)
        self.gridDatos.ArmaCabeceras(cabeceras=cabeceras)
        self.layoutBotones = QHBoxLayout()
        self.btnImprimir = Boton(texto="Imprimir", imagen=imagen('print.png'))
        self.btnCargar = Boton(texto="Cargar", imagen=imagen("if_SEO_usability_audit_search__969250.png"))
        self.envioCorreo = Boton(texto="Enviar por correo", imagen=imagen('email.png'))
        self.btnCerrar = BotonCerrarFormulario()
        self.layoutBotones.addWidget(self.btnCargar)
        self.layoutBotones.addWidget(self.btnImprimir)
        self.layoutBotones.addWidget(self.envioCorreo)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.verticalLayoutDatos.addLayout(self.layoutBotones)
