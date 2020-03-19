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

#Controlador para Exporta ventas por grupos a Excel
import xlsxwriter
from PyQt5.QtWidgets import QApplication
from peewee import fn

from controladores.ControladorBase import ControladorBase
from libs import Constantes
from libs.Utiles import GuardarArchivo, LeerIni, AbrirArchivo
from modelos.Articulos import Articulo
from modelos.Cabfact import Cabfact
from modelos.Detfact import Detfact
from modelos.Grupos import Grupo
from modelos.Impuestos import Impuesto
from vistas.InformeVentasPorGrupo import InformeVentasPorGrupoView


class InformeVentasPorGrupoController(ControladorBase):

    def __init__(self):
        super(InformeVentasPorGrupoController, self).__init__()
        self.view = InformeVentasPorGrupoView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnExcel.clicked.connect(self.onClickExcel)

    def onClickExcel(self, mostrar=True):
        archivo = GuardarArchivo(filter="*.XLSX", directory="excel/", filename="informe de ventas por grupo")
        if not archivo:
            return

        archivo = str(archivo)
        self.view.avance.setVisible(True)
        data = Cabfact().select().where(Cabfact.fecha.between(
            self.view.textDesdeFecha.date().toPyDate(), self.view.textHastaFecha.date().toPyDate()))
        workbook = xlsxwriter.Workbook(archivo)
        worksheet = workbook.add_worksheet()
        fila, col = 0, 0

        worksheet.write(fila, 0, "Desde fecha {} hasta fecha {}".format(self.view.textDesdeFecha.text(),
                                                                        self.view.textHastaFecha.text()))
        fila += 2
        worksheet.write(fila, 0, 'Fecha')
        worksheet.write(fila, 1, 'Tipo Comprobante')
        worksheet.write(fila, 2, 'Numero')
        worksheet.write(fila, 3, 'Grupo')
        worksheet.write(fila, 4, 'Importe')
        fila += 1
        totalData = len(data)
        cant = 0.0
        for d in data:
            QApplication.processEvents()
            cant += 1.
            self.view.avance.actualizar(cant/totalData*100.)
            detfac = Detfact.select().where(Detfact.idcabfact == d.idcabfact)
            for det in detfac:
                worksheet.write(fila, 0, d.fecha.strftime('%d/%m/%Y'))
                worksheet.write(fila, 1, d.tipocomp.nombre)
                worksheet.write(fila, 2, d.numero)
                worksheet.write(fila, 3, det.idarticulo.grupo.nombre)
                if LeerIni(clave='cat_iva', key='WSFEv1') == Constantes.CODIGO_RI:
                    worksheet.write(fila, 4, det.precio * det.cantidad + det.montoiva + det.montodgr)
                else:
                    worksheet.write(fila, 4, det.precio * det.cantidad)
                fila += 1
        precio = fn.Sum(Detfact.precio * Detfact.cantidad).alias("precio")
        montoiva = fn.Sum(Detfact.montoiva).alias("montoiva")
        montodgr = fn.Sum(Detfact.montodgr).alias("montodgr")
        det = Detfact.select(precio, montodgr, montoiva, Grupo.nombre, Impuesto.porcentaje)\
            .join(Cabfact).switch(Detfact).join(Articulo).join(Grupo).join(Impuesto).where(
            Cabfact.fecha.between(self.view.textDesdeFecha.date().toPyDate(), self.view.textHastaFecha.date().toPyDate()))\
            .group_by(Detfact.idarticulo.grupo.idgrupo)
        fila += 2
        for d in det:
            worksheet.write(fila, 1, d.idarticulo.grupo.nombre)
            if LeerIni(clave='cat_iva', key='WSFEv1') == Constantes.CODIGO_RI:
                worksheet.write(fila, 2, d.precio + d.montoiva, d.montodgr)
                worksheet.write(fila, 3, d.idarticulo.grupo.impuesto.porcentaje)
            else:
                worksheet.write(fila, 2, d.precio)
                worksheet.write(fila, 3, d.idarticulo.grupo.impuesto.porcentaje)
                fila += 1
        workbook.close()
        self.view.avance.setVisible(False)
        if mostrar:
            AbrirArchivo(archivo)