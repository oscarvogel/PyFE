#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""
Módulo para envio de correo electronico
Se utiliza para poder tomar los correos, sean de clientes o proveedores, y validarlos
Tambien en caso de querer enviar un email con algun mensaje o adjunto se puede utilizar este componente
"""

__author__ = "Jose Oscar Vogel (oscarvogel@gmail.com)"
__copyright__ = "Copyright (C) 2017-2020 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.10"

from PyQt5.QtWidgets import QVBoxLayout, QGridLayout, QHBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.Checkbox import CheckBox
from libs.EntradaTexto import EntradaTexto, TextoEnriquecido, EmailCompleter
from libs.Etiquetas import Etiqueta
from libs.Grillas import Grilla
from libs.Listas import Lista
from libs.Utiles import imagen
from vistas.VistaBase import VistaBase


class EnvioEmailView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Envio de correo electronico")

        layoutPpal = QVBoxLayout(Form)

        layoutParam = QGridLayout()
        self.btnPara = Boton(texto="Para:")
        self.textPara = EmailCompleter(placeholderText="Para")
        layoutParam.addWidget(self.btnPara, 0,0)
        layoutParam.addWidget(self.textPara, 0, 1)

        self.btnCC = Boton(texto="CC:")
        self.textCC = EmailCompleter(placeholderText="Con copia")
        layoutParam.addWidget(self.btnCC, 1, 0)
        layoutParam.addWidget(self.textCC, 1, 1)

        self.btnCCO = Boton(texto="CCO:")
        self.textCCO = EmailCompleter(placeholderText="Con copia oculta")
        layoutParam.addWidget(self.btnCCO, 2, 0)
        layoutParam.addWidget(self.textCCO, 2, 1)

        self.btnAdjunto = Boton(texto="Adjunto:")
        self.textAdjunto = EntradaTexto(enabled=False)
        layoutParam.addWidget(self.btnAdjunto, 3, 0)
        layoutParam.addWidget(self.textAdjunto, 3, 1)

        lblAsunto = Etiqueta(texto="Asunto")
        self.textAsunto = EntradaTexto(placeholderText="Asunto")
        layoutParam.addWidget(lblAsunto, 4, 0)
        layoutParam.addWidget(self.textAsunto, 4, 1, 1, 2)
        layoutPpal.addLayout(layoutParam)

        self.listaAdjuntos = Lista()
        layoutParam.addWidget(self.listaAdjuntos, 0, 2, 4, 1)

        self.textMensaje = TextoEnriquecido()
        layoutPpal.addWidget(self.textMensaje)

        layoutBotones = QHBoxLayout()
        self.btnEnviar = Boton(texto="Enviar", imagen=imagen("email.png"))
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnEnviar)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)

class ListaCorreosView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Seleccion de correos electronico")
        self.resize(650, 350)
        layoutPpal = QVBoxLayout(self)

        layoutBusqueda = QHBoxLayout()
        lblBusqueda = Etiqueta(texto="Busqueda")
        self.textBusqueda = EntradaTexto(placeholderText="Busqueda")
        self.checkTodos = CheckBox(texto="Todos?")
        layoutBusqueda.addWidget(lblBusqueda)
        layoutBusqueda.addWidget(self.textBusqueda)
        layoutBusqueda.addWidget(self.checkTodos)
        layoutPpal.addLayout(layoutBusqueda)

        self.gridCorreos = Grilla()
        self.gridCorreos.enabled = True
        cabeceras = [
            'Selecciona', 'Nombre', 'Correo'
        ]
        self.gridCorreos.columnasHabilitadas = [0,]
        self.gridCorreos.ArmaCabeceras(cabeceras)
        layoutPpal.addWidget(self.gridCorreos)

        layoutBotones = QHBoxLayout()
        self.btnSeleccionar = Boton(texto="&Selecciona", imagen=imagen("check.png"))
        self.btnAgregar = Boton(texto="&Agregar correo", imagen=imagen("email.png"))
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnSeleccionar)
        layoutBotones.addWidget(self.btnAgregar)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)