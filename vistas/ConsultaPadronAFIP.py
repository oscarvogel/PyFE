# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Grillas import Grilla
from libs.Utiles import imagen
from vistas.VistaBase import VistaBase


class ConsultaPadronAFIPView(VistaBase):

    def __init__(self, *args, **kwargs):
        VistaBase.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Consulta padron de la afip")
        self.resize(650, 450)
        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        self.layoutPpal.addWidget(self.lblTitulo)

        self.layoutCUIT = QHBoxLayout()
        self.lblCUIT = Etiqueta(texto="CUIT")
        self.textCUIT = EntradaTexto(placeholderText="CUIT")
        self.textCUIT.setInputMask("99-99999999-99")
        self.layoutCUIT.addWidget(self.lblCUIT)
        self.layoutCUIT.addWidget(self.textCUIT)
        self.layoutPpal.addLayout(self.layoutCUIT)

        self.gridDatos = Grilla()
        self.gridDatos.enabled = True
        cabecera = [
            "Campo", "Valor"
        ]
        self.gridDatos.ArmaCabeceras(cabeceras=cabecera)
        self.layoutPpal.addWidget(self.gridDatos)

        self.layoutBotones = QHBoxLayout()
        self.btnConsulta = Boton(texto="Consulta", imagen=imagen("if_SEO_usability_audit_search__969250.png"))
        self.btnImprimir = Boton(texto="Imprimir Constancia", imagen=imagen("print.png"))
        self.btnCerrar = BotonCerrarFormulario()
        self.btnAgregaCliente = Boton(texto="Agrega Cliente", imagen=imagen('new.png'))
        self.layoutBotones.addWidget(self.btnConsulta)
        self.layoutBotones.addWidget(self.btnImprimir)
        self.layoutBotones.addWidget(self.btnAgregaCliente)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.layoutPpal.addLayout(self.layoutBotones)