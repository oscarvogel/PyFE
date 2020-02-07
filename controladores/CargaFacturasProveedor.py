# coding=utf-8
import os

from PyQt5.QtCore import Qt

from controladores.ConstatacionComprobantes import PDFConstatatacion
from controladores.ControladorBase import ControladorBase
from controladores.PadronAfip import PadronAfip
from controladores.WSConstComp import WSConstComp
from libs import Ventanas
from libs.Utiles import LeerIni, inicializar_y_capturar_excepciones, FechaMysql, AbrirArchivo
from modelos.CabFacProv import CabFactProv
from modelos.DetFactProv import DetFactProv
from modelos.PercepcionesDGR import PercepDGR
from modelos.Proveedores import Proveedor
from modelos.Provincias import Provincia
from vistas.Busqueda import UiBusqueda
from vistas.CargaFacturasProveedor import CargaFacturaProveedorView, PercepDGRView


class CargaFacturaProveedorController(ControladorBase):

    LanzarExcepciones = False
    cbte_modo = ''  # modalidad de emision: CAI, CAE, CAEA
    cuit_emisor = ''  # proveedor
    pto_vta = ''  # punto de venta habilitado en AFIP
    cbte_tipo = ''  # 1: factura A (ver tabla de parametros)
    cbte_nro = ''  # numero de factura
    cbte_fch = ''  # fecha en formato aaaammdd
    cod_autorizacion = '' # numero de CAI, CAE o CAEA
    imp_total = "0"  # importe total
    doc_tipo_receptor = ""  # CUIT (obligatorio Facturas A o M)
    doc_nro_receptor = ""  # numero de CUIT del cliente
    estado = 'A' #estado del comprobante
    obs = '' #observaciones
    ventana = None #ventana de carga de percepciones de DGR

    def __init__(self):
        super(CargaFacturaProveedorController, self).__init__()
        self.view = CargaFacturaProveedorView()
        self.conectarWidgets()
        self.EstablecerOrden()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.textFactura.lineEditPtoVta.editingFinished.connect(self.ValidaFactura)
        self.view.textFactura.lineEditNumero.editingFinished.connect(self.ValidaFactura)
        #self.view.gridDatos.itemChanged.connect(self.SumaTodo)
        self.view.gridDatos.currentItemChanged.connect(self.SumaTodo)
        self.view.btnGrabar.clicked.connect(self.onClickBtnGrabar)
        self.view.textPercepcionDGR.editingFinished.connect(self.SumaTodo)
        self.view.textNoGravado.editingFinished.connect(self.SumaTodo)
        self.view.textPercepcionIVA.editingFinished.connect(self.SumaTodo)
        self.view.textExentos.editingFinished.connect(self.SumaTodo)
        self.view.btnConstatacion.clicked.connect(self.onClickBtnConstata)
        self.view.btnPercepDGR.clicked.connect(self.onClickBtnPercepDGR)

    def SumaTodo(self):
        neto = 0.
        iva = 0.
        total = 0.

        self.view.btnGrabar.setEnabled(True)
        self.view.btnConstatacion.setEnabled(True)
        self.view.btnPercepDGR.setEnabled(True)
        for row in range(self.view.gridDatos.rowCount()):
            cantidad = float(self.view.gridDatos.ObtenerItem(fila=row, col='Cantidad'))
            netorenglon = float(self.view.gridDatos.ObtenerItem(fila=row, col='Neto'))
            ivarenglon = float(self.view.gridDatos.ObtenerItem(fila=row, col='IVA'))

            total = netorenglon * cantidad
            iva += total * ivarenglon / 100.
            neto += total
            self.view.gridDatos.ModificaItem(fila=row, col='Total', valor=total)

        total += neto + iva + self.view.textExentos.value() + \
            self.view.textPercepcionIVA.value() + \
            self.view.textNoGravado.value() + \
            self.view.textPercepcionDGR.value() + \
            self.view.textInternos.value()

        self.view.textIVA.setText(str(round(iva, 3)))
        self.view.textNeto.setText(str(round(neto, 3)))
        self.view.textTotal.setText(str(round(total, 3)))

    @inicializar_y_capturar_excepciones
    def onClickBtnGrabar(self, *args, **kwargs):
        if not self.ValidaFactura(): #si ya fue cargada la factura no permite que se cargue de nuevo
            return
        cab = CabFactProv()
        cab.fecha = self.view.fechaCarga.date().toPyDate()
        cab.fechaem = self.view.fechaEmision.date().toPyDate()
        cab.idproveedor = self.view.textProveedor.text()
        cab.tipocomp = self.view.textTipoComp.text()
        cab.numero = self.view.textFactura.numero
        cab.neto = self.view.textNeto.value()
        cab.iva = self.view.textIVA.value()
        cab.percepciondgr = self.view.textPercepcionDGR.value()
        cab.percepcioniva = self.view.textPercepcionIVA.value()
        cab.impuestos = self.view.textInternos.value()
        cab.exentos = self.view.textExentos.value()
        cab.nogravados = self.view.textNoGravado.value()
        cab.cai = str(self.view.textCAE.text())
        cab.modocpte = self.view.cboModoCpte.valor()
        cab.periodo = self.view.periodo.cPeriodo
        cab.save()

        for row in range(self.view.gridDatos.rowCount()):
            iva = float(self.view.gridDatos.ObtenerItem(fila=row, col='IVA'))
            neto = float(self.view.gridDatos.ObtenerItem(fila=row, col='Neto'))
            ctrocosto = int(self.view.gridDatos.ObtenerItem(fila=row, col='Ctro Costos'))
            cantidad = float(self.view.gridDatos.ObtenerItem(fila=row, col='Cantidad'))
            detalle = self.view.gridDatos.ObtenerItem(fila=row, col='Detalle')

            if cantidad != 0:
                det = DetFactProv()
                det.idpcabecera = cab.idpcabfact
                det.idctrocosto = ctrocosto
                det.cantidad = cantidad
                det.iva = iva
                det.neto = neto
                det.detalle = detalle
                det.save()

        if self.ventana:
            for row in range(self.ventana.view.gridPercepDGR.rowCount()):
                codjur = self.ventana.view.gridPercepDGR.ObtenerItem(fila=row, col='Codigo')
                monto = float(self.ventana.view.gridPercepDGR.ObtenerItem(fila=row, col='Monto'))
                if int(codjur) != 0:
                    try:
                        prov = Provincia.get_by_id(codjur)
                        percep = PercepDGR()
                        percep.codjur = codjur
                        percep.monto = monto
                        percep.idpcabecera = cab.idpcabfact
                        percep.save()

                    except Provincia.DoesNotExist:
                        Ventanas.showAlert(LeerIni('nombre_sistema'),
                                           "Codigo de jurisdiccion no existente {}".format(codjur))

        Ventanas.showAlert(LeerIni('nombre_sistema'), "Factura grabada correctamente")
        self.view.Cerrar()

    def EstablecerOrden(self):
        self.view.textProveedor.proximoWidget = self.view.textTipoComp
        self.view.textTipoComp.proximoWidget = self.view.textFactura.lineEditPtoVta
        self.view.textFactura.lineEditNumero.proximoWidget = self.view.fechaCarga
        self.view.fechaCarga.proximoWidget = self.view.fechaEmision
        self.view.fechaEmision.proximoWidget = self.view.periodo.lineEditMes
        self.view.periodo.lineEditAnio.proximoWidget = self.view.cboModoCpte
        self.view.cboModoCpte.proximoWidget = self.view.textCAE
        self.view.textCAE.proximoWidget = self.view.gridDatos
        self.view.textExentos.proximoWidget = self.view.textNoGravado
        self.view.textNoGravado.proximoWidget = self.view.textPercepcionDGR
        self.view.textPercepcionDGR.proximoWidget = self.view.textPercepcionIVA

    def onClickBtnConstata(self):

        WSCDC = WSConstComp()

        self.cbte_modo = self.view.cboModoCpte.valor()

        if self.cbte_modo in ['CF']:
            Ventanas.showAlert(LeerIni('nombre_sistema'), "No se puede constatar facturas emitidas con controlador fiscal")
        proveedor = Proveedor.get_by_id(self.view.textProveedor.text())
        self.cuit_emisor = proveedor.cuit.replace("-", "")  # proveedor
        self.pto_vta = str(self.view.textFactura.lineEditPtoVta.text())  # punto de venta habilitado en AFIP
        self.cbte_tipo = int(self.view.textTipoComp.text())  # 1: factura A (ver tabla de parametros)
        self.cbte_nro = str(self.view.textFactura.lineEditNumero.text())  # numero de factura
        self.cbte_fch = FechaMysql(self.view.fechaEmision.date().toPyDate())  # fecha en formato aaaammdd
        self.cod_autorizacion = str(self.view.textCAE.text())  # numero de CAI, CAE o CAEA
        # if self.cbte_modo == 'CAI':
        #     self.imp_total = "0"  # importe total
        #     self.doc_tipo_receptor = ""  # CUIT (obligatorio Facturas A o M)
        #     self.doc_nro_receptor = ""  # numero de CUIT del cliente
        # else:
        self.imp_total = str(self.view.textTotal.text())  # importe total
        self.doc_tipo_receptor = "80"  # CUIT (obligatorio Facturas A o M)
        self.doc_nro_receptor = LeerIni(clave='cuit', key='WSFEv1')  # numero de CUIT del cliente

        ok = WSCDC.Comprobar(cbte_modo=self.cbte_modo, cuit_emisor=self.cuit_emisor,
                             pto_vta=self.pto_vta, cbte_tipo=self.cbte_tipo,
                             cbte_nro=self.cbte_nro, cbte_fch=self.cbte_fch,
                             imp_total=self.imp_total, cod_autorizacion=self.cod_autorizacion,
                             doc_tipo_receptor=self.doc_tipo_receptor, doc_nro_receptor=self.doc_nro_receptor)

        if WSCDC.Resultado == "R":
            detalle = "Rechazado"
        elif WSCDC.Resultado == "A":
            detalle = "Aprobado"
        else:
            detalle = "Observado"
        self.estado = detalle
        self.obs = WSCDC.Obs.encode('utf-8')

        detalle += WSCDC.Obs
        if WSCDC.Resultado == "R":
            detalle = WSCDC.ErrMsg
        self.Imprimir()

    def Imprimir(self):
        pdf = PDFConstatatacion()
        pdf.estado = self.estado
        pdf.obs = self.obs
        pdf.cbte_modo = self.cbte_modo
        pdf.add_page()
        self.cbte_fch = self.view.fechaEmision.date().toPyDate().strftime("%d/%m/%Y")
        pdf.imprimedetalle(cbte_modo=self.cbte_modo, cuit_emisor=self.cuit_emisor,
                           pto_vta=self.pto_vta, cbte_tipo=self.cbte_tipo,
                           cbte_nro=self.cbte_nro, cbte_fch=self.cbte_fch,
                           imp_total=self.imp_total, cod_autorizacion=self.cod_autorizacion,
                           doc_tipo_receptor=self.doc_tipo_receptor, doc_nro_receptor=self.doc_nro_receptor)
        if not os.path.isdir("tmp"):
            os.mkdir("tmp")
        filename = LeerIni('iniciosistema') + "tmp/constatacion{}.pdf".format(self.cuit_emisor.strip())
        pdf.output(name=filename)
        AbrirArchivo(filename)

        padron = PadronAfip()
        cuit = self.doc_nro_receptor.replace("-", "")
        filename = "tmp/constancia{}.pdf".format(cuit)
        padron.DescargarConstancia(cuit=cuit, filename=filename)

    def ValidaFactura(self):
        try:
            data = CabFactProv.select().where(CabFactProv.idproveedor == self.view.textProveedor.value(),
                                              CabFactProv.tipocomp == self.view.textTipoComp.value(),
                                              CabFactProv.numero == self.view.textFactura.numero).get()
            if data:
                Ventanas.showAlert(LeerIni("nombre_sistema"), "Error factura ya cargada al sistema")
                self.view.btnGrabar.setEnabled(False)
                retorno = False
            else:
                self.view.btnGrabar.setEnabled(True)
                retorno = True
        except CabFactProv.DoesNotExist:
            retorno = True

        return retorno

    def onClickBtnPercepDGR(self):
        self.ventana = PercepDGRController()
        self.ventana.exec_()
        percep = 0.
        for row in range(self.ventana.view.gridPercepDGR.rowCount()):
            percep += float(self.ventana.view.gridPercepDGR.ObtenerItem(fila=row, col='Monto'))
        self.view.textPercepcionDGR.setText(str(round(percep, 2)))
        self.SumaTodo()

