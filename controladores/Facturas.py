# coding=utf-8
import decimal
from os.path import join

from PyQt4.QtCore import Qt

from controladores.ControladorBase import ControladorBase
from controladores.FE import FEv1
from libs import Ventanas
from libs.Utiles import LeerIni, validar_cuit, FechaMysql, ubicacion_sistema, inicializar_y_capturar_excepciones
from modelos import Tipocomprobantes
from modelos.Articulos import Articulo
from modelos.Cabfact import Cabfact
from modelos.Clientes import Cliente
from modelos.Detfact import Detfact
from modelos.Impuestos import Impuesto
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

    def __init__(self):
        super(FacturaController, self).__init__()
        self.view = FacturaView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.validaCliente.editingFinished.connect(self.CargaDatosCliente)
        self.view.checkBoxServicios.stateChanged.connect(self.HabilitaVencimientos)
        self.view.btnCerrarFormulario.clicked.connect(self.view.Cerrar)
        self.view.botonAgregaArt.clicked.connect(self.AgregaArt)
        self.view.gridFactura.keyPressed.connect(self.onKeyPressedGridFactura)
        self.view.btnGrabarFactura.clicked.connect(self.GrabaFactura)
        self.view.lineEditDocumento.editingFinished.connect(self.onEditingFinishedDocumento)

    def CargaDatosCliente(self):
        if not self.view.validaCliente.text():
            return
        self.cliente = Cliente.select().where(Cliente.idcliente == self.view.validaCliente.text()).get()
        cliente = self.cliente
        self.view.lineEditDomicilio.setText(cliente.domicilio)
        if cliente.tiporesp.idtiporesp in [1, 2, 4]: #monotributo o resp inscripto
            self.view.lineEditDocumento.setText(cliente.cuit.replace('-',''))
            self.view.lineEditDocumento.setInputMask("99-99999999-9")
        else:
            self.view.lineEditDocumento.setText(str(cliente.dni))
            self.view.lineEditDocumento.setInputMask("99999999")
        if int(LeerIni(clave='CAT_IVA', key='WSFEv1')) == 1: #si es Resp insc el contribuyente veo si teiene que emitira A o B
            if cliente.tiporesp.idtiporesp == 2: #resp inscripto
                self.view.cboComprobante.setText('Factura A')
            else:
                self.view.cboComprobante.setText('Factura B')
        else:
            self.view.cboComprobante.setText('Factura C')

        self.view.cboTipoIVA.setText(cliente.tiporesp.nombre)
        self.view.layoutFactura.lineEditPtoVta.setText(LeerIni(clave='PTO_VTA', key='WSFEv1').zfill(4))
        tipos = Tipocomprobantes.ComboTipoComp(tiporesp=int(LeerIni(clave='CAT_IVA', key='WSFEv1')))
        tipo_cpte = [k for (k, v) in tipos.valores.iteritems() if v == self.view.cboComprobante.text()][0]
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
            _ventana.campos = ['idarticulo', 'nombre']
            _ventana.CargaDatos()
            _ventana.exec_()
            if _ventana.lRetval:
                self.view.gridFactura.ModificaItem(valor=_ventana.ValorRetorno,
                                                   fila=self.view.gridFactura.currentRow(),
                                                   col=1)
                self.view.gridFactura.ModificaItem(valor=_ventana.campoRetornoDetalle,
                                                   fila=self.view.gridFactura.currentRow(),
                                                   col=2)
        elif key in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab] and col == 1:
            codigo = self.view.gridFactura.ObtenerItem(fila=row, col=1)

        self.SumaTodo()

    def SumaTodo(self):

        totalgral = 0.
        ivagral = 0.
        dgrgral = 0.
        self.netos = {
            0: 0,
            10.5: 0,
            21: 0
        }
        try:
            impuesto = float(self.cliente.percepcion.porcentaje)
        except Impuesto.DoesNotExist:
            impuesto = decimal.Decimal.from_float(0.)
        for x in range(self.view.gridFactura.rowCount()):
            if int(LeerIni(clave='CAT_IVA', key='WSFEv1')) == 6:
                self.view.gridFactura.ModificaItem(valor=21, fila=x, col='IVA')
            detalle = self.view.gridFactura.ObtenerItem(fila=x, col='Detalle')
            if not detalle:
                codigo = self.view.gridFactura.ObtenerItem(fila=x, col='Codigo')
                try:
                    art = Articulo.get_by_id(codigo)
                    self.view.gridFactura.ModificaItem(valor=art.nombre, fila=x, col='Detalle')
                    self.view.gridFactura.ModificaItem(valor=art.preciopub, fila=x, col='Unitario')
                except Articulo.DoesNotExist:
                    pass
            cantidad = self.view.gridFactura.ObtenerItem(fila=x, col='Cant.')
            #self.view.gridFactura.ModificaItem(valor=cantidad, fila=x, col='Cant.')
            unitario = self.view.gridFactura.ObtenerItem(fila=x, col='Unitario')
            iva = float(self.view.gridFactura.ObtenerItem(fila=x, col='IVA'))
            total = float(cantidad) * float(unitario)
            self.netos[iva] += total
            if int(LeerIni(clave='CAT_IVA',
                           key='WSFEv1')) == 1:  # si es Resp insc el contribuyente
                ivagral += total * iva / 100
            totalgral += total
            self.view.gridFactura.ModificaItem(valor=total, fila=x, col='SubTotal')


        if int(LeerIni(clave='CAT_IVA',
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

        self.view.lineEditTributos.setText(str(round(dgrgral, 3)))
        self.view.lineEditTotalIVA.setText(str(round(ivagral, 3)))
        self.view.lineEditTotal.setText(str(round(totalgral + ivagral + dgrgral, 2)))

    def GrabaFactura(self):
        if not self.Validacion():
            return
        self.SumaTodo()
        ok = self.CreaFE()
        if ok:
            print("Graba factura")
            self.GrabaFE()
        self.view.Cerrar()

    def CreaFE(self):
        ok = True
        wsfev1 = FEv1()
        ta = wsfev1.Autenticar()
        #Setear tocken y sign de autorizacion(ticket de accesso, pasos previos)
        wsfev1.SetTicketAcceso(ta)
        wsfev1.Cuit = LeerIni(clave='CUIT', key='WSFEv1') #CUIT del emisor (debe estar registrado en la AFIP)
        #Conectar al Servicio Web de Facturacion
        #Produccion usar: *-- ok = WSFE.Conectar("", "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL") & & Producción
        if LeerIni(clave='HOMO'):
            ok = wsfev1.Conectar("") #Homologacion
        else:
            ok = wsfev1.Conectar("", LeerIni(clave="URL", key="WSFEv1"))

        if self.view.checkBoxServicios.isChecked() \
            and self.view.checkBoxProductos.isChecked(): #si es productoso y servicios
            concepto = wsfev1.PRODUCTOYSERVICIOS
        elif self.view.checkBoxServicios.isChecked():
            concepto = wsfev1.SERVICIOS
        else:
            concepto = wsfev1.PRODUCTOS

        self.concepto = concepto
        if self.cliente.tiporesp.idtiporesp == 3: #consumidor final
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
        if int(LeerIni(clave='CAT_IVA',
                       key='WSFEv1')) == 1:  # si es Resp insc el contribuyente
            imp_neto = str(float(self.view.lineEditTotal.text()) - \
                float(self.view.lineEditTributos.text()) - \
                float(self.view.lineEditTotalIVA.text()))
        else:
            imp_neto = self.view.lineEditTotal.text()
        imp_iva = self.view.lineEditTotalIVA.text()
        imp_trib = self.view.lineEditTributos.text()
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
        #Llamo al WebService de Autorizacion para obtener el CAE
        ok = wsfev1.CrearFactura(concepto, tipo_doc, nro_doc, tipo_cbte, punto_vta,
                cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
                imp_iva, imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
                fecha_serv_desde, fecha_serv_hasta,
                moneda_id, moneda_ctz)

        if round(float(self.view.lineEditTributos.text()), 3) != 0:
            idimp = wsfev1.ID_IMP_PCIAL
            detalle = self.cliente.percepcion.detalle
            base_imp = float(self.view.lineEditTotal.text()) - \
                float(self.view.lineEditTributos.text()) - \
                float(self.view.lineEditTotalIVA.text())
            alicuota = self.cliente.percepcion.porcentaje
            importe = self.view.lineEditTributos.text()
            wsfev1.AgregarTributo(tributo_id=idimp, desc=detalle, base_imp=base_imp,
                                  alic=alicuota, importe=importe)
        #SolicitoCAE:
        cae = wsfev1.CAESolicitar()
        if wsfev1.ErrMsg:
            Ventanas.showAlert("Sistema", wsfev1.ErrMsg)
            ok = False
        else:
            if wsfev1.Resultado == 'R':
                Ventanas.showAlert("Sistema", "Motivo de rechazo {}".format(wsfev1.Obs))
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
        cabfact.venccae = self.view.fechaVencCAE.getFechaSql()
        cabfact.concepto = self.concepto
        cabfact.save()

        for x in range(self.view.gridFactura.rowCount()):
            codigo = self.view.gridFactura.ObtenerItem(fila=x, col='Codigo')
            cantidad = float(self.view.gridFactura.ObtenerItem(fila=x, col='Cant.'))
            importe = float(self.view.gridFactura.ObtenerItem(fila=x, col='SubTotal'))
            iva = float(self.view.gridFactura.ObtenerItem(fila=x, col='IVA'))
            detalle = self.view.gridFactura.ObtenerItem(fila=x, col='Detalle')
            articulo = Articulo.get_by_id(codigo)
            detfact = Detfact()
            detfact.idcabfact = cabfact.idcabfact
            detfact.idarticulo = codigo
            detfact.cantidad = cantidad
            detfact.unidad = articulo.unidad
            detfact.costo = articulo.costo
            if LeerIni(clave='CAT_IVA', key='WSFEv1') == 1:
                detfact.precio = importe + importe * iva / 100
            else:
                detfact.precio = importe
            detfact.tipoiva = articulo.tipoiva.codigo
            detfact.montoiva = importe * iva / 100
            if self.view.lineEditTributos.value() > 0:
                detfact.montodgr = importe * self.cliente.percepcion.porcentaje / 100
            else:
                detfact.montodgr = 0.00
            detfact.montomuni = 0.00
            detfact.descad = detalle
            detfact.detalle = detalle[:40]
            detfact.descuento = 0.00
            detfact.save()
        self.ImprimeFactura(idcabecera=cabfact.idcabfact)

    @inicializar_y_capturar_excepciones
    def ImprimeFactura(self, idcabecera = None, *args, **kwargs):
        if not idcabecera:
            return
        cabfact = Cabfact().get_by_id(idcabecera)
        print("imprimir factura {}".format(cabfact.numero))
        pyfpdf = FEPDF()
        #cuit del emisor
        pyfpdf.CUIT = LeerIni(clave='CUIT', key='WSFEv1')
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
        tipo_doc = "80" if cabfact.cliente.tiporesp_id == 2 else "96"
        nro_doc = cabfact.cliente.cuit if cabfact.cliente.tiporesp_id == 2 else str(cabfact.cliente.dni)
        nombre_cliente = cabfact.nombre
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
        fecha_serv_desde = fecha
        fecha_serv_hasta = fecha
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
        #tipo = 19
        #pto_vta = 2
        #nro = 1234
        #pyfepdf.AgregarCmpAsoc(tipo, pto_vta, nro)

        #Agrego subtotales de IVA(uno por alicuota)
        if cabfact.netoa != 0:
            iva_id = 5 #c�digo para al�cuota del 21 %
            base_imp = cabfact.netoa #importe neto sujeto a esta al�cuota
            importe = 21 #importe liquidado de iva
            ok = pyfpdf.AgregarIva(iva_id, base_imp, importe)

        if cabfact.netob != 0:
            iva_id = 4  # c�digo para al�cuota del 21 %
            base_imp = cabfact.netob  # importe neto sujeto a esta al�cuota
            importe = 10.5  # importe liquidado de iva
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
            ds = d.descad
            qty = d.cantidad #cantidad
            umed = 7 #c�digo de unidad de medida(ej. 7 para"unidades")
            precio = d.precio #precio neto(A) o iva incluido(B)
            bonif = 0 #importe de descuentos
            iva_id = FEv1().TASA_IVA[str(d.tipoiva.iva)] #c�digopara al�cuota del 21 %
            imp_iva = d.montoiva #importe liquidado deiva
            importe = d.precio #importe total del item
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
        ok = pyfpdf.AgregarDato("EMPRESA", "Razon social: {}".format(LeerIni(clave='EMPRESA', key='FACTURA')))
        ok = pyfpdf.AgregarDato("MEMBRETE1", "Domicilio Comercial: {}".format(LeerIni(clave='MEMBRETE1', key='FACTURA')))
        ok = pyfpdf.AgregarDato("MEMBRETE2", LeerIni(clave='MEMBRETE2', key='FACTURA'))
        ok = pyfpdf.AgregarDato("CUIT", LeerIni(clave='CUIT', key='FACTURA'))
        ok = pyfpdf.AgregarDato("IIBB", LeerIni(clave='IIBB', key='FACTURA'))
        ok = pyfpdf.AgregarDato("IVA", "Condicion frente al IVA: {}".format(LeerIni(clave='IVA', key='FACTURA')))
        ok = pyfpdf.AgregarDato("INICIO", "Fecha inicio actividades: {}".format(LeerIni(clave='INICIO', key='FACTURA')))

        #Cargo el formato desde el archivo CSV(opcional)
        #(carga todos los campos a utilizar desde la planilla)
        ok = pyfpdf.CargarFormato(ubicacion_sistema() + "/plantillas/factura.csv")
        #Creo plantilla para esta factura(papel A4vertical):
        papel = "A4" #o "letter" para carta, "legal" para oficio
        orientacion = "portrait" #o landscape(apaisado)
        ok = pyfpdf.CrearPlantilla(papel, orientacion)
        num_copias = 3 #original, duplicado y triplicado
        lineas_max = 24 #cantidad de linas de items porp�gina
        qty_pos = "izq" #(cantidad a la izquierda de la descripci�n del art�culo)
        #Proceso la plantilla
        ok = pyfpdf.ProcesarPlantilla(num_copias, lineas_max, qty_pos)
        #Genero el PDF de salida seg�n la plantilla procesada
        salida = join('facturas',"factura{}.pdf".format(cabfact.numero))
        ok = pyfpdf.GenerarPDF(salida)
        #Abro el visor de PDF y muestro lo generado
        #(es necesario tener instalado Acrobat Reader o similar)
        imprimir = False #cambiar a True para que lo envie directo a laimpresora
        ok = pyfpdf.MostrarPDF(salida, imprimir)

    def Validacion(self):
        retorno = True
        if not self.view.validaCliente.text():
            Ventanas.showAlert(LeerIni('nombre_sistema'), "ERROR: No se ha especificado un cliente valido")
            retorno = False

        return retorno