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

#consultar datos del padron de la afip online
from controladores.FE import FEv1
from libs.Utiles import LeerIni, inicializar_y_capturar_excepciones, AbrirArchivo
from pyafipws.padron import PadronAFIP
from pyafipws.ws_sr_padron import WSSrPadronA5

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2018 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"

class PadronAfip(WSSrPadronA5):
     
    @inicializar_y_capturar_excepciones
    def ConsultarPersona(self, cuit=''):
        self.HOMO = True if LeerIni(clave='homo') == 'S' else False

        wsfev1 = FEv1()
        ta = wsfev1.Autenticar(service='ws_sr_padron_a5')
        # ta = wsfev1.Autenticar(service='ws_sr_padron_a13')
        self.SetTicketAcceso(ta_string=ta)
        self.Cuit = LeerIni(clave='cuit', key='WSFEv1') #cuit de la empresa/persona

        if LeerIni(clave='homo') == 'N':
            self.WSDL = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5?wsdl"
            # self.WSDL = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13?wsdl"
            self.Conectar("", self.WSDL)
        else:
            self.Conectar()
        try:
            ok = self.Consultar(id_persona=cuit)
        except:
            ok = False
        # ok = self.Consultar(id_persona=23347203)
        return ok

    @inicializar_y_capturar_excepciones
    def DescargarConstancia(self, cuit='', filename='', *args, **kwargs):
        padron = PadronAFIP()
        if LeerIni(clave='homo') == 'S':
            padron.Conectar()
        ok = padron.DescargarConstancia(cuit, filename)
        filename = LeerIni("iniciosistema") + filename
        AbrirArchivo(filename)