class PercepDGRController(ControladorBase):

    def __init__(self):
        super(PercepDGRController, self).__init__()
        self.view = PercepDGRView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrarDGR.clicked.connect(self.view.Cerrar)
        self.view.gridPercepDGR.keyPressed.connect(self.onKeyGridPercepDGR)

    def onKeyGridPercepDGR(self, key):
        col = self.view.gridPercepDGR.currentColumn()
        fila = self.view.gridPercepDGR.currentRow()

        if key == Qt.Key_F2 and col == 0:
            _ventana = UiBusqueda()
            _ventana.modelo = Provincia
            _ventana.cOrden = Provincia.nombre
            _ventana.campoBusqueda = _ventana.cOrden
            _ventana.campoRetorno = Provincia.codjur
            _ventana.campoRetornoDetalle = Provincia.nombre
            _ventana.campos = ['codjur', 'nombre']
            _ventana.CargaDatos()
            _ventana.exec_()
            if _ventana.lRetval:
                self.view.gridPercepDGR.ModificaItem(valor=_ventana.ValorRetorno,
                                                     col=0, fila=fila)
                self.view.gridPercepDGR.ModificaItem(valor=_ventana.campoRetornoDetalle,
                                                     col='Nombre', fila=fila)
            self.view.gridPercepDGR.setFocus()

        if key in [Qt.Key_Tab, Qt.Key_Enter, Qt.Key_Return] and col == 0:
            try:
                prov = Provincia.get_by_id(
                    int(self.view.gridPercepDGR.ObtenerItem(fila=fila, col=col))
                )
                self.view.gridPercepDGR.ModificaItem(valor=prov.nombre, fila=fila, col='Nombre')
            except Provincia.DoesNotExist:
                #Ventanas.showAlert(LeerIni("nombre_sistema"), "Error codigo de jurisdiccion no encontrado")
                pass