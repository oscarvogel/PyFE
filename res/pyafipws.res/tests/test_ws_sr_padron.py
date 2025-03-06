#!/usr/bin/python
# -*- coding: utf8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Test para Módulo WS_SR_PADRON
(Módulo para acceder a los datos de un contribuyente registrado en el Padrón
de AFIP).
"""

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2010-2019 Mariano Reingart"
__license__ = "GPL 3.0"

import os, sys
import pytest

from pyafipws.wsaa import WSAA
from pyafipws.ws_sr_padron import WSSrPadronA4, WSSrPadronA5, main


__WSDL__ = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5?wsdl"
__obj__ = WSSrPadronA5()
__service__ = "ws_sr_padron_a5"

CUIT = os.environ["CUIT"]
CERT = "reingart.crt"
PKEY = "reingart.key"
CACHE = ""

pytestmark =pytest.mark.vcr




@pytest.mark.xfail
def test_server_status(auth):
    """Test de estado de servidores."""
    # Estados de servidores respuesta no funciona afip
    wspa5=auth
    wspa5.Dummy()
    assert wspa5.AppServerStatus == "OK"
    assert wspa5.DbServerStatus == "OK"
    assert wspa5.AuthServerStatus == "OK"


def test_inicializar(auth):
    """Test inicializar variables de BaseWS."""
    wspa5=auth
    wspa5.inicializar()
    assert wspa5.tipo_doc == 0
    assert wspa5.denominacion == ""
    assert wspa5.actividades == []



def test_consultar(auth):
    """Test consultar."""
    wspa5=auth
    # Consulta Nivel A4 afip no esta funcionando.
    id_persona = "20201797064"
    consulta = wspa5.Consultar(id_persona)
    assert consulta == False


def test_consultar_a5(auth):
    """Test consultar padron nivel A5."""
    wspa5=auth
    id_persona = "20201797064"
    consulta = wspa5.Consultar(id_persona)

    assert wspa5.direccion == "LARREA 1"
    assert wspa5.provincia == "CIUDAD AUTONOMA BUENOS AIRES"
    assert wspa5.cod_postal == "1030"

    # metodo analizar datos
    assert wspa5.imp_iva == "S"
    assert wspa5.cat_iva == 1


def test_main(auth):
    sys.argv = []
    sys.argv.append("--debug")
    sys.argv.append("--constancia")
    sys.argv.append('--prueba')
    padron = main()
    assert padron.denominacion == "ERNESTO DANIEL, MARCELO NICOLAS"
    assert padron.tipo_doc == 80
    assert padron.tipo_persona == "FISICA"
    assert padron.nro_doc == 20000000516
    assert padron.estado == "ACTIVO"
    assert padron.localidad == "JUNIN DE LOS ANDES"
    assert padron.cod_postal == "8371"


def test_main_csv(auth):
    sys.argv = []
    sys.argv.append("")
    sys.argv.append("20000000516")
    sys.argv.append("--constancia")
    sys.argv.append("--csv")
    main()
    assert os.path.isfile("salida.csv")
