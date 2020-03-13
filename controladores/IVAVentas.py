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
from PyQt5.QtWidgets import QFileDialog, QApplication, QInputDialog

from controladores.ControladorBase import ControladorBase
from controladores.FE import FEv1
from libs import Constantes, Ventanas
from libs.Utiles import AbrirArchivo, EsVerdadero, LeerIni, inicializar_y_capturar_excepciones, GrabarIni, envia_correo
from modelos.Articulos import Articulo
from modelos.Cabfact import Cabfact
from modelos.Detfact import Detfact
from modelos.ParametrosSistema import ParamSist
from pyafipws.pyemail import PyEmail
from vistas.IVAVentas import IVAVentasView

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2018 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"


class IVAVentasController(ControladorBase):

    cArchivoGenerado = None

    def __init__(self):
        super(IVAVentasController, self).__init__()
        self.view = IVAVentasView()
        self.conectarWidgets()
        self.EstablecerOrden()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnExcel.clicked.connect(lambda: self.ExportaExcel(mostrar=True))
        self.view.btnEnviaCorreo.clicked.connect(self.EnviaCorreo)
        self.view.controles['desdeptovta'].editingFinished.connect(self.onEditinFinished)

    def ExportaExcel(self, mostrar=True):
        self.view.avance.setVisible(True)
        cArchivo = QFileDialog.getSaveFileName(caption="Guardar archivo", directory="", filter="*.XLSX")[0]
        if not cArchivo:
            return
        self.cArchivoGenerado = cArchivo
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
                worksheet.write(fila, 6, d.netoa if d.tipocomp.lado == 'D' else d.netoa * -1)
                worksheet.write(fila, 7, d.netob if d.tipocomp.lado == 'D' else d.netob * -1)
                worksheet.write(fila, 9, d.iva if d.tipocomp.lado == 'D' else d.iva * -1)
                worksheet.write(fila, 10, d.percepciondgr if d.tipocomp.lado == 'D' else d.percepciondgr * -1)
                worksheet.write(fila, 11, d.cae)
                worksheet.write(fila, 12, d.venccae.strftime('%d/%m/%Y') if d.venccae else '')
                deta = Detfact.select().where(Detfact.idcabfact == d.idcabfact)
                totserv = decimal.Decimal.from_float(0.)
                totprod = totserv
                op_exentas = 0
                for det in deta:
                    art = Articulo.get_by_id(det.idarticulo)
                    if art.concepto.strip():
                        if int(art.concepto.strip()) == FEv1.SERVICIOS:
                            totserv += det.precio * det.cantidad if d.tipocomp.lado == 'D' else \
                                det.precio * det.cantidad * -1
                        else:
                            totprod += det.precio * det.cantidad if d.tipocomp.lado == 'D' else \
                                det.precio * det.cantidad * -1
                    else:
                        totprod += det.precio * det.cantidad if d.tipocomp.lado == 'D' else \
                            det.precio * det.cantidad * -1
                    if det.montoiva == 0:
                        op_exentas += det.precio * det.cantidad
                worksheet.write(fila, 8, op_exentas)
                worksheet.write(fila, 13, totprod)
                worksheet.write(fila, 14, totserv)
                worksheet.write(fila, 15, '=sum(G{}:J{})'.format(fila+1, fila+1))
                fila += 1
        worksheet.write(fila, 6, '=sum(G{}:G{})'.format(2, fila))
        worksheet.write(fila, 7, '=sum(H{}:H{})'.format(2, fila))
        worksheet.write(fila, 8, '=sum(I{}:I{})'.format(2, fila))
        worksheet.write(fila, 9, '=sum(J{}:J{})'.format(2, fila))
        worksheet.write(fila, 10, '=sum(K{}:K{})'.format(2, fila))
        worksheet.write(fila, 13, '=sum(N{}:N{})'.format(2, fila))
        worksheet.write(fila, 14, '=sum(O{}:O{})'.format(2, fila))
        worksheet.write(fila, 15, '=sum(P{}:P{})'.format(2, fila))
        workbook.close()
        self.view.avance.setVisible(False)
        if mostrar:
            AbrirArchivo(cArchivo)

    def onEditinFinished(self):
        print(str(self.view.controles['desdeptovta'].text()).zfill(4))
        self.view.controles['desdeptovta'].setText(str(self.view.controles['desdeptovta'].text()).zfill(4))

    def EstablecerOrden(self):
        self.view.controles['desdeptovta'].proximoWidget = self.view.controles['hastaptovta']
        self.view.controles['hastaptovta'].proximoWidget = self.view.lineDesdeFecha
        self.view.lineDesdeFecha.proximoWidget = self.view.lineHastaFecha

    @inicializar_y_capturar_excepciones
    def EnviaCorreo(self, *args, **kwargs):

        self.ExportaExcel(mostrar=False)

        if not self.cArchivoGenerado:
            return
        email_contador = LeerIni('email_contador')
        text, ok = QInputDialog.getText(self.view, 'Sistema', 'Ingrese el mail destinatario:',
                                        text=email_contador if email_contador else '')
        if ok:
            GrabarIni(clave='email_contador', key='param', valor=str(text))
            destinatario = str(text).strip()
            archivo = self.cArchivoGenerado

            mensaje = "Enviado desde mi Software de Gestion desarrollado por http://www.servinlgsm.com.ar \n\n" \
                      "No responder este email"
            motivo = "Se envia informe de ventas de {}".format(LeerIni(clave='empresa', key='FACTURA'))
            servidor = ParamSist.ObtenerParametro("SERVER_SMTP")
            clave = ParamSist.ObtenerParametro("CLAVE_SMTP")
            usuario = ParamSist.ObtenerParametro("USUARIO_SMTP")
            puerto = ParamSist.ObtenerParametro("PUERTO_SMTP") or 587
            responder=ParamSist.ObtenerParametro("RESPONDER")
            # envia_correo(from_address='', to_address='', message='', subject='', password_email='', to_cc='',
            #              smtp='', smtp_port=587, files=''):
            ok = envia_correo(from_address=responder, to_address=destinatario, message=mensaje, subject=motivo,
                         password_email=clave, smtp_port=puerto, smtp_server=servidor, files=archivo)
            if not ok:
                Ventanas.showAlert("Sistema", "Ha ocurrido un error al enviar el correo")
            else:
                Ventanas.showAlert("Sistema", "Archivo de ventas enviado correctamente")