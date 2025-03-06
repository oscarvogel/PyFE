#!/usr/bin/python
# -*- coding: utf8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.

"""Módulo para obtener Carta de Porte Electrónica
para transporte ferroviario y automotor RG 5017/2021
"""

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2021- Mariano Reingart"
__license__ = "LGPL 3.0"
__version__ = "1.06b"

LICENCIA = """
wscpe.py: Interfaz para generar Carta de Porte Electrónica AFIP v1.0.0
Resolución General 5017/2021
Copyright (C) 2021 Mariano Reingart reingart@gmail.com
http://www.sistemasagiles.com.ar/trac/wiki/CartadePorte

Este progarma es software libre, se entrega ABSOLUTAMENTE SIN GARANTIA
y es bienvenido a redistribuirlo bajo la licencia GPLv3.

Para información adicional sobre garantía, soporte técnico comercial
e incorporación/distribución en programas propietarios ver PyAfipWs:
http://www.sistemasagiles.com.ar/trac/wiki/PyAfipWs
"""

AYUDA="""
Opciones: 
  --ayuda: este mensaje

  --debug: modo depuración (detalla y confirma las operaciones)
  --prueba: genera y autoriza una rec de prueba (no usar en producción!)
  --xml: almacena los requerimientos y respuestas XML (depuración)
  --dummy: consulta estado de servidores

  --autorizar: autoriza un cpe

  --ult: consulta ultimo nro cpe emitido
  --consultar: consulta un cpe generado

  --anular: un CPE existente (usa cabecera)
  --informar_contingencia: (usa cabecera y contingencias)
  --cerrar_contingencia: (usa cabecera y contingencias)
  --rechazo: (usa cabecera)
  --confirmar_arribo: (usa cabecera)
  --descargado_destino: (usa cabecera)
  --confirmacion_definitiva: (usa cabecera, datos_carga)
  --nuevo_destino_destinatario: (usa cabecera, destino, transporte)
  --regreso_origen: (usa cabecera, transporte)
  --desvio: (usa cabecera, destino, transporte)

  --editar: modificar datos (cabecera: ctg, destino, datos_carga y transporte)

  --provincias: listado de provincias
  --localidades_por_provincia: listado de localidades para la provincia dada
  --localidades_por_productor: listado de localidades para el CUIT
  --tipos_granos': listado de granos
  --plantas: codigos de plantas habilitados para el cuit

Ver wscpe.ini para parámetros de configuración (URL, certificados, etc.)"
"""

import os, sys, time, base64, datetime
from pyafipws.utils import date
import traceback
from pysimplesoap.client import SoapFault
import pyafipws.utils

# importo funciones compartidas:
from pyafipws.utils import json, BaseWS, inicializar_y_capturar_excepciones, get_install_dir, json_serializer
from pyafipws.utils import leer_txt, grabar_txt, leer_dbf, guardar_dbf, N, A, B, I, json, BaseWS, inicializar_y_capturar_excepciones, get_install_dir

from pyafipws.wscpe import WSCPE, HOMO

# constantes de configuración (producción/homologación):

WSDL = ["https://serviciosjava.afip.gob.ar/cpe-ws/services/wscpe?wsdl",
        "https://fwshomo.afip.gov.ar/wscpe/services/soap?wsdl"]

DEBUG = False
XML = False
CONFIG_FILE = "wscpe.ini"

ENCABEZADO = [
    ('tipo_reg', 1, A), # 0: encabezado carta de porte

    ('tipo_cpe', 3, N),  # 74: CPE Automotor, 75: CPE Ferroviaria,  99: Flete Corto.
    
    ('sucursal', 5, N),
    ('nro_orden', 8, N),
    ('planta', 6, N),

    # desvio cpe automotor
    ('cuit_solicitante', 11, N),

    # confirmación definitiva
    ('peso_bruto_descarga', 10, N),
    ('peso_tara_descarga', 10, N),

    # resultado:
    ('nro_ctg', 12, N),
    ('fecha_emision', 25, A), # 2021-08-21T23:29:26
    ('fecha_inicio_estado', 25, A),
    ('estado', 15, A),
    ('fecha_vencimiento', 25, A), # 26/02/2013

    ('observaciones', 2000, A),
    ]

