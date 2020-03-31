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

#Vista para Exporta ventas por grupos a Excel
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.BarraProgreso import Avance
from libs.Botones import Boton, BotonCerrarFormulario
from libs.Etiquetas import Etiqueta
from libs.Fechas import Fecha
from libs.Formulario import Formulario
from libs.Utiles import imagen


class InformeVentasPorGrupoView(Formulario):

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Informe de ventas por grupo")
        layoutPpal = QVBoxLayout(Form)

        layoutFecha = QHBoxLayout()
        lblDesdeFecha = Etiqueta(texto="Desde fecha")
        self.textDesdeFecha = Fecha()
        self.textDesdeFecha.setFecha(-30)
        lblHastaFecha = Etiqueta(texto="Hasta fecha")
        self.textHastaFecha = Fecha()
        self.textHastaFecha.setFecha()
        layoutFecha.addWidget(lblDesdeFecha)
        layoutFecha.addWidget(self.textDesdeFecha)
        layoutFecha.addWidget(lblHastaFecha)
        layoutFecha.addWidget(self.textHastaFecha)

        layoutPpal.addLayout(layoutFecha)

        self.avance = Avance()
        self.avance.setVisible(False)
        layoutPpal.addWidget(self.avance)

        layoutBotones = QHBoxLayout()
        self.btnExcel = Boton(texto="Exporta", imagen=imagen("excel.png"))
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnExcel)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)