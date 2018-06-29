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

#Exporta libro iva ventas en formato excel
import xlsxwriter
from PyQt4.QtGui import QFileDialog

from controladores.ControladorBase import ControladorBase
from libs.Utiles import AbrirArchivo
from modelos.Cabfact import Cabfact
from vistas.IVAVentas import IVAVentasView

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2018 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"


class IVAVentasController(ControladorBase):

    def __init__(self):
        super(IVAVentasController, self).__init__()
        self.view = IVAVentasView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnExcel.clicked.connect(self.ExportaExcel)

    def ExportaExcel(self):
        cArchivo = str(QFileDialog.getSaveFileName(caption="Guardar archivo", directory="", filter="*.XLSX"))
        if not cArchivo:
            return
        workbook = xlsxwriter.Workbook(cArchivo)
        worksheet = workbook.add_worksheet()

        data = Cabfact().select().where(Cabfact.fecha.between(
            self.view.lineDesdeFecha.date().toPyDate(), self.view.lineHastaFecha.date().toPyDate()))
        fila, col = 0, 0
        worksheet.write(fila, 0, 'Fecha')
        worksheet.write(fila, 1, 'Tipo Comprobante')
        worksheet.write(fila, 2, 'Cliente')
        worksheet.write(fila, 3, 'Reg IVA')
        worksheet.write(fila, 4, 'CUIT')
        worksheet.write(fila, 5, 'Neto 21')
        worksheet.write(fila, 6, 'Neto 10.5')
        worksheet.write(fila, 7, 'Operaciones Exentas')
        worksheet.write(fila, 8, 'IVA')
        worksheet.write(fila, 9, 'Percep. DGR')
        worksheet.write(fila, 10, 'CAE')
        worksheet.write(fila, 11, 'Venc CAE')
        worksheet.write(fila, 12, 'Total')
        fila += 1
        for d in data:
            worksheet.write(fila, 0, d.fecha.strftime('%d/%m/%Y'))
            worksheet.write(fila, 1, d.tipocomp.nombre)
            worksheet.write(fila, 2, d.cliente.nombre)
            worksheet.write(fila, 3, d.cliente.tiporesp.nombre)
            worksheet.write(fila, 4, d.cliente.cuit)
            worksheet.write(fila, 5, d.netoa)
            worksheet.write(fila, 6, d.netob)
            worksheet.write(fila, 7, 0)
            worksheet.write(fila, 8, d.iva)
            worksheet.write(fila, 9, d.percepciondgr)
            worksheet.write(fila, 10, d.cae)
            worksheet.write(fila, 11, d.venccae)
            worksheet.write(fila, 12, '=sum(F{}:J{})'.format(fila+1, fila+1))
            fila += 1

        workbook.close()
        AbrirArchivo(cArchivo)