ORIGEN = [
    ('tipo_reg', 1, A), # O: Origen
    ('cod_provincia_operador', 2, N),
    ('cod_localidad_operador', 6, N), 
    ('planta', 6, N),
    ('cod_provincia_productor', 2, N),
    ('cod_localidad_productor', 6, N), 
    ]

INTERVINIENTES = [
    ('tipo_reg', 1, A), # I: Intervinientes
    ('cuit_remitente_comercial_venta_primaria', 11, N),
    ('cuit_remitente_comercial_venta_secundaria', 11, N),
    ('cuit_remitente_comercial_venta_secundaria2', 11, N),
    ('cuit_mercado_a_termino', 11, N),
    ('cuit_corredor_venta_primaria', 11, N),
    ('cuit_corredor_venta_secundaria', 11, N),
    ('cuit_representante_entregador', 11, N),
    ('cuit_representante_recibidor', 11, N),
    ]

RETIRO_PRODUCTOR = [
    ('tipo_reg', 1, A), # R: Retiro Productor
    ('corresponde_retiro_productor', 5, B),
    ('es_solicitante_campo', 5, B),
    ('certificado_coe', 12, N),
    ('cuit_remitente_comercial_productor', 11, N),
    ]

DATOS_CARGA = [
    ('tipo_reg', 1, A), # C
    ('cod_grano', 2, N),
    ('cosecha', 4, N),
    ('peso_bruto', 10, N),
    ('peso_tara', 10, N),
    ]

DESTINO = [
    ('tipo_reg', 1, A), # D
    ('cuit_destino', 11, N),
    ('es_destino_campo', 5, B),
    ('cod_provincia', 2, N),
    ('cod_localidad', 6, N),
    ('planta', 6, N),
    ('cuit_destinatario', 11, N),
    ]

TRANSPORTE = [
    ('tipo_reg', 1, A), # D
    ('cuit_transportista', 11, N),
    ('dominio', 10, A),
    ('fecha_hora_partida', 20, A),  # 2016-11-17T12:00:39
    ('km_recorrer', 5, N),
    ('codigo_turno', 30, A),
    ('cuit_chofer', 11, N),
    ('tarifa', 10, I, 2),  # 99999.99
    ('cuit_intermediario_flete', 11, N),
    ('cuit_pagador_flete', 11, N),
    ('mercaderia_fumigada', 5, B),
    ('tarifa_referencia', 10, I, 2),  # 99999.99
    ('cuit_transportista_tramo2', 11, N),
    ('nro_vagon', 8, N),  # 10000000 hasta 99999999
    ('nro_precinto', 20, A),
    ('nro_operativo', 10, N),
    ('codigo_ramal', 2, N),  # 1: Roca, 2: Sarmiento, 3: Mitre, 4: Urquiza, 5: Belgrano, 6: San Martín, 99: Otro
    ('descripcion_ramal', 50, A),
    ]

CONTINGENCIA = [
    ('tipo_reg', 1, A), # D
    ('concepto', 2, A),
    ('cuit_transportista', 11, N),
    ('nro_operativo', 11, N),
    ('concepto_desactivacion', 2, A),
    ('descripcion', 140, A),
]

EVENTO = [
    ('tipo_reg', 1, A), # E: Evento
    ('codigo', 4, A), 
    ('descripcion', 250, A), 
    ]
    
ERROR = [
    ('tipo_reg', 1, A), # R: Error
    ('codigo', 4, A), 
    ('descripcion', 250, A), 
    ]

FORMATOS = {
    'encabezado': ENCABEZADO,
    'origen': ORIGEN,
    'intervinientes': INTERVINIENTES,
    'retiro_productor': RETIRO_PRODUCTOR,
    'datos_carga': DATOS_CARGA,
    'destino': DESTINO,
    'transporte': TRANSPORTE,
    'contingencia': CONTINGENCIA,
    'errores': ERROR,
    'eventos': EVENTO,
}
TIPO_REGISTROS = {
    "0": 'encabezado',
    "O": 'origen',
    "I": 'intervinientes',
    "R": 'retiro_productor',
    "C": 'datos_carga',
    "D": 'destino',
    "T": 'transporte',
    "N": 'contingencia',
    "E": 'errores',
    "V": 'eventos',
}
TIPO_REGISTROS_REV = dict([(v, k) for (k, v) in TIPO_REGISTROS.items()])

def preparar_registros(dic, header='encabezado'):
    formatos = []
    for key, formato in FORMATOS.items():
        nombre = key
        tipo_reg = TIPO_REGISTROS_REV[key]
        if key != header:
            regs = dic.get(key, [])
        else:
            regs = dic
        if not isinstance(regs, list):
            regs = [regs]
        for reg in regs:
            try:
                reg["tipo_reg"] = tipo_reg
            except Exception as e:
                print(e)

        formatos.append((nombre, formato, regs))
    return formatos


def escribir_archivo(dic, nombre_archivo, agrega=True):
    if '--json' in sys.argv:
        with open(nombre_archivo, agrega and "a" or "w") as archivo:
            json.dump(dic, archivo, sort_keys=True, indent=4)
    elif '--dbf' in sys.argv:
        formatos = preparar_registros(dic)
        guardar_dbf(formatos, agrega, conf_dbf)
    else:
        grabar_txt(FORMATOS, TIPO_REGISTROS, nombre_archivo, [dic], agrega)


def leer_archivo(nombre_archivo):
    if '--json' in sys.argv:
        with open(nombre_archivo, "r") as archivo:
            dic = json.load(archivo)
    elif '--dbf' in sys.argv:
        dic = []
        formatos = preparar_registros(dic)
        leer_dbf(formatos, conf_dbf)
    else:
        dics = leer_txt(FORMATOS, TIPO_REGISTROS, nombre_archivo)
        dic = dics[0]
    if DEBUG:
        import pprint; pprint.pprint(dic)
    return dic


if __name__ == '__main__':
    if '--ayuda' in sys.argv:
        print(LICENCIA)
        print(AYUDA)
        sys.exit(0)

    if '--formato' in sys.argv:
        print("Formato:")
        for msg, formato in sorted(FORMATOS.items(), key=lambda x: TIPO_REGISTROS_REV[x[0]]):
            tipo_reg = TIPO_REGISTROS_REV[msg]
            comienzo = 1
            print("=== %s ===" % msg)
            print("|| Campo %-39s || Posición || Longitud || Tipo %7s || Dec. || Valor ||" % (" ", " "))
            for fmt in formato:
                clave, longitud, tipo = fmt[0:3]
                dec = len(fmt)>3 and fmt[3] or (tipo=='I' and '2' or '')
                print("|| %-45s || %8d || %8d || %-12s || %-4s || %-5s ||" % (
                    clave, comienzo, longitud, tipo,
                    ("%s" % dec) if tipo == I else "",
                    ("%s" % tipo_reg) if clave == "tipo_reg" else "",
                ))
                comienzo += longitud
        sys.exit(0)

    from ConfigParser import SafeConfigParser

    try:
    
        for arg in sys.argv[1:]:
            if arg.startswith("--"):
                break
            print("Usando configuración:", arg)
            CONFIG_FILE = arg

        config = SafeConfigParser()
        config.read(CONFIG_FILE)
        CERT = config.get('WSAA','CERT')
        PRIVATEKEY = config.get('WSAA','PRIVATEKEY')
        CUIT = config.get('WSCPE','CUIT')
        ENTRADA = config.get('WSCPE','ENTRADA')
        SALIDA = config.get('WSCPE','SALIDA')
        
        if config.has_option('WSAA','URL') and not HOMO:
            wsaa_url = config.get('WSAA','URL')
        else:
            wsaa_url = None
        if config.has_option('WSCPE','URL') and not HOMO:
            wscpe_url = config.get('WSCPE','URL')
        else:
            wscpe_url = WSDL[HOMO]

        if config.has_section('DBF'):
            conf_dbf = dict(config.items('DBF'))
            if DEBUG: print("conf_dbf", conf_dbf)
        else:
            conf_dbf = {}

        DEBUG = '--debug' in sys.argv
        XML = '--xml' in sys.argv

        if DEBUG or "--version" in sys.argv:
            print("WSCPE cliente:", __version__, "componente:", WSCPE.Version)
            print("Usando Configuración:")
            print("wsaa_url:", wsaa_url)
            print("wscpe_url:", wscpe_url)

        # obteniendo el TA
        from wsaa import WSAA
        wsaa = WSAA()
        ta = wsaa.Autenticar("wscpe", CERT, PRIVATEKEY, wsaa_url, debug=DEBUG)
        ##if not ta:
        ##    sys.exit("Imposible autenticar con WSAA: %s" % wsaa.Excepcion)

        # cliente soap del web service
        wscpe = WSCPE()
        wscpe.Conectar(wsdl=wscpe_url)
        ##print(wscpe.client.help("autorizarCPEAutomotor"))
        wscpe.SetTicketAcceso(ta)
        wscpe.Cuit = CUIT
        ok = None
        
        if '--dummy' in sys.argv:
            ret = wscpe.Dummy()
            print("AppServerStatus", wscpe.AppServerStatus)
            print("DbServerStatus", wscpe.DbServerStatus)
            print("AuthServerStatus", wscpe.AuthServerStatus)
            sys.exit(0)

        if '--ult' in sys.argv:
            try:
                sucursal = int(sys.argv[sys.argv.index("--ult") + 1])
            except (IndexError, ValueError):
                sucursal = 1
            try:
                tipo_cpe = int(sys.argv[sys.argv.index("--ult") + 2])
            except (IndexError, ValueError):
                tipo_cpe = 74
            rec = {}
            print("Consultando ultimo cpe sucursal=%s tipo_cpe=%s" % (sucursal, tipo_cpe))
            ok = wscpe.ConsultarUltNroOrden(tipo_cpe=tipo_cpe, sucursal=sucursal)
            if wscpe.Excepcion:
                print("EXCEPCION:", wscpe.Excepcion, file=sys.stderr)
                if DEBUG: print(wscpe.Traceback, sys.stderr)
            print("Ultimo Nro de CPE", wscpe.NroOrden)
            print("Errores:", wscpe.Errores)

        if '--consultar' in sys.argv:
            rec = {}
            try:
                nro_orden = sys.argv[sys.argv.index("--consultar") + 1]
                sucursal = sys.argv[sys.argv.index("--consultar") + 2]
                tipo_cpe = sys.argv[sys.argv.index("--consultar") + 3]
                nro_ctg = sys.argv[sys.argv.index("--consultar") + 4]
            except (IndexError, ValueError):
                tipo_cpe = raw_input("Tipo de CPE [74]:") or 74
                sucursal = raw_input("Sucursal [1]:") or 1
                nro_orden = raw_input("Nro de orden:") or 1
                nro_ctg = raw_input("Nro de CTG:") or None
            if nro_ctg:
                ok = wscpe.ConsultarCPEAutomotor(cuit_solicitante=wscpe.Cuit, nro_ctg=nro_ctg)
            else:
                ok = wscpe.ConsultarCPEAutomotor(tipo_cpe=tipo_cpe, sucursal=sucursal, nro_orden=nro_orden, cuit_solicitante=wscpe.Cuit)
            if wscpe.Excepcion:
                print ("EXCEPCION:", wscpe.Excepcion, file=sys.stderr)
                if DEBUG: print(wscpe.Traceback, file=sys.stderr)
            print("Nro de CTG", wscpe.NroCTG)
            print("Errores:", wscpe.Errores)
            if DEBUG:
                import pprint
                pprint.pprint(wscpe.cpe)

        ##wscpe.client.help("generarCPE")
        if '--prueba' in sys.argv:
            ok = wscpe.ConsultarUltNroOrden(sucursal=222, tipo_cpe=74)
            nro_orden = wscpe.NroOrden + 1
            dic = dict(
                    tipo_cpe=74,  # 74: CPE Automotor, 75: CPE Ferroviaria,  99: Flete Corto.
                    cuit_solicitante=wscpe.Cuit,
                    sucursal=222,
                    nro_orden=nro_orden,
                    observaciones="Notas del transporte",
            )
            dic["origen"] = [dict(
                    #cod_provincia_operador=12,
                    #cod_localidad_operador=6904,
                    #planta=1938,
                    cod_provincia_productor=1,
                    cod_localidad_productor=14310,
            )]
            dic["retiro_productor"] = [dict(
                    corresponde_retiro_productor="false",
                    es_solicitante_campo="true",
                    certificado_coe=None,  # 330100025869
                    cuit_remitente_comercial_productor=None,  # 20111111112
            )]
            dic["intervinientes"] = [dict(
                    cuit_remitente_comercial_venta_primaria=27000000014,
                    cuit_remitente_comercial_venta_secundaria=None,
                    cuit_mercado_a_termino=None,
                    cuit_corredor_venta_primaria=None,
                    cuit_corredor_venta_secundaria=None,
                    cuit_remitente_comercial_venta_secundaria2=20400000000,
                    cuit_representante_entregador=None,
                    cuit_representante_recibidor=None,
            )]
            dic["datos_carga"] = [dict(
                    cod_grano=23,
                    cosecha=2021,
                    peso_bruto=110,
                    peso_tara=10,
            )]
            dic["destino"] = [dict(
                    cuit_destino=wscpe.Cuit,
                    es_destino_campo="true",
                    cod_provincia=12,
                    cod_localidad=14310,
                    planta=1938,
                    cuit_destinatario=wscpe.Cuit,
            )]
            dic["transporte"] = [dict(
                    cuit_transportista=20120372913,
                    dominio="AB000ST",
                    fecha_hora_partida=(datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()[:-7],
                    km_recorrer=500,
                    cuit_chofer='20333333334',
                    codigo_turno=None,
                    mercaderia_fumigada="true",
                    cuit_pagador_flete=None,
                    cuit_intermediario_flete=None,
                    tarifa=None,
                    tarifa_referencia=1234.5,
            ), dict(
                    dominio="AC001ST",
            )
            ]
            dic["contingencia"] = [dict(
                    concepto="B",
                    cuit_transportista=20333333334,
                    nro_operativo=1111111111,
                    concepto_desactivacion="B",
                    descripcion="Desctrucción carga",
            )]
            escribir_archivo(dic, ENTRADA, False)

        if '--cargar' in sys.argv:
            dic = leer_archivo(ENTRADA)
            wscpe.CrearCPE(actualiza='--autorizar' not in sys.argv)
            wscpe.AgregarCabecera(**dic)
            if dic.get("origen"):
                wscpe.AgregarOrigen(**dic['origen'][0])
            if dic.get("retiro_productor"):
                wscpe.AgregarRetiroProductor(**dic['retiro_productor'][0])
            if dic.get("intervinientes"):
                wscpe.AgregarIntervinientes(**dic['intervinientes'][0])
            if dic.get("datos_carga"):
                wscpe.AgregarDatosCarga(**dic['datos_carga'][0])
            if dic.get("destino"):
                wscpe.AgregarDestino(**dic['destino'][0])
            if dic.get("transporte"):
                dominios = []
                for transporte in reversed(dic['transporte']):
                    dominios.insert(0, transporte["dominio"])
                transporte["dominio"] = dominios
                wscpe.AgregarTransporte(**transporte)
            if dic.get("contingencia"):
                contingencia = dic['contingencia'][0]
                del contingencia["tipo_reg"]
                if '--informar_contingencia' in sys.argv:
                    for campo in "cuit_transportista", "nro_operativo", "concepto_desactivacion":
                        del contingencia[campo]
                    wscpe.AgregarContingencia(**contingencia)
                elif '--cerrar_contingencia' in sys.argv:
                    wscpe.AgregarCerrarContingencia(**contingencia)
        else:
            dic = {}

        if '--autorizar' in sys.argv:
            if '--testing' in sys.argv:
                wscpe.LoadTestXML("tests/xml/wscpe.xml")  # cargo respuesta

            if not "--ferroviaria" in sys.argv:
                ok = wscpe.AutorizarCPEAutomotor(archivo="cpe.pdf")
            else:
                ok = wscpe.AutorizarCPEFerroviaria(archivo="cpe.pdf")

        if '--editar' in sys.argv:
            cabecera = dic
            interviniente = dic["intervinientes"][0] if "intervinientes" in dic else {}
            transporte = dic["transporte"][0] if "transporte" in dic else {}
            datos_carga = dic["datos_carga"][0] if "datos_carga" in dic else {}
            if not "--ferroviaria" in sys.argv:
                ok = wscpe.EditarCPEAutomotor(
                    nro_ctg=cabecera.get("nro_ctg"),
                    cuit_corredor_venta_primaria=interviniente.get("cuit_corredor_venta_primaria"),
                    cuit_corredor_venta_secundaria=interviniente.get("cuit_corredor_venta_secundaria"),
                    cuit_remitente_comercial_venta_primaria=interviniente.get("cuit_remitente_comercial_venta_primaria"),
                    cuit_remitente_comercial_venta_secundaria=interviniente.get("cuit_remitente_comercial_venta_secundaria"),
                    cuit_remitente_comercial_venta_secundaria2=interviniente.get("cuit_remitente_comercial_venta_secundaria2"),
                    cuit_chofer=transporte.get("cuit_chofer"),
                    cuit_transportista=transporte.get("cuit_transportista"),
                    peso_bruto=datos_carga.get("peso_bruto"),
                    cod_grano=datos_carga.get("cod_grano"),
                    dominio=transporte.get("dominio"),
                )
            else:
                ok = wscpe.EditarCPEFerroviaria(
                    nro_ctg=cabecera.get("nro_ctg"),
                    cuit_corredor_venta_primaria=interviniente.get("cuit_corredor_venta_primaria"),
                    cuit_corredor_venta_secundaria=interviniente.get("cuit_corredor_venta_secundaria"),
                    cuit_remitente_comercial_venta_primaria=interviniente.get("cuit_remitente_comercial_venta_primaria"),
                    cuit_remitente_comercial_venta_secundaria=interviniente.get("cuit_remitente_comercial_venta_secundaria"),
                    cuit_remitente_comercial_venta_secundaria2=interviniente.get("cuit_remitente_comercial_venta_secundaria2"),
                    cuit_transportista=transporte.get("cuit_transportista"),
                    peso_bruto=datos_carga.get("peso_bruto"),
                    cod_grano=datos_carga.get("cod_grano"),
                )

        if '--anular' in sys.argv:
            ok = wscpe.AnularCPE()

        if '--anular_todo' in sys.argv:
            # Limpieza de CPE pendientes para evitar el error de validación de AFIP:
            # 2002: 'No es posible guardar la solicitud si posee cartas de porte vencidas.'
            ok = raw_input("CUIDADO: esto anulara todas las CPE, ingresar Si para confirmar: ")
            if ok == "Si":
                sucursal_desde = int(raw_input("Sucursal desde: "))
                sucursal_hasta = int(raw_input("Sucursal hasta: "))
                for tipo in 74, 75, 99:
                    for suc in range(sucursal_desde, sucursal_hasta+1):
                        wscpe.ConsultarUltNroOrden(sucursal=suc, tipo_cpe=tipo)
                        ult = wscpe.NroOrden
                        print ("ConsultarUltNroOrden: Tipo %s suc %4d ult %d" % (tipo, suc, ult))
                        for nro in range(ult, 1, -1):
                            wscpe.CrearCPE(True)
                            wscpe.AgregarCabecera(tipo_cpe=tipo, sucursal=suc, nro_orden=nro)
                            wscpe.AnularCPE()
                            err = wscpe.ErrMsg
                            estado = wscpe.Estado
                            print ("AnularCPE: Tipo %s suc %4d num %d -> %s %s" % (tipo, suc, nro, estado, err))

        if '--informar_contingencia' in sys.argv:
            ok = wscpe.InformarContingencia()

        if '--cerrar_contingencia' in sys.argv:
            ok = wscpe.CerrarContingenciaCPE()

        if '--rechazo' in sys.argv:
            ok = wscpe.RechazoCPE()

        if '--confirmar_arribo' in sys.argv:
            ok = wscpe.ConfirmarArriboCPE()

        if '--descargado_destino' in sys.argv:
            ok = wscpe.DescargadoDestinoCPE()

        if '--confirmacion_definitiva' in sys.argv:
            if not "--ferroviaria" in sys.argv:
                ok = wscpe.ConfirmacionDefinitivaCPEAutomotor()
            else:
                ok = wscpe.ConfirmacionDefinitivaCPEFerroviaria()

        if '--nuevo_destino_destinatario' in sys.argv:
            if not "--ferroviaria" in sys.argv:
                ok = wscpe.NuevoDestinoDestinatarioCPEAutomotor()
            else:
                ok = wscpe.NuevoDestinoDestinatarioCPEFerroviaria()

        if '--regreso_origen' in sys.argv:
            if not "--ferroviaria" in sys.argv:
                ok = wscpe.RegresoOrigenCPEAutomotor()
            else:
                ok = wscpe.RegresoOrigenCPEFerroviaria()

        if '--desvio' in sys.argv:
            if not "--ferroviaria" in sys.argv:
                ok = wscpe.DesvioCPEAutomotor()
            else:
                ok = wscpe.DesvioCPEFerroviaria()

        if ok is not None:
            print("Resultado: ", wscpe.Resultado)
            print("Numero CTG: ", wscpe.NroCTG)
            print("Numero Orden: ", wscpe.NroOrden)
            print("Fecha Emision", wscpe.FechaEmision)
            print("Fecha Inicio Estado", wscpe.FechaInicioEstado)
            print("Fecha Vencimiento", wscpe.FechaVencimiento)
            print("Estado: ", wscpe.Estado)
            obs = wscpe.Observaciones.strip() if wscpe.Observaciones else ""
            obs = obs.replace("\n", "\t").replace("\r", "\t")
            print("Observaciones:", obs)
            print("Tarifa Referencia:", wscpe.TarifaReferencia)
            print("Evento:", wscpe.Evento)
            dic['nro_ctg'] = wscpe.NroCTG

            dic['resultado'] = wscpe.Resultado
            dic['estado'] = wscpe.Estado
            dic['observaciones'] = obs
            dic['fecha_emision'] = wscpe.FechaEmision
            dic['fecha_vencimiento'] = wscpe.FechaVencimiento
            dic['fecha_inicio_estado'] = wscpe.FechaInicioEstado
            dic['errores'] = wscpe.errores
            dic['evento'] = wscpe.Evento
            if dic.get('transporte'):
                dic['transporte'][0]['tarifa_referencia'] = wscpe.TarifaReferencia

        if '--grabar' in sys.argv:
            escribir_archivo(dic, SALIDA)

        # Recuperar parámetros:

        if "--provincias" in sys.argv:
            ret = wscpe.ConsultarProvincias()
            print("\n".join(ret))

        if "--localidades_por_provincia" in sys.argv:
            ret = wscpe.ConsultarLocalidadesPorProvincia(sys.argv[2])
            print("\n".join(ret))

        if "--localidades_por_productor" in sys.argv:
            ret = wscpe.ConsultarLocalidadesProductor(wscpe.Cuit)
            print("\n".join(ret))

        if '--tipos_granos' in sys.argv:
            ret = wscpe.ConsultarTiposGrano()
            print("\n".join(ret))

        if "--plantas" in sys.argv:
            ret = wscpe.ConsultarPlantas(cuit=CUIT)
            print("\n".join(ret))

        if wscpe.Errores:
            print("Errores:", wscpe.Errores)

        print("hecho.")
        
    except SoapFault as e:
        print("Falla SOAP:", e.faultcode, e.faultstring)
        sys.exit(3)
    except Exception as e:
        ex = utils.exception_info()
        print(ex)
        if DEBUG:
            raise
        sys.exit(5)

    finally:
        import xml.dom.minidom
        if XML:
            for (xml_data, xml_path) in ((wscpe.XmlRequest, "wscpe_cli_req.xml"), (wscpe.XmlResponse, "wscpe_cli_res.xml")):
                with open(xml_path, "w") as x:
                    if xml_data:
                        dom = xml.dom.minidom.parseString(xml_data)
                        x.write(dom.toprettyxml(encoding="utf8"))
