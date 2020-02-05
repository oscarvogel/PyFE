# coding=utf-8
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

#Vista para Exporta libro iva compras en formato excel
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.BarraProgreso import Avance
from libs.Botones import Boton, BotonCerrarFormulario
from libs.Etiquetas import EtiquetaTitulo
from libs.Formulario import Formulario
from libs.Spinner import Periodo


class IVAComprasView(Formulario):

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Exportacion IVA Compras")
        layoutPpal = QVBoxLayout(Form)
        lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        layoutPpal.addWidget(lblTitulo)

        self.avance = Avance()
        self.avance.setVisible(False)
        layoutPpal.addWidget(self.avance)

        self.periodo = Periodo(texto='Periodo a exportar')
        layoutPpal.addLayout(self.periodo)

        layoutBotones = QHBoxLayout()
        self.btnExcel = Boton(texto="Exportar", imagen='imagenes/excel.png')
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnExcel)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)