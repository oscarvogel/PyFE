# coding=utf-8
import decimal
import os

import peewee
from PyQt5.QtCore import Qt
from os.path import join

from controladores.ControladorBase import ControladorBase
from controladores.FCE import WsFECred
from controladores.FE import FEv1
from libs import Ventanas, Constantes
from libs.Utiles import LeerIni, validar_cuit, FechaMysql, ubicacion_sistema, inicializar_y_capturar_excepciones, \
    DeCodifica, imagen
from modelos.Articulos import Articulo
from modelos.Cabfact import Cabfact
from modelos.Clientes import Cliente
from modelos.CpbteRelacionado import CpbteRel
from modelos.Detfact import Detfact
from modelos.Impuestos import Impuesto
from modelos.ParametrosSistema import ParamSist
from modelos.Tipoiva import Tipoiva
from pyafipws.pyfepdf import FEPDF
from vistas.Busqueda import UiBusqueda

from vistas.Facturas import FacturaView


class FacturaController(ControladorBase):

    cliente = None #modelo cliente
    tipo_cpte = 1 #tipo de comprobante a facturar
    netos = {
        0:0,
        10.5:0,
        21:0
    }
    concepto = '1' #concepto de factura electronica (productos, servicios o ambos)
    facturaGenerada = ''
    informo = False  # indica si ya informo monto obligado de FCE
    decimales = 3  # indica la cantidad de decimales para el redondeo

    def __init__(self):
        super(FacturaController, self).__init__()
        self.view = FacturaView()
        self.conectarWidgets()
        self.EstablecerOrden()
        # for x in range(15):
        #     item = ['']
        #     self.view.gridFactura.AgregaItem(item)

    def conectarWidgets(self):
        self.view.validaCliente.editingFinished.connect(self.CargaDatosCliente)
        self.view.checkBoxServicios.stateChanged.connect(self.HabilitaVencimientos)
        self.view.btnCerrarFormulario.clicked.connect(self.view.Cerrar)
        self.view.botonAgregaArt.clicked.connect(self.AgregaArt)
        self.view.gridFactura.keyPressed.connect(self.onKeyPressedGridFactura)
        self.view.btnGrabarFactura.clicked.connect(self.GrabaFactura)
        self.view.lineEditDocumento.editingFinished.connect(self.onEditingFinishedDocumento)
        self.view.botonBorrarArt.clicked.connect(self.onClickbotonBorraArt)
        self.view.cboComprobante.currentIndexChanged.connect(self.onCurrentIndexChanged)

    @inicializar_y_capturar_excepciones
    def CargaDatosCliente(self, *args, **kwargs):
        if not self.view.validaCliente.text():
            return
        try:
            self.cliente = Cliente.select().where(Cliente.idcliente == self.view.validaCliente.text()).get()
            cliente = self.cliente
            self.view.lineEditDomicilio.setText(cliente.domicilio)
            if cliente.tiporesp.idtiporesp in [1, 2, 4]: #monotributo o resp inscripto
                self.view.lineEditDocumento.setText(cliente.cuit.replace('-',''))
                self.view.lineEditDocumento.setInputMask("99-99999999-9")
                if int(LeerIni(clave='cat_iva', key='WSFEv1')) == 1:
                    wsfecred = WsFECred()
                    obligado, minimo = wsfecred.ConsultarMontoObligado(cliente.cuit.replace('-',''), LeerIni('cuit', key='WSFEv1'))
                    if obligado and not self.informo:
                        Ventanas.showAlert("Sistema", "Se debe emitir FCE al cliente desde un monto de {}".format(minimo))
                self.informo = True
            else:
                self.view.lineEditDocumento.setText(str(cliente.dni))
                self.view.lineEditDocumento.setInputMask("99999999")
            if int(LeerIni(clave='cat_iva', key='WSFEv1')) == 1: #si es Resp insc el contribuyente veo si teiene que emitira A o B
                if cliente.tiporesp.idtiporesp == 2: #resp inscripto
                    self.view.cboComprobante.setText('Factura A')
                else:
                    self.view.cboComprobante.setText('Factura B')
            else:
                self.view.cboComprobante.setText('Factura C')

            self.view.cboTipoIVA.setText(cliente.tiporesp.nombre)
            self.ObtieneNumeroFactura()
        except Cliente.DoesNotExist:
            Ventanas.showAlert("Sistema", "Cliente no encontrado en el sistema")

    def ObtieneNumeroFactura(self):
        self.view.layoutFactura.lineEditPtoVta.setText(LeerIni(clave='pto_vta', key='WSFEv1').zfill(4))
        # tipos = Tipocomprobantes.ComboTipoComp(tiporesp=int(LeerIni(clave='cat_iva', key='WSFEv1')))
        # tipo_cpte = [k for (k, v) in tipos.valores.iteritems() if v == self.view.cboComprobante.text()][0]
        tipo_cpte = self.view.cboComprobante.text()
        nro = FEv1().UltimoComprobante(tipo=tipo_cpte,
                                       ptovta=self.view.layoutFactura.lineEditPtoVta.text())
        self.tipo_cpte = tipo_cpte
        self.view.layoutFactura.lineEditNumero.setText(str(int(nro)+1).zfill(8))
        self.SumaTodo()

    def HabilitaVencimientos(self):
        self.view.fechaDesde.setEnabled(self.view.checkBoxServicios.isChecked())
        self.view.fechaHasta.setEnabled(self.view.checkBoxServicios.isChecked())

    def AgregaArt(self):
        self.view.gridFactura.setRowCount(self.view.gridFactura.rowCount() + 1)
        self.view.gridFactura.ModificaItem(valor=1, fila=self.view.gridFactura.rowCount() + 1, col='Cant.')
        self.view.gridFactura.ModificaItem(valor=0, fila=self.view.gridFactura.rowCount() - 1, col='Unitario')
        self.view.gridFactura.ModificaItem(valor=21, fila=self.view.gridFactura.rowCount() - 1, col='IVA')
        self.SumaTodo()

    def onKeyPressedGridFactura(self, key):
        col = self.view.gridFactura.currentColumn()
        row = self.view.gridFactura.currentRow()
        if key == Qt.Key_F2 and col == 1:
            _ventana = UiBusqueda()
            _ventana.modelo = Articulo
            _ventana.cOrden = Articulo.nombre
            _ventana.campoBusqueda = _ventana.cOrden
            _ventana.campoRetorno = Articulo.idarticulo
            _ventana.campoRetornoDetalle = Articulo.nombre
            _ventana.campos = ['idarticulo', 'nombre', 'preciopub']
            _ventana.CargaDatos()
            _ventana.exec_()
            if _ventana.lRetval:
                self.view.gridFactura.ModificaItem(valor=_ventana.ValorRetorno,
                                                   fila=self.view.gridFactura.currentRow(),
                                                   col=1)
                self.view.gridFactura.ModificaItem(valor=_ventana.campoRetornoDetalle,
                                                   fila=self.view.gridFactura.currentRow(),
                                                   col=2)
                art = Articulo.get_by_id(_ventana.ValorRetorno)
                self.view.gridFactura.ModificaItem(valor=art.preciopub,
                                                   fila=self.view.gridFactura.currentRow(),
                                                   col='Unitario')
            self.view.gridFactura.setFocus()
        if key in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab] and col == 1:
            if float(self.view.gridFactura.ObtenerItem(fila=row, col='Unitario')) == 0:
                codigo = self.view.gridFactura.ObtenerItem(fila=row, col=1)
                if codigo:
                    art = Articulo.get_by_id(codigo)
                    self.view.gridFactura.ModificaItem(valor=art.preciopub,
                                               fila=self.view.gridFactura.currentRow(),
                                               col='Unitario')

        if key in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab]:
            if col < self.view.gridFactura.columnCount():
                self.view.gridFactura.setCurrentCell(row, col + 1)
            else:
                self.view.gridFactura.setCurrentCell(row + 1, 0)

        if key == Qt.Key_Down and row + 1 == self.view.gridFactura.rowCount():
            self.AgregaArt()

        self.SumaTodo()

    def SumaTodo(self):
        totalgral = 0.
        ivagral = 0.
        dgrgral = 0.
        subtotal = 0.
        self.netos = {
            0: 0,
            10.5: 0,
            21: 0
        }
        if not self.cliente:
            return
        try:
            impuesto = float(self.cliente.percepcion.porcentaje)
        except Impuesto.DoesNotExist:
            impuesto = decimal.Decimal.from_float(0.)
        for x in range(self.view.gridFactura.rowCount()):
            art = None
            if int(LeerIni(clave='cat_iva', key='WSFEv1')) == 6:
                self.view.gridFactura.ModificaItem(valor=21, fila=x, col='IVA')
            detalle = self.view.gridFactura.ObtenerItem(fila=x, col='Detalle')
            unitario = float(self.view.gridFactura.ObtenerItem(fila=x, col='Unitario'))
            if not detalle or unitario == 0:
                codigo = self.view.gridFactura.ObtenerItem(fila=x, col='Codigo')
                try:
                    art = Articulo.get_by_id(codigo)
                except Articulo.DoesNotExist:
                    try:
                        art = Articulo.get(Articulo.codbarra == codigo)
                    except Articulo.DoesNotExist:
                        pass
                if art:
                    if not detalle:
                        self.view.gridFactura.ModificaItem(valor=art.nombre, fila=x, col='Detalle')
                    if unitario == 0:
                        self.view.gridFactura.ModificaItem(valor=art.preciopub, fila=x, col='Unitario')
            cantidad = self.view.gridFactura.ObtenerItem(fila=x, col='Cant.')
            #self.view.gridFactura.ModificaItem(valor=cantidad, fila=x, col='Cant.')
            unitario = float(self.view.gridFactura.ObtenerItem(fila=x, col='Unitario'))
            iva = float(self.view.gridFactura.ObtenerItem(fila=x, col='IVA'))
            total = float(cantidad) * float(unitario)
            if int(LeerIni(clave='cat_iva',
                           key='WSFEv1')) == 1:  # si es Resp insc el contribuyente
                if self.tipo_cpte in [6, 7, 8]:
                    neto = round(total / ((iva / 100) + 1), 3)
                    try:
                        self.netos[iva] += neto
                    except KeyError:
                        pass
                    ivagral += (total - neto)
                    totalgral += neto
                else:
                    ivagral += total * iva / 100
                    totalgral += total
                    try:
                        self.netos[iva] += total
                    except KeyError:
                        pass
            else:
                try:
                    self.netos[iva] += total
                except KeyError:
                    pass
                totalgral += total

            # if int(LeerIni(clave='cat_iva',
            #                key='WSFEv1')) == 1:  # si es Resp insc el contribuyente
            #     ivagral += total * iva / 100
            # totalgral += total
            subtotal += total

            self.view.gridFactura.ModificaItem(valor=total, fila=x, col='SubTotal')


        if int(LeerIni(clave='cat_iva',
                       key='WSFEv1')) == 1:  # si es Resp insc el contribuyente
            dgrgral = totalgral * impuesto / 100

        if dgrgral > 0:
            row = self.view.gridAlicuotasTributos.currentRow()
            if self.view.gridAlicuotasTributos.rowCount() == 0:
                self.view.gridAlicuotasTributos.AgregaItem(items=[
                    self.cliente.percepcion.porcentaje,
                    totalgral, dgrgral
                ])
            else:
                self.view.gridAlicuotasTributos.ModificaItem(valor=totalgral,
                                                            fila=row, col='Base Imponible')
                self.view.gridAlicuotasTributos.ModificaItem(valor=totalgral,
                                                            fila=row, col='Importe')
        else:
            self.view.gridAlicuotasTributos.setRowCount(0)


        self.view.textSubTotal.setText(str(round(subtotal, self.decimales)))
        self.view.lineEditTributos.setText(str(round(dgrgral, self.decimales)))
        self.view.lineEditTotalIVA.setText(str(round(ivagral, self.decimales)))
        self.view.lineEditTotal.setText(str(round(totalgral + ivagral + dgrgral, 2)))

    def GrabaFactura(self):
        if not self.Validacion():
            return
        self.view.btnGrabarFactura.setEnabled(False)
        self.SumaTodo()
        ok = self.CreaFE()
        if ok:
            print("Graba factura")
            self.GrabaFE()
        self.view.Cerrar()

    @inicializar_y_capturar_excepciones
    def CreaFE(self, *args, **kwargs):
        ok = True
        self.ObtieneNumeroFactura()
        wsfev1 = FEv1()
        ta = wsfev1.Autenticar()
        #Setear tocken y sign de autorizacion(ticket de accesso, pasos previos)
        wsfev1.SetTicketAcceso(ta)
        wsfev1.Cuit = LeerIni(clave='cuit', key='WSFEv1') #CUIT del emisor (debe estar registrado en la AFIP)
        #Conectar al Servicio Web de Facturacion
        #Produccion usar: *-- ok = WSFE.Conectar("", "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL") & & Producción
        if LeerIni(clave='homo') == "S":
            ok = wsfev1.Conectar("") #Homologacion
        else:
            cacert = LeerIni(clave='cacert', key='WSFEv1')
            ok = wsfev1.Conectar("", LeerIni(clave="url_prod", key="WSFEv1"), cacert=cacert)

        if self.view.checkBoxServicios.isChecked() \
            and self.view.checkBoxProductos.isChecked(): #si es productoso y servicios
            concepto = wsfev1.PRODUCTOYSERVICIOS
        elif self.view.checkBoxServicios.isChecked():
            concepto = wsfev1.SERVICIOS
        else:
            concepto = wsfev1.PRODUCTOS

        self.concepto = concepto
        if self.cliente.tiporesp.idtiporesp == 3: #consumidor final
            if str(self.view.lineEditDocumento.text()).strip() in ['0', '']:
                tipo_doc = 99
            else:
                tipo_doc = 96
        else:
            tipo_doc = 80

        punto_vta = int(self.view.layoutFactura.lineEditPtoVta.value())
        tipo_cbte = self.tipo_cpte
        nro_doc = str(self.view.lineEditDocumento.text()).strip().replace('-','')
        cbt_desde = int(self.view.layoutFactura.lineEditNumero.value())
        cbt_hasta = cbt_desde
        imp_total = self.view.lineEditTotal.text()
        imp_tot_conc = "0.00"
        if int(LeerIni(clave='cat_iva',
                       key='WSFEv1')) == 1:  # si es Resp insc el contribuyente
            imp_neto = str(round(float(self.view.lineEditTotal.text()) - \
                float(self.view.lineEditTributos.text()) - \
                float(self.view.lineEditTotalIVA.text()), 2))
        else:
            imp_neto = str(round(float(self.view.lineEditTotal.text()),2))
        imp_iva = str(round(float(self.view.lineEditTotalIVA.text()),2))
        imp_trib = str(round(float(self.view.lineEditTributos.text()),2))
        impto_liq_rni = "0.00"
        imp_op_ex = "0.00"
        fecha_cbte = self.view.lineEditFecha.getFechaSql()
        #Fechas del periodo del servicio facturado(solo siconcepto > 1)
        if concepto in [wsfev1.SERVICIOS, wsfev1.PRODUCTOYSERVICIOS]:
            fecha_serv_desde = self.view.fechaDesde.getFechaSql()
            fecha_serv_hasta = self.view.fechaHasta.getFechaSql()
            fecha_venc_pago = self.view.lineEditFecha.getFechaSql()
        else:
            fecha_serv_desde = ""
            fecha_serv_hasta = ""
            fecha_venc_pago = ""
        moneda_id = "PES"
        moneda_ctz = "1.000"

        if self.tipo_cpte in Constantes.COMPROBANTES_FCE: #FCE
            fecha_venc_pago = self.view.lineEditFecha.getFechaSql()
        #Llamo al WebService de Autorizacion para obtener el CAE
        ok = wsfev1.CrearFactura(concepto, tipo_doc, nro_doc, tipo_cbte, punto_vta,
                cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
                imp_iva, imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
                fecha_serv_desde, fecha_serv_hasta,
                moneda_id, moneda_ctz)

        # Agregar comprobantes asociados(si es una NC / ND):
        if self.tipo_cpte in [3, 8, 13]:
        # if str(self.view.cboComprobante.text()).find('credito'):
            tipo = tipo_cbte
            pto_vta = self.view.layoutCpbteRelacionado.lineEditPtoVta.text()
            nro = self.view.layoutCpbteRelacionado.lineEditNumero.text()
            wsfev1.AgregarCmpAsoc(tipo, pto_vta, nro)

        if self.tipo_cpte in Constantes.COMPROBANTES_FCE:
            #homologacion
            wsfev1.AgregarOpcional(2101, LeerIni("CBUFCE", key='FACTURA')) #CBU
            wsfev1.AgregarOpcional(2102, LeerIni("ALIASFCE", key='FACTURA')) # alias

            #cargo los remitos relacionados, por ahora cargo la fecha actual
            #habria q ver de hacer una tabla de remitos
            if self.view.layoutCpbteRelacionado.numero:
                tipo_cbte_rem = 91
                pto_vta_rem = self.view.layoutCpbteRelacionado.lineEditPtoVta.text()
                nro_comp_rem = self.view.layoutCpbteRelacionado.lineEditNumero.text()
                wsfev1.AgregarCmpAsoc(tipo_cbte_rem, pto_vta_rem, nro_comp_rem,
                                      LeerIni(clave='cat_iva', key='cuit'), FechaMysql())

        if round(float(self.view.lineEditTributos.text()), 3) != 0:
            idimp = wsfev1.ID_IMP_PCIAL
            detalle = self.cliente.percepcion.detalle
            base_imp = round(float(self.view.lineEditTotal.text()) - \
                float(self.view.lineEditTributos.text()) - \
                float(self.view.lineEditTotalIVA.text()),2)
            alicuota = self.cliente.percepcion.porcentaje
            importe = str(round(float(self.view.lineEditTributos.text()),2))
            wsfev1.AgregarTributo(tributo_id=idimp, desc=detalle, base_imp=base_imp,
                                  alic=alicuota, importe=importe)

        if int(LeerIni(clave='cat_iva', key='WSFEv1')) == 1: #◘unicamente si es RI se informa los IVA
            #agrego todos los iva
            for k,v in self.netos.items():
                if v != 0:
                    id = FEv1().TASA_IVA[str(float(k))]
                    base_imp = round(v,2)
                    iva = round(k,2)
                    importe = round(base_imp * iva / 100,2)
                    ok = wsfev1.AgregarIva(id, base_imp, importe)

        #SolicitoCAE:
        cae = wsfev1.CAESolicitar()
        if wsfev1.ErrMsg:
            Ventanas.showAlert("Sistema", "ERROR {}".format(DeCodifica(wsfev1.ErrMsg)))
            ok = False
        else:
            if wsfev1.Resultado == 'R':
                Ventanas.showAlert("Sistema", "Motivo de rechazo {}".format(DeCodifica(wsfev1.Obs)))
                ok = False
            else:
                self.view.lineditCAE.setText(cae)
                self.view.lineEditResultado.setText(wsfev1.Resultado)
                self.view.fechaVencCAE.setFecha(wsfev1.Vencimiento, format="Ymd")
        return ok

    def onEditingFinishedDocumento(self):
        if self.cliente.tiporesp.idtiporesp != 3:
            if not validar_cuit(self.view.lineEditDocumento.text()):
                Ventanas.showAlert("Sistema", "ERROR: CUIT/CUIL no valido. Verifique!!!")

    @inicializar_y_capturar_excepciones
    def GrabaFE(self, *args, **kwargs):
        self.view.layoutFactura.AssignNumero()
        cabfact = Cabfact()
        cabfact.tipocomp = self.tipo_cpte
        cabfact.cliente = self.cliente.idcliente
        cabfact.fecha = self.view.lineEditFecha.date().toPyDate()
        cabfact.numero = self.view.layoutFactura.numero
        cabfact.neto = sum([i for i in self.netos.values()])
        cabfact.netoa = self.netos[21]
        cabfact.netob = self.netos[10.5]
        cabfact.iva = self.view.lineEditTotalIVA.value()
        cabfact.total = self.view.lineEditTotal.value()
        if self.view.cboFormaPago.text() == 'Contado':
            cabfact.saldo = 0.00
        else:
            cabfact.saldo = self.view.lineEditTotal.value()
        cabfact.tipoiva = self.cliente.tiporesp.idtiporesp
        cabfact.cajero = 1 #por defecto cajero
        cabfact.formapago = 1 if self.view.cboFormaPago.text() == 'Contado' else 2
        cabfact.percepciondgr = self.view.lineEditTributos.value()
        cabfact.nombre = self.view.lblNombreCliente.text()
        cabfact.domicilio = self.view.lineEditDomicilio.text()
        cabfact.cae = self.view.lineditCAE.text()
        cabfact.venccae = self.view.fechaVencCAE.date().toPyDate()
        cabfact.concepto = self.concepto
        cabfact.desde = self.view.fechaDesde.date().toPyDate()
        cabfact.hasta = self.view.fechaHasta.date().toPyDate()
        cabfact.save()

        for x in range(self.view.gridFactura.rowCount()):
            codigo = self.view.gridFactura.ObtenerItem(fila=x, col='Codigo')
            cantidad = float(self.view.gridFactura.ObtenerItem(fila=x, col='Cant.'))
            importe = float(self.view.gridFactura.ObtenerItem(fila=x, col='SubTotal'))
            iva = float(self.view.gridFactura.ObtenerItem(fila=x, col='IVA'))
            detalle = self.view.gridFactura.ObtenerItem(fila=x, col='Detalle')
            try:
                articulo = Articulo.get_by_id(codigo)
                detfact = Detfact()
                detfact.idcabfact = cabfact.idcabfact
                detfact.idarticulo = codigo
                detfact.cantidad = cantidad
                detfact.unidad = articulo.unidad
                detfact.costo = articulo.costo

                if LeerIni(clave='cat_iva', key='WSFEv1') == 1:
                    if self.tipo_cpte in [6,7,8]:
                        detfact.precio = importe / cantidad
                    else:
                        detfact.precio = (importe + importe * iva / 100) / cantidad
                else:
                    detfact.precio = importe / cantidad
                try:
                    ti = Tipoiva.get(Tipoiva.iva == iva)
                    detfact.tipoiva = ti.codigo
                except Tipoiva.DoesNotExist:
                    detfact.tipoiva = articulo.tipoiva.codigo
                if self.tipo_cpte in [6, 7, 8]:
                    detfact.montoiva = importe * iva / 100
                else:
                    neto = round(importe / ((iva / 100) + 1), 3)
                    detfact.montoiva = neto * iva / 100
                if self.view.lineEditTributos.value() > 0:
                    detfact.montodgr = importe * float(self.cliente.percepcion.porcentaje) / 100
                else:
                    detfact.montodgr = 0.00
                detfact.montomuni = 0.00
                detfact.descad = detalle
                detfact.detalle = detalle[:40]
                detfact.descuento = 0.00
                detfact.save()
            except peewee.DoesNotExist:
                pass
        # Agregar comprobantes asociados(si es una NC / ND):
        if str(self.view.cboComprobante.text()).find('credito'):
            cpbte = CpbteRel()
            cpbte.idcabfact = cabfact.idcabfact
            if self.tipo_cpte == 13:
                cpbte.idtipocpbte = 11
            else:
                if self.cliente.tiporesp.idtiporesp == 2:  # resp inscripto
                    cpbte.idtipocpbte = 1
                else:
                    cpbte.idtipocpbte = 6
            cpbte.numero = self.view.layoutCpbteRelacionado.numero
            cpbte.save()
        self.ImprimeFactura(idcabecera=cabfact.idcabfact)

    @inicializar_y_capturar_excepciones
    def ImprimeFactura(self, idcabecera = None, mostrar = True, *args, **kwargs):
        if not idcabecera:
            return
        cabfact = Cabfact().get_by_id(idcabecera)
        print("imprimir factura {}".format(cabfact.numero))
        pyfpdf = FEPDF()
        #cuit del emisor
        pyfpdf.CUIT = LeerIni(clave='cuit', key='WSFEv1')
        #establezco formatos (cantidad de decimales):
        pyfpdf.FmtCantidad = "0.4"
        pyfpdf.FmtPrecio = "0.2"
        #Datos del encabezado de la factura:
        tipo_cbte = cabfact.tipocomp.codigo
        punto_vta = cabfact.numero[:4]
        cbte_nro = cabfact.numero[-8:]
        fecha = FechaMysql(cabfact.fecha)
        concepto = cabfact.concepto
        #datos del cliente:
        tipo_doc = "80" if cabfact.cliente.tiporesp_id != 3 else "96"
        nro_doc = cabfact.cliente.cuit if cabfact.cliente.tiporesp_id != 3 else str(cabfact.cliente.dni)
        nombre_cliente = cabfact.nombre if cabfact.nombre != '' else cabfact.cliente.nombre
        domicilio_cliente = cabfact.domicilio

        #totales del comprobante:
        imp_total = cabfact.total
        imp_tot_conc = "0.00"
        imp_neto = cabfact.neto
        imp_iva = cabfact.iva
        imp_trib = cabfact.percepciondgr
        imp_op_ex = "0.00"
        imp_subtotal = cabfact.neto
        fecha_cbte = fecha
        fecha_venc_pago = fecha
        #Fechas del período del servicio facturado
        if int(cabfact.concepto or 1) in [FEv1().SERVICIOS, FEv1().PRODUCTOYSERVICIOS]:
            fecha_serv_desde = FechaMysql(cabfact.desde)
            fecha_serv_hasta = FechaMysql(cabfact.hasta)
        else:
            fecha_serv_hasta = None
            fecha_serv_desde = None

        moneda_id = "PES"
        moneda_ctz = "1.000"
        obs_generales = ""
        obs_comerciales = ""
        moneda_id = ""
        moneda_ctz = 1
        cae = cabfact.cae
        fecha_vto_cae = FechaMysql(cabfact.venccae)

        #Creo la factura(internamente en la interfaz)
        ok = pyfpdf.CrearFactura(concepto, tipo_doc, nro_doc, tipo_cbte, punto_vta,
                    cbte_nro, imp_total, imp_tot_conc, imp_neto,
                    imp_iva, imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
                    fecha_serv_desde, fecha_serv_hasta,
                    moneda_id, moneda_ctz, cae, fecha_vto_cae, "",
                    nombre_cliente, domicilio_cliente, 0)
        pyfpdf.EstablecerParametro("forma_pago", cabfact.formapago.detalle)
        pyfpdf.EstablecerParametro("custom-nro-cli", "[{}]".format(str(cabfact.cliente.idcliente).zfill(5)))
        pyfpdf.EstablecerParametro("localidad_cli", cabfact.cliente.localidad.nombre)
        pyfpdf.EstablecerParametro("provincia_cli", cabfact.cliente.localidad.provincia)
        pyfpdf.EstablecerParametro("iva_cli", cabfact.cliente.tiporesp.nombre)

        #Agregar comprobantes asociados(si es una NC / ND):
        if cabfact.tipocomp.codigo in [3, 8, 13]:
            cpbterel = CpbteRel().select().where(CpbteRel.idcabfact == cabfact.idcabfact)
            for cp in cpbterel:
                tipo = cp.idtipocpbte.codigo
                pto_vta = cp.numero[:4]
                nro = cp.numero[-8:]
                pyfpdf.AgregarCmpAsoc(tipo, pto_vta, nro)
        # if str(self.view.cboComprobante.text()).find('credito'):
        #     tipo = 19
        #     pto_vta = 2
        #     nro = 1234
        #     pyfepdf.AgregarCmpAsoc(tipo, pto_vta, nro)

        #Agrego subtotales de IVA(uno por alicuota)
        if cabfact.netoa != 0:
            iva_id = 5 #c�digo para al�cuota del 21 %
            base_imp = cabfact.netoa #importe neto sujeto a esta al�cuota
            importe = cabfact.netoa * 21 / 100 #importe liquidado de iva
            ok = pyfpdf.AgregarIva(iva_id, base_imp, importe)

        if cabfact.netob != 0:
            iva_id = 4  # c�digo para al�cuota del 10.5 %
            base_imp = cabfact.netob  # importe neto sujeto a esta al�cuota
            importe = cabfact.netob * 10.5 / 100  # importe liquidado de iva
            ok = pyfpdf.AgregarIva(iva_id, base_imp, importe)

        if cabfact.netoa == 0 and cabfact.netob == 0:
            iva_id = 3  # c�digo para al�cuota del 21 %
            base_imp = cabfact.netob  # importe neto sujeto a esta al�cuota
            importe = 0  # importe liquidado de iva
            ok = pyfpdf.AgregarIva(iva_id, base_imp, importe)

        if cabfact.percepciondgr != 0:
            #Agregar cada impuesto(por ej.IIBB, retenciones, percepciones, etc.):
            tributo_id = 99 #codigo para 99 - otros tributos
            Desc = cabfact.cliente.percepcion.detalle
            base_imp = cabfact.neto #importe sujeto a estetributo
            alic = cabfact.cliente.percepcion.porcentaje #alicuota(porcentaje) de estetributo
            importe = cabfact.percepciondgr #importe liquidado de este tributo
            ok = pyfpdf.AgregarTributo(tributo_id, Desc, base_imp, alic, importe)

        det = Detfact().select().where(Detfact.idcabfact == cabfact.idcabfact)
        for d in det:
            #Agrego detalles de cada item de la factura:
            u_mtx = 0 #unidades
            cod_mtx = "" #c�digo de barras
            codigo = d.idarticulo.idarticulo #codigo interno a imprimir(ej. "articulo")
            ds = d.descad.strip()
            qty = d.cantidad #cantidad
            umed = 7 #c�digo de unidad de medida(ej. 7 para"unidades")
            precio = d.precio #precio neto(A) o iva incluido(B)
            bonif = 0 #importe de descuentos
            iva_id = FEv1().TASA_IVA[str(float(d.tipoiva.iva))] #c�digopara al�cuota del 21 %
            imp_iva = d.montoiva #importe liquidado deiva
            importe = d.precio * d.cantidad  #importe total del item
            despacho = "" #numero de despacho de importaci�n
            dato_a = "" #primer dato adicional del item
            dato_b = ""
            dato_c = ""
            dato_d = ""
            dato_e = "" #ultimo dato adicionaldel item
            ok = pyfpdf.AgregarDetalleItem(u_mtx, cod_mtx, codigo, ds, qty, umed,
                        precio, bonif, iva_id, imp_iva, importe, despacho,
                        dato_a, dato_b, dato_c, dato_d, dato_e)

        #Agrego datos adicionales fijos:
        ok = pyfpdf.AgregarDato("logo", ubicacion_sistema() + "plantillas/logo.png")
        fondo = ParamSist.ObtenerParametro("FONDO_FACTURA")
        if fondo:
            x1 = ParamSist.ObtenerParametro("FONDO_FACTURA_X1") or 50
            y1 = ParamSist.ObtenerParametro("FONDO_FACTURA_Y1") or 117.1
            x2 = ParamSist.ObtenerParametro("FONDO_FACTURA_X2") or 150
            y2 = ParamSist.ObtenerParametro("FONDO_FACTURA_Y2") or 232.9
            pyfpdf.AgregarCampo("fondo_factura", 'I', x1, y1, x2, y2,
                              foreground=0x808080, priority=-1, text=imagen(fondo))
        ok = pyfpdf.AgregarDato("EMPRESA", "Razon social: {}".format(DeCodifica(LeerIni(clave='empresa', key='FACTURA'))))
        ok = pyfpdf.AgregarDato("MEMBRETE1", "Domicilio Comercial: {}".format(
            DeCodifica(LeerIni(clave='membrete1', key='FACTURA'))))
        ok = pyfpdf.AgregarDato("MEMBRETE2", DeCodifica(LeerIni(clave='membrete2', key='FACTURA')))
        ok = pyfpdf.AgregarDato("CUIT", 'CUIT: {}'.format(LeerIni(clave='cuit', key='WSFEv1')))
        ok = pyfpdf.AgregarDato("IIBB", LeerIni(clave='iibb', key='FACTURA'))
        ok = pyfpdf.AgregarDato("IVA", "Condicion frente al IVA: {}".format(LeerIni(clave='iva', key='FACTURA')))
        ok = pyfpdf.AgregarDato("INICIO", "Fecha inicio actividades: {}".format(LeerIni(clave='inicio', key='FACTURA')))

        if int(cabfact.tipocomp.codigo) in Constantes.COMPROBANTES_FCE: #si es una FCE
            pyfpdf.AgregarDato('CBUFCE', LeerIni('CBUFCE', key='FACTURA'))
            pyfpdf.AgregarDato('ALIASFCE', LeerIni('ALIASFCE', key='FACTURA'))
            pyfpdf.AgregarDato('nombre_condvta', Constantes.COND_VTA['T'])
            ok = pyfpdf.CargarFormato(ubicacion_sistema() + "/plantillas/factura-fce.csv")
        else:
            #Cargo el formato desde el archivo CSV(opcional)
            #(carga todos los campos a utilizar desde la planilla)
            ok = pyfpdf.CargarFormato(ubicacion_sistema() + "/plantillas/factura.csv")
        #Creo plantilla para esta factura(papel A4vertical):

        if LeerIni(clave='homo') == 'S':
            pyfpdf.AgregarCampo("homo", 'T', 150, 350, 0, 0,
                              size=70, rotate=45, foreground=0x808080, priority=-1, text="HOMOLOGACION")
        papel = "A4" #o "letter" para carta, "legal" para oficio
        orientacion = "portrait" #o landscape(apaisado)
        ok = pyfpdf.CrearPlantilla(papel, orientacion)
        num_copias = int(LeerIni(clave='num_copias', key='FACTURA')) #original, duplicado y triplicado
        lineas_max = 24 #cantidad de linas de items porp�gina
        qty_pos = "izq" #(cantidad a la izquierda de la descripci�n del art�culo)
        #Proceso la plantilla
        ok = pyfpdf.ProcesarPlantilla(num_copias, lineas_max, qty_pos)

        if not os.path.isdir('facturas'):
            os.mkdir('facturas')
        #Genero el PDF de salida seg�n la plantilla procesada
        salida = join('facturas',"{}-{}.pdf".format(cabfact.tipocomp.nombre, cabfact.numero))
        ok = pyfpdf.GenerarPDF(salida)
        #Abro el visor de PDF y muestro lo generado
        #(es necesario tener instalado Acrobat Reader o similar)
        imprimir = False #cambiar a True para que lo envie directo a laimpresora
        if mostrar:
            pyfpdf.MostrarPDF(salida, imprimir)

        self.facturaGenerada = salida

    def Validacion(self):
        retorno = True
        if not self.view.validaCliente.text():
            Ventanas.showAlert(LeerIni('nombre_sistema'), "ERROR: No se ha especificado un cliente valido")
            retorno = False

        for x in range(self.view.gridFactura.rowCount()):
            iva = float(self.view.gridFactura.ObtenerItem(fila=x, col='IVA'))
            if str(iva) not in FEv1().TASA_IVA:
                Ventanas.showAlert(LeerIni('nombre_sistema'), "Error el item {} no tiene un IVA valido".format(x+1))
                retorno = False
            codigo = self.view.gridFactura.ObtenerItem(fila=x, col='Codigo')
            try:
                articulo = Articulo.get_by_id(codigo)
            except Articulo.DoesNotExist:
                Ventanas.showAlert(LeerIni('nombre_sistema'), "Error el item {} tiene un articulo no valido".format(x + 1))
                retorno = False

        return retorno

    def onClickbotonBorraArt(self):
        self.view.gridFactura.removeRow(self.view.gridFactura.currentRow())
        self.SumaTodo()

    def onCurrentIndexChanged(self):
        #self.ObtieneNumeroFactura()
        self.tipo_cpte = self.view.cboComprobante.text()
        if str(self.view.cboComprobante.text()).find('credito'):
            self.view.layoutCpbteRelacionado.lineEditNumero.setEnabled(True)
            self.view.layoutCpbteRelacionado.lineEditPtoVta.setEnabled(True)

    def EstablecerOrden(self):
        self.view.validaCliente.proximoWidget = self.view.lineEditDomicilio
        self.view.lineEditDomicilio.proximoWidget = self.view.lineEditDocumento
        self.view.lineEditDocumento.proximoWidget = self.view.cboTipoIVA
        self.view.cboTipoIVA.proximoWidget = self.view.cboComprobante
        self.view.cboComprobante.proximoWidget = self.view.botonAgregaArt
