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

#Exporta libro iva compras en formato excel
import decimal

import xlsxwriter

from controladores.ControladorBase import ControladorBase
from libs.Utiles import GuardarArchivo, AbrirArchivo
from modelos.CabFacProv import CabFactProv
from modelos.DetFactProv import DetFactProv
from vistas.IVACompras import IVAComprasView

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2018 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"

class IVAComprasController(ControladorBase):

    def __init__(self):
        super(IVAComprasController, self).__init__()
        self.view = IVAComprasView()
        self.conectarWidgets()
        self.EstablecerOrden()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnExcel.clicked.connect(self.Exporta)

    def Exporta(self):
        cabecera = CabFactProv.select().where(CabFactProv.periodo == self.view.periodo.cPeriodo)
        archivo = GuardarArchivo(filter="*.XLSX", directory="excel/", filename="iva compras {}".format(
            self.view.periodo.cPeriodo
        ))
        if not archivo:
            return
        total = cabecera.count()
        i = 0
        self.view.avance.setVisible(True)
        archivo = str(archivo)
        workbook = xlsxwriter.Workbook(archivo)
        worksheet = workbook.add_worksheet()
        # Start from the first cell. Rows and columns are zero indexed.
        row = 0
        col = 0
        worksheet.write(row, col, "Periodo listado {}".format(self.view.periodo.cPeriodo))
        row += 1
        worksheet.write(row, col, 'Fecha')
        worksheet.write(row, col + 1, 'Comprobante')
        worksheet.write(row, col + 2, 'Razon Social')
        worksheet.write(row, col + 3, 'CUIT')
        worksheet.write(row, col + 4, 'CAI/CAE')
        worksheet.write(row, col + 5, 'Neto 21%')
        worksheet.write(row, col + 6, 'Neto 10.5%')
        worksheet.write(row, col + 7, 'Neto 27%')
        worksheet.write(row, col + 8, 'IVA')
        worksheet.write(row, col + 9, 'Perc IVA')
        worksheet.write(row, col + 10, 'Exento')
        worksheet.write(row, col + 11, 'Imp. Int')
        worksheet.write(row, col + 12, 'DGR')
        worksheet.write(row, col + 13, 'Monotributo')
        worksheet.write(row, col + 14, 'Total')
        for cab in cabecera:
            self.view.avance.setValue(i / total * 100)
            row += 1
            worksheet.write(row, col, cab.fechaem.strftime("%d/%m/%Y"))
            worksheet.write(row, col + 1, '{} {}'.format(cab.tipocomp.nombre, cab.numero))
            worksheet.write(row, col + 2, cab.idproveedor.nombre)
            worksheet.write(row, col + 3, cab.idproveedor.cuit)
            worksheet.write(row, col + 4, cab.cai)

            detalle = DetFactProv.select().where(DetFactProv.idpcabecera == cab.idpcabfact)
            neto21 = decimal.Decimal.from_float(0.)
            neto105 = decimal.Decimal.from_float(0.)
            neto27 = decimal.Decimal.from_float(0.)
            monotributo = decimal.Decimal.from_float(0.)
            for det in detalle:
                if det.iva == 21:
                    neto21 += det.neto
                elif det.iva == 10.5:
                    neto105 += det.neto
                elif det.iva == 27:
                    neto27 += det.neto
                elif det.iva == 0 and cab.tipocomp.abreviatura.strip() == 'C':
                    monotributo += det.neto

            multiplicador = decimal.Decimal.from_float(-1.) if cab.tipocomp.lado.strip() == 'H' else \
                decimal.Decimal.from_float(1.)

            worksheet.write(row, col + 5, neto21 * multiplicador)
            worksheet.write(row, col + 6, neto105 * multiplicador)
            worksheet.write(row, col + 7, neto27 * multiplicador)
            worksheet.write(row, col + 8, cab.iva * multiplicador)
            worksheet.write(row, col + 9, cab.percepcioniva * multiplicador)
            worksheet.write(row, col + 10, cab.exentos * multiplicador)
            worksheet.write(row, col + 11, cab.impuestos * multiplicador)
            worksheet.write(row, col + 12, cab.percepciondgr * multiplicador)
            worksheet.write(row, col + 13, monotributo * multiplicador)
            worksheet.write(row, col + 14, '=sum(F{}:N{})'.format(row + 1,row + 1))

        workbook.close()
        self.view.avance.setVisible(False)
        AbrirArchivo(archivo)

