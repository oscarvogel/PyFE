# coding=utf-8
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.EntradaTexto import EntradaTexto
from libs.Formulario import Formulario
from libs.Grillas import Grilla


class FacturaCodBarraView(Formulario):

    def __init__(self):
        Formulario.__init__(self)
        self.setupUi(self)

    def setupUi(self, Form):
        self.layoutPpal = QVBoxLayout(Form)
        self.setWindowTitle("Emision de factura")
        self.resize(650,750)

        layoutProd = QHBoxLayout()
        self.gridArticulos = Grilla()
        self.gridArticulos.enabled = True
        cabeceras = [
            'Cant', 'UN', 'Detalle', 'Unitario', 'Total', 'idArticulo'
        ]
        self.gridArticulos.ArmaCabeceras(cabeceras)
        layoutProd.addWidget(self.gridArticulos)

        self.layoutPpal.addLayout(layoutProd)

        layoutTotales = QHBoxLayout()
        self.textCodBarra = EntradaTexto(tamanio=15, placeholderText='Codigo de barra')
        layoutTotales.addWidget(self.textCodBarra)
        self.textTotal = EntradaTexto(tamanio=15, enabled=False)
        layoutTotales.addWidget(self.textTotal)
        self.layoutPpal.addLayout(layoutTotales)
        self.textCodBarra.setFocus()