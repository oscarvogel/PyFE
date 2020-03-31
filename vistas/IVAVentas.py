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

#Vista para Exporta libro iva ventas en formato excel
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from libs.BarraProgreso import Avance
from libs.Botones import Boton, BotonCerrarFormulario
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Fechas import Fecha
from libs.Formulario import Formulario
from libs.Utiles import imagen, InicioMes, FinMes


class IVAVentasView(Formulario):

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self, *args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Libro IVA Ventas")
        self.verticalLayoutDatos = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto=self.windowTitle())
        self.verticalLayoutDatos.addWidget(self.lblTitulo)
        self.avance = Avance()
        self.avance.setVisible(False)
        self.verticalLayoutDatos.addWidget(self.avance)

        self.layoutPtoVta = self.ArmaEntrada('desdeptovta', texto="Desde punto de venta")
        self.ArmaEntrada('hastaptovta', texto="Hasta punto de venta", boxlayout=self.layoutPtoVta)
        self.controles['desdeptovta'].setInputMask("9999")
        self.controles['hastaptovta'].setInputMask("9999")
        self.controles['desdeptovta'].setText("0000")
        self.controles['hastaptovta'].setText("9999")
        self.layoutFechas = QHBoxLayout()
        self.lblDesdeFecha = Etiqueta(texto="Desde fecha")
        self.lineDesdeFecha = Fecha()
        self.lineDesdeFecha.setFecha(InicioMes())
        self.lblHastaFecha = Etiqueta(texto="Hasta fecha")
        self.lineHastaFecha = Fecha()
        self.lineHastaFecha.setFecha(FinMes())
        self.layoutFechas.addWidget(self.lblDesdeFecha)
        self.layoutFechas.addWidget(self.lineDesdeFecha)
        self.layoutFechas.addWidget(self.lblHastaFecha)
        self.layoutFechas.addWidget(self.lineHastaFecha)
        self.verticalLayoutDatos.addLayout(self.layoutFechas)

        self.layoutBotones = QHBoxLayout()
        self.btnExcel = Boton(texto="Excel", imagen=imagen('excel.png'))
        self.btnEnviaCorreo = Boton(texto="Envia correo", imagen=imagen('email.png'))
        self.btnCerrar = BotonCerrarFormulario()
        self.layoutBotones.addWidget(self.btnExcel)
        self.layoutBotones.addWidget(self.btnEnviaCorreo)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.verticalLayoutDatos.addLayout(self.layoutBotones)
