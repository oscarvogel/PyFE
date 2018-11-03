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
import decimal

import xlsxwriter
from PyQt4.QtGui import QFileDialog, QApplication

from controladores.ControladorBase import ControladorBase
from controladores.FE import FEv1
from libs import Constantes
from libs.Utiles import AbrirArchivo, EsVerdadero, LeerIni
from modelos.Articulos import Articulo
from modelos.Cabfact import Cabfact
from modelos.Detfact import Detfact
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
        self.EstablecerOrden()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnExcel.clicked.connect(self.ExportaExcel)
        self.view.controles['desdeptovta'].editingFinished.connect(self.onEditinFinished)

    def ExportaExcel(self):
        self.view.avance.setVisible(True)
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
        worksheet.write(fila, 2, 'Numero')
        worksheet.write(fila, 3, 'Cliente')
        worksheet.write(fila, 4, 'Reg IVA')
        worksheet.write(fila, 5, 'CUIT')
        worksheet.write(fila, 6, 'Neto 21')
        worksheet.write(fila, 7, 'Neto 10.5')
        worksheet.write(fila, 8, 'Operaciones Exentas')
        worksheet.write(fila, 9, 'IVA')
        worksheet.write(fila, 10, 'Percep. DGR')
        worksheet.write(fila, 11, 'CAE')
        worksheet.write(fila, 12, 'Venc CAE')
        worksheet.write(fila, 13, 'Producto')
        worksheet.write(fila, 14, 'Servicio')
        worksheet.write(fila, 15, 'Total')
        fila += 1
        totalData = len(data)
        cant = 0.0
        for d in data:
            QApplication.processEvents()
            cant += 1.
            self.view.avance.actualizar(cant/totalData*100.)
            if str(self.view.controles['desdeptovta'].text()).zfill(4) <= d.numero[:4] <= \
                                str(self.view.controles['hastaptovta'].text()).zfill(4) \
                    and d.tipocomp.exporta:
                worksheet.write(fila, 0, d.fecha.strftime('%d/%m/%Y'))
                worksheet.write(fila, 1, d.tipocomp.nombre)
                worksheet.write(fila, 2, d.numero)
                worksheet.write(fila, 3, d.cliente.nombre)
                worksheet.write(fila, 4, d.cliente.tiporesp.nombre)
                worksheet.write(fila, 5, d.cliente.cuit)
                worksheet.write(fila, 6, d.netoa)
                worksheet.write(fila, 7, d.netob)
                worksheet.write(fila, 8, 0)
                worksheet.write(fila, 9, d.iva)
                worksheet.write(fila, 10, d.percepciondgr)
                worksheet.write(fila, 11, d.cae)
                worksheet.write(fila, 12, d.venccae.strftime('%d/%m/%Y') if d.venccae else '')
                deta = Detfact.select().where(Detfact.idcabfact == d.idcabfact)
                totserv = decimal.Decimal.from_float(0.)
                totprod = totserv
                for det in deta:
                    art = Articulo.get_by_id(det.idarticulo)
                    if art.concepto.strip():
                        if int(art.concepto.strip()) == FEv1.SERVICIOS:
                            totserv += det.precio * det.cantidad
                        else:
                            totprod += det.precio * det.cantidad
                    else:
                        totprod += det.precio * det.cantidad
                worksheet.write(fila, 13, totprod)
                worksheet.write(fila, 14, totserv)
                worksheet.write(fila, 15, '=sum(G{}:J{})'.format(fila+1, fila+1))
                fila += 1

        workbook.close()
        self.view.avance.setVisible(False)
        AbrirArchivo(cArchivo)

    def onEditinFinished(self):
        print(str(self.view.controles['desdeptovta'].text()).zfill(4))
        self.view.controles['desdeptovta'].setText(str(self.view.controles['desdeptovta'].text()).zfill(4))

    def EstablecerOrden(self):
        self.view.controles['desdeptovta'].proximoWidget = self.view.controles['hastaptovta']
        self.view.controles['hastaptovta'].proximoWidget = self.view.lineDesdeFecha
        self.view.lineDesdeFecha.proximoWidget = self.view.lineHastaFecha