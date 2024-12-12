#!/usr/bin/python
# -*- coding: latin-1 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"M?dulo para generar c?digos QR"

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2011 Mariano Reingart"
__license__ = "LGPL 3.0"
__version__ = "1.03b"

import base64
import json
import os
import sys
import tempfile

import qrcode


TEST_QR_DATA = """
eyJ2ZXIiOjEsImZlY2hhIjoiMjAyMC0xMC0xMyIsImN1aXQiOjMwMDAwMDAwMDA3LCJwdG9WdGEiOj
EwLCJ0aXBvQ21wIjoxLCJucm9DbXAiOjk0LCJpbXBvcnRlIjoxMjEwMCwibW9uZWRhIjoiRE9MIiwi
Y3R6Ijo2NSwidGlwb0RvY1JlYyI6ODAsIm5yb0RvY1JlYyI6MjAwMDAwMDAwMDEsInRpcG9Db2RBdX
QiOiJFIiwiY29kQXV0Ijo3MDQxNzA1NDM2NzQ3Nn0=""".replace("\n", "")


class PyQR:
    "Interfaz para generar Codigo QR de Factura Electr?nica"
    _public_methods_ = ['GenerarImagen', 'CrearArchivo',
                        ]
    _public_attrs_ = ['Version', 'Excepcion', 'Traceback', "URL", "Archivo",
                      'qr_ver', 'box_size', 'border', 'error_correction',
                     ]

    _reg_progid_ = "PyQR"
    _reg_clsid_ = "{0868A2B6-2DC7-478D-8884-A10E92C588DE}"

    URL = "https://www.afip.gob.ar/fe/qr/?p=%s"
    Archivo = "qr.png"

    # qrencode default parameters:
    qr_ver = 1
    box_size = 10
    border = 4
    error_correction = qrcode.constants.ERROR_CORRECT_L

    def __init__(self):
        self.Version = __version__
        self.Exception = self.Traceback = ""

    def CrearArchivo(self):
        """Crea un nombre de archivo temporal"""
        # para evitar errores de permisos y poder generar varios qr simultaneos
        tmp = tempfile.NamedTemporaryFile(prefix="qr_afip_",
                                          suffix=".png",
                                          delete=False)
        self.Archivo = tmp.name
        return self.Archivo

    def GenerarImagen(self, ver=1,
                      fecha="2020-10-13",
                      cuit=30000000007,
                      pto_vta=10, tipo_cmp=1, nro_cmp=94,
                      importe=12100, moneda="PES", ctz=1.000,
                      tipo_doc_rec=80, nro_doc_rec=20000000001,
                      tipo_cod_aut="E", cod_aut=70417054367476,
                      ):
        "Generar una im?gen con el c?digo QR"
        # basado en: https://www.afip.gob.ar/fe/qr/especificaciones.asp
        datos_cmp = {
            "ver": int(ver),
            "fecha": fecha,
            "cuit": int(cuit),
            "ptoVta": int(pto_vta),
            "tipoCmp": int(tipo_cmp),
            "nroCmp": int(nro_cmp),
            "importe": float(importe),
            "moneda": moneda,
            "ctz": float(ctz),
            "tipoDocRec": int(tipo_doc_rec),
            "nroDocRec": int(nro_doc_rec),
            "tipoCodAut": tipo_cod_aut,
            "codAut": int(cod_aut),
            }

        # convertir a representaci�n json y codificar en base64:
        datos_cmp_json = json.dumps(datos_cmp)
        url = self.URL % (base64.b64encode(datos_cmp_json))

        qr = qrcode.QRCode(
            version=self.qr_ver,
            error_correction=self.error_correction,
            box_size=self.box_size,
            border=self.border,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        img.save(self.Archivo, "PNG")
        return url


if __name__ == '__main__':

    if "--register" in sys.argv or "--unregister" in sys.argv:
        import win32com.server.register
        win32com.server.register.UseCommandLine(PyQR)
    elif "/Automate" in sys.argv:
        try:
            # MS seems to like /automate to run the class factories.
            import win32com.server.localserver
            win32com.server.localserver.serve([PyQR._reg_clsid_])
        except Exception:
            raise
    else:

        pyqr = PyQR()

        if '--datos' in sys.argv:
            args = sys.argv[sys.argv.index("--datos")+1:]
            (ver, fecha, cuit, pto_vta, tipo_cmp, nro_cmp, importe, moneda, ctz,
            tipo_doc_rec, nro_doc_rec, tipo_cod_aut, cod_aut) = args
        else:
            ver = 1
            fecha = "2020-10-13"
            cuit = 30000000007
            pto_vta = 10
            tipo_cmp = 1
            nro_cmp = 94
            importe = 12100
            moneda = "DOL"
            ctz = 65.000
            tipo_doc_rec = 80
            nro_doc_rec = 20000000001
            tipo_cod_aut = "E"
            cod_aut = 70417054367476

        if '--archivo' in sys.argv:
            pyqr.Archivo = sys.argv[sys.argv.index("--archivo")+1]
        else:
            pyqr.CrearArchivo()

        if '--url' in sys.argv:
            pyqr.URL = sys.argv[sys.argv.index("--url")+1]

        print("datos:", (ver, fecha, cuit, pto_vta, tipo_cmp, nro_cmp,
                         importe, moneda, ctz, tipo_doc_rec, nro_doc_rec,
                         tipo_cod_aut, cod_aut))
        print("archivo", pyqr.Archivo)

        url = pyqr.GenerarImagen(ver, fecha, cuit, pto_vta, tipo_cmp, nro_cmp,
                                importe, moneda, ctz, tipo_doc_rec, nro_doc_rec,
                                tipo_cod_aut, cod_aut)

        print("url generada:", url)

        if "--prueba" in sys.argv:
            qr_data_test = json.loads(base64.b64decode(TEST_QR_DATA))
            qr_data_gen = json.loads(base64.b64decode(url[33:]))
            assert url.startswith("https://www.afip.gob.ar/fe/qr/?p=")
            assert qr_data_test == qr_data_gen, "Diff: %r != %r" % (qr_data_test, qr_data_gen)
            print("QR data ok:", qr_data_gen)

        if not '--mostrar' in sys.argv:
            pass
        elif sys.platform=="linux2":
            os.system("eog ""%s""" % pyqr.Archivo)
        else:
            os.startfile(pyqr.archivo)