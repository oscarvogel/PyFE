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

#Controlador para generar, cargar y grabar la firma para el correo electronico que se envia desde el sistema

from controladores.ControladorBase import ControladorBase
from libs.Utiles import GuardarArchivo, LeerIni, openFileNameDialog
from modelos.ParametrosSistema import ParamSist
from vistas.FirmaCorreoElectronico import FirmaCorreoElectronicoView


class FirmaCorreoElectronicoController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = FirmaCorreoElectronicoView()
        self.conectarWidgets()
        self.CargaDatos()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnGrabar.clicked.connect(self.onClickBtnGrabar)
        self.view.btnCargar.clicked.connect(self.onClickBtnCargar)

    def CargaDatos(self):
        archivo_firma = ParamSist.ObtenerParametro("ARCHIVO_FIRMA_EMAIL")
        if archivo_firma:
            self.view.editorFirma.file_open(archivo_firma)

    def onClickBtnGrabar(self):
        archivo = GuardarArchivo(filter="HTML documents (*.html)")

        self.view.editorFirma.file_save(archivo)
        ParamSist.GuardarParametro("ARCHIVO_FIRMA_EMAIL", archivo)

    def onClickBtnCargar(self):
        archivo = openFileNameDialog(filename=ParamSist.ObtenerParametro("ARCHIVO_FIRMA_EMAIL"),
                                     files="HTML documents (*.html)")
        if archivo:
            self.view.editorFirma.file_open(archivo)