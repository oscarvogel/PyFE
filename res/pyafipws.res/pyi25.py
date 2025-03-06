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

"Módulo para generar códigos de barra en Entrelazado 2 de 5 (I25)"
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from builtins import str
from builtins import range
from builtins import object
from past.utils import old_div

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2011-2021 Mariano Reingart"
__license__ = "LGPL-3.0-or-later"
__version__ = "3.02e"

import os
import sys
import traceback
from PIL import Image, ImageFont, ImageDraw


class PyI25(object):
    "Interfaz para generar PDF de Factura Electrónica"
    _public_methods_ = ["GenerarImagen", "DigitoVerificadorModulo10"]
    _public_attrs_ = ["Version", "Excepcion", "Traceback"]

    _reg_progid_ = "PyI25"
    _reg_clsid_ = "{5E6989E8-F658-49FB-8C39-97C74BC67650}"

    def __init__(self):
        self.Version = __version__
        self.Exception = self.Traceback = ""

    def GenerarImagen(
        self,
        codigo,
        archivo="barras.png",
        basewidth=3,
        width=None,
        height=30,
        extension="PNG",
    ):
        "Generar una imágen con el código de barras Interleaved 2 of 5"
        # basado de:
        #  * http://www.fpdf.org/en/script/script67.php
        #  * http://code.activestate.com/recipes/426069/

        wide = basewidth
        narrow = old_div(basewidth, 3)

        # códigos ancho/angostos (wide/narrow) para los dígitos
        bars = (
            "nnwwn",
            "wnnnw",
            "nwnnw",
            "wwnnn",
            "nnwnw",
            "wnwnn",
            "nwwnn",
            "nnnww",
            "wnnwn",
            "nwnwn",
            "nn",
            "wn",
        )

        # agregar un 0 al principio si el número de dígitos es impar
        if len(codigo) % 2:
            codigo = "0" + codigo

        if not width:
            width = (len(codigo) * 3) * basewidth + (10 * narrow)
            print(width)
            # width = 380
        # crear una nueva imágen
        im = Image.new("1", (width, height))

        # agregar códigos de inicio y final
        codigo = "::" + codigo.lower() + ";:"  # A y Z en el original

        # crear un drawer
        draw = ImageDraw.Draw(im)

        # limpiar la imágen
        draw.rectangle(((0, 0), (im.size[0], im.size[1])), fill=256)

        xpos = 0
        # dibujar los códigos de barras
        for i in range(0, len(codigo), 2):
            # obtener el próximo par de dígitos
            bar = ord(codigo[i]) - ord("0")
            space = ord(codigo[i + 1]) - ord("0")
            # crear la sequencia barras (1er dígito=barras, 2do=espacios)
            seq = ""
            for s in range(len(bars[bar])):
                seq = seq + bars[bar][s] + bars[space][s]

            for s in range(len(seq)):
                if seq[s] == "n":
                    width = narrow
                else:
                    width = wide

                # dibujar barras impares (las pares son espacios)
                if not s % 2:
                    draw.rectangle(((xpos, 0), (xpos + width - 1, height)), fill=0)
                xpos = xpos + width

        im.save(archivo, extension.upper())
        return True

    def DigitoVerificadorModulo10(self, codigo):
        "Rutina para el cálculo del dígito verificador 'módulo 10'"
        # http://www.consejo.org.ar/Bib_elect/diciembre04_CT/documentos/rafip1702.htm
        # Etapa 1: comenzar desde la izquierda, sumar todos los caracteres ubicados en las posiciones impares.
        codigo = codigo.strip()
        if not codigo or not codigo.isdigit():
            return ""
        etapa1 = sum([int(c) for i, c in enumerate(codigo) if not i % 2])
        # Etapa 2: multiplicar la suma obtenida en la etapa 1 por el número 3
        etapa2 = etapa1 * 3
        # Etapa 3: comenzar desde la izquierda, sumar todos los caracteres que están ubicados en las posiciones pares.
        etapa3 = sum([int(c) for i, c in enumerate(codigo) if i % 2])
        # Etapa 4: sumar los resultados obtenidos en las etapas 2 y 3.
        etapa4 = etapa2 + etapa3
        # Etapa 5: buscar el menor número que sumado al resultado obtenido en la etapa 4 dé un número múltiplo de 10. Este será el valor del dígito verificador del módulo 10.
        digito = 10 - (etapa4 - (int(old_div(etapa4, 10)) * 10))
        if digito == 10:
            digito = 0
        return str(digito)


def main():

    if "--register" in sys.argv or "--unregister" in sys.argv:
        import win32com.server.register

        win32com.server.register.UseCommandLine(PyI25)
    elif "/Automate" in sys.argv:
        try:
            # MS seems to like /automate to run the class factories.
            import win32com.server.localserver

            win32com.server.localserver.serve([PyI25._reg_clsid_])
        except Exception:
            raise
    elif "py2exe" in sys.argv:
        from distutils.core import setup
        from pyafipws.nsis import build_installer, Target
        import py2exe
        import glob

        VCREDIST = (
            ".",
            glob.glob(r"c:\Program Files\Mercurial\mfc*.*")
            + glob.glob(r"c:\Program Files\Mercurial\Microsoft.VC90.CRT.manifest"),
        )
        setup(
            name="PyI25",
            version=__version__,
            description="Interfaz PyAfipWs I25 %s",
            long_description=__doc__,
            author="Mariano Reingart",
            author_email="reingart@gmail.com",
            url="http://www.sistemasagiles.com.ar",
            license="GNU GPL v3",
            com_server=[
                {"modules": "pyi25", "create_exe": True, "create_dll": True},
            ],
            console=[
                Target(
                    module=sys.modules[__name__],
                    script="pyi25.py",
                    dest_base="pyi25_cli",
                )
            ],
            windows=[
                Target(
                    module=sys.modules[__name__],
                    script="pyi25.py",
                    dest_base="pyi25_win",
                )
            ],
            options={
                "py2exe": {
                    "includes": [],
                    "optimize": 2,
                    "excludes": [
                        "pywin",
                        "pywin.dialogs",
                        "pywin.dialogs.list",
                        "win32ui",
                        "distutils.core",
                        "py2exe",
                        "nsis",
                    ],
                    #'skip_archive': True,
                }
            },
            data_files=[
                VCREDIST,
                (".", ["licencia.txt"]),
            ],
            cmdclass={"py2exe": build_installer},
        )
    else:

        pyi25 = PyI25()

        if "--barras" in sys.argv:
            barras = sys.argv[sys.argv.index("--barras") + 1]
        else:
            cuit = 20267565393
            tipo_cbte = 2
            punto_vta = 4001
            cae = 61203034739042
            fch_venc_cae = 20110529

            # codigo de barras de ejemplo:
            barras = "%11s%02d%04d%s%8s" % (
                cuit,
                tipo_cbte,
                punto_vta,
                cae,
                fch_venc_cae,
            )

        if not "--noverificador" in sys.argv:
            barras = barras + pyi25.DigitoVerificadorModulo10(barras)

        if "--archivo" in sys.argv:
            archivo = sys.argv[sys.argv.index("--archivo") + 1]
            extension = os.path.splitext(archivo)[1]
            extension = extension.upper()[1:]
            if extension == "JPG":
                extension = "JPEG"
        else:
            archivo = "prueba-cae-i25.png"
            extension = "PNG"

        print("barras", barras)
        print("archivo", archivo)
        pyi25.GenerarImagen(barras, archivo, extension=extension)

        if not "--mostrar" in sys.argv:
            pass
        elif sys.platform == "linux2" or sys.platform == "linux":
            os.system("eog " "%s" "" % archivo)
        else:
            os.startfile(archivo)

if __name__ == "__main__":
    main()