from ntpath import join
import os
from PyQt5.QtCore import Qt
from controladores.FPDFv1 import FEPDFv1
from controladores.ControladorBase import ControladorBase
from controladores.FE import FEv1, PyQRv1
from libs import Ventanas
from libs.Utiles import DeCodifica, FechaMysql, FormatoFecha, LeerIni, getFileName, imagen, inicializar_y_capturar_excepciones, ubicacion_sistema
from modelos.Articulos import Articulo
from modelos.ParametrosSistema import ParamSist
from modelos.Remitos import DetalleRemito, Remito
from modelos.Tipocomprobantes import TipoComprobante
from vistas.Busqueda import UiBusqueda
from vistas.Remitos import RemitoView


class RemitoController(ControladorBase):

    cliente = None #modelo cliente
    tipo_cpte = 1 #tipo de comprobante a facturar
    remitoGenerado = None #ruta del remito generado
    modifica = False
    id_remito = 0
    
    def __init__(self):
        super().__init__()
        self.view = RemitoView()
        self.conectarWidgets()
        self.EstablecerOrden()
        
    def conectarWidgets(self):
        self.view.btn_cerrar.clicked.connect(self.view.Cerrar)
        self.view.btn_guardar.clicked.connect(self.Guardar)
        self.view.btn_borrar.clicked.connect(self.Borrar)
        self.view.grilla.keyPressed.connect(self.onKeyPressedGridFactura)
        self.view.tipo_comprobante.editingFinished.connect(self.onTipoComprobanteEditingFinished)
        self.view.numero.lineEditNumero.editingFinished.connect(self.onNumeroEditingFinished)
        
    @inicializar_y_capturar_excepciones
    def Guardar(self, *args, **kwargs):
        if not self.Validaciones():
            return
        if self.modifica:
            ultimo_comprobante = self.view.numero.numero
        else:
            ultimo_comprobante = TipoComprobante().SiguienteNumero(self.view.tipo_comprobante.text())
        if self.modifica:
            remito = self.id_remito
        else:
            remito = Remito()
        remito.cliente = self.view.cliente.text()
        remito.fecha = self.view.fecha.toPyDate()
        remito.ptovta = self.view.numero.lineEditPtoVta.text()
        remito.numero = str(ultimo_comprobante).zfill(8)
        remito.observaciones = self.view.observaciones.toPlainText()
        remito.forma_pago = self.view.forma_pago.text()
        remito.tipo_comprobante = self.view.tipo_comprobante.text()
        remito.estado = 'A'
        remito.save()
        
        if self.modifica: #si se esta modificando el remito se borra todos los detalles
            DetalleRemito.delete().where(DetalleRemito.remito == remito.idremito).execute()
            
        for row in range(self.view.grilla.rowCount()):
            detalle = DetalleRemito()
            detalle.remito = remito.idremito
            detalle.producto = self.view.grilla.ObtenerItem(fila=row, col='Producto')
            detalle.detalle = self.view.grilla.ObtenerItem(fila=row, col='Detalle')
            detalle.cantidad = self.view.grilla.ObtenerItem(fila=row, col='Cantidad')
            detalle.precio = self.view.grilla.ObtenerItem(fila=row, col='Unitario')
            detalle.tipo_iva = Articulo.get_by_id(detalle.producto).tipoiva
            detalle.save()
        self.Imprimir(remito.idremito)
        self.view.Cerrar()            
    
    @inicializar_y_capturar_excepciones
    def onKeyPressedGridFactura(self, key, *args, **kwargs):
        col = self.view.grilla.currentColumn()
        row = self.view.grilla.currentRow()
        cabeceras = ["Producto", "Detalle", "Cantidad", "Unitario"]
        if key == Qt.Key_F2 and col == 0:
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
                self.view.grilla.ModificaItem(valor=_ventana.ValorRetorno,
                                                   fila=self.view.grilla.currentRow(),
                                                   col=0)
                self.view.grilla.ModificaItem(valor=_ventana.campoRetornoDetalle,
                                                   fila=self.view.grilla.currentRow(),
                                                   col=1)
                art = Articulo.get_by_id(_ventana.ValorRetorno)
                self.view.grilla.ModificaItem(valor=art.preciopub,
                                                   fila=self.view.grilla.currentRow(),
                                                   col='Unitario')
            self.view.grilla.setFocus()
        if key in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab] and col == 0:
            codigo = self.view.grilla.ObtenerItem(fila=row, col="Producto")
            if codigo:
                art = Articulo.get_by_id(codigo)
                if float(self.view.grilla.ObtenerItem(fila=row, col='Unitario')) == 0:
                    self.view.grilla.ModificaItem(valor=art.preciopub,
                                                fila=self.view.grilla.currentRow(),
                                                col='Unitario')
                self.view.grilla.ModificaItem(valor=art.nombre,
                                              fila=self.view.grilla.currentRow(),
                                              col="Detalle")
                    

        if key in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab]:
            if col < self.view.grilla.columnCount():
                self.view.grilla.setCurrentCell(row, col + 1)
            else:
                self.view.grilla.setCurrentCell(row + 1, 0)

        if key == Qt.Key_Down and row + 1 == self.view.grilla.rowCount():
            self.AgregaArt()

        self.SumaTodo()

    def AgregaArt(self):
        item = [
            0, '', 0, 0
        ]
        self.view.grilla.AgregaItem(items=item)
    
    def SumaTodo(self):
        total = 0
        for row in range(self.view.grilla.rowCount()):
            cantidad = self.view.grilla.ObtenerItemNumerico(fila=row, col='Cantidad')
            unitario = self.view.grilla.ObtenerItemNumerico(fila=row, col='Unitario')
            total_renglon = cantidad * unitario
            self.view.grilla.ModificaItem(valor=total_renglon, fila=row, col='Total')
            total += cantidad * unitario
        self.view.total.setText(str(total))
        
    def Borrar(self, *args, **kwargs):
        row = self.view.grilla.currentRow()
        if row == -1:
            return
        self.view.grilla.removeRow(row)
        self.SumaTodo()
        
    @inicializar_y_capturar_excepciones
    def onTipoComprobanteEditingFinished(self, *args, **kwargs):
        try:
            tipo_comprobante = TipoComprobante.get_by_id(self.view.tipo_comprobante.text())
            self.view.numero.lineEditPtoVta.setText(ParamSist.ObtenerParametro('PtoVtaRemito', '0001'))
            self.view.numero.lineEditNumero.setText(str(tipo_comprobante.ultcomp + 1).zfill(8))
        except:
            return
        
    def EstablecerOrden(self):
        self.view.cliente.proximoWidget = self.view.fecha
        self.view.fecha.proximoWidget = self.view.tipo_comprobante
        self.view.tipo_comprobante.proximoWidget = self.view.numero.lineEditPtoVta
        self.view.numero.lineEditPtoVta.proximoWidget = self.view.numero.lineEditNumero
        self.view.numero.lineEditNumero.proximoWidget = self.view.forma_pago
        self.view.forma_pago.proximoWidget = self.view.observaciones
        self.view.observaciones.proximoWidget = self.view.grilla
        self.view.grilla.proximoWidget = self.view.btn_guardar
        
    def Imprimir(self, remito_id, mostrar=True):
        if not remito_id:
            return
        cabrem = Remito.get_by_id(remito_id)
        print("imprimir Remito {}".format(cabrem.numero))
        pyfpdf = FEPDFv1()
        #cuit del emisor
        pyfpdf.CUIT = LeerIni(clave='cuit', key='WSFEv1')
        #establezco formatos (cantidad de decimales):
        pyfpdf.FmtCantidad = "0.4"
        pyfpdf.FmtPrecio = "0.2"
        #Datos del encabezado de la factura:
        tipo_cbte = str(cabrem.tipo_comprobante.codigo).zfill(3)
        punto_vta = str(cabrem.ptovta).zfill(4)
        cbte_nro = str(cabrem.numero).zfill(8)
        fecha = FechaMysql(cabrem.fecha)
        concepto = 1
        #datos del cliente:
        tipo_doc = "80" if cabrem.cliente.tiporesp_id != 3 else "96"
        nro_doc = cabrem.cliente.cuit if cabrem.cliente.tiporesp_id != 3 else str(cabrem.cliente.dni)
        nombre_cliente = cabrem.cliente.nombre
        domicilio_cliente = cabrem.cliente.domicilio

        #totales del comprobante:
        imp_total = cabrem.total
        imp_tot_conc = "0.00"
        imp_neto = 0
        imp_iva = 0
        imp_trib = 0
        imp_op_ex = "0.00"
        imp_subtotal = 0
        fecha_cbte = fecha
        fecha_venc_pago = fecha
        #Fechas del período del servicio facturado
        fecha_serv_hasta = None
        fecha_serv_desde = None

        moneda_id = "PES"
        moneda_ctz = "1.000"
        obs_generales = ""
        obs_comerciales = ""
        moneda_id = ""
        moneda_ctz = 1
        cae = ""
        fecha_vto_cae = ""

        #Creo la factura(internamente en la interfaz)
        ok = pyfpdf.CrearFactura(concepto, tipo_doc, nro_doc, tipo_cbte, punto_vta,
                    cbte_nro, imp_total, imp_tot_conc, imp_neto,
                    imp_iva, imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
                    fecha_serv_desde, fecha_serv_hasta,
                    moneda_id, moneda_ctz, cae, fecha_vto_cae, "",
                    nombre_cliente, domicilio_cliente, 0)
        pyfpdf.EstablecerParametro("forma_pago", cabrem.forma_pago.detalle)
        pyfpdf.EstablecerParametro("custom-nro-cli", "[{}]".format(str(cabrem.cliente.idcliente).zfill(5)))
        pyfpdf.EstablecerParametro("localidad_cli", cabrem.cliente.localidad.nombre)
        pyfpdf.EstablecerParametro("provincia_cli", cabrem.cliente.localidad.provincia)
        pyfpdf.EstablecerParametro("iva_cli", cabrem.cliente.tiporesp.nombre)

        #Agrego detalles de cada item de la remito:
        det = DetalleRemito.select().where(DetalleRemito.remito == cabrem.idremito)
        for d in det:
            #Agrego detalles de cada item de la factura:
            u_mtx = 0 #unidades
            cod_mtx = "" #c�digo de barras
            codigo = d.producto.idarticulo #codigo interno a imprimir(ej. "articulo")
            ds = d.detalle.strip()
            qty = d.cantidad #cantidad
            umed = 7 #c�digo de unidad de medida(ej. 7 para"unidades")
            precio = d.precio #precio neto(A) o iva incluido(B)
            bonif = 0 #importe de descuentos
            iva_id = FEv1().TASA_IVA[str(float(d.tipo_iva.iva))] #c�digopara al�cuota del 21 %
            # imp_iva = d.montoiva #importe liquidado deiva
            imp_iva = 0
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
        logo = ParamSist.ObtenerParametro("LOGO_FACTURA")
        if logo:
            ok = pyfpdf.AgregarDato("logo", logo)
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

        pyqr = PyQRv1()
        pyqr.CrearArchivo()
        ver = 1
        fecha = FormatoFecha(cabrem.fecha, formato='afip')
        cuit = ParamSist.ObtenerParametro("CUIT_EMPRESA").replace('-', '')
        if not cuit:
            cuit = LeerIni(clave='cuit', key='WSFEv1').replace('-', '')
        pto_vta = punto_vta
        tipo_cmp = tipo_cbte
        nro_cmp = cbte_nro
        importe = round(imp_total, 2)
        moneda = moneda_id
        ctz = moneda_ctz
        tipo_doc_rec = tipo_doc
        nro_doc_rec = nro_doc.replace('-', '')
        tipo_cod_aut = "E"
        cod_aut = cae
        # url = pyqr.GenerarImagen(
        #     ver, fecha, cuit, pto_vta, tipo_cmp, nro_cmp,
        #     importe, moneda, ctz, tipo_doc_rec, nro_doc_rec,
        #     tipo_cod_aut, cod_aut
        # )
        # pyfpdf.AgregarDato("QR", pyqr.Archivo)

        ok = pyfpdf.CargarFormato(ubicacion_sistema() + "/plantillas/remito.csv")
        #Creo plantilla para esta factura(papel A4vertical):

        papel = "A4" #o "letter" para carta, "legal" para oficio
        orientacion = "portrait" #o landscape(apaisado)
        ok = pyfpdf.CrearPlantilla(papel, orientacion)
        num_copias = int(LeerIni(clave='num_copias', key='FACTURA')) #original, duplicado y triplicado
        lineas_max = 24 #cantidad de linas de items porp�gina
        qty_pos = "izq" #(cantidad a la izquierda de la descripci�n del art�culo)
        #Proceso la plantilla
        ok = pyfpdf.ProcesarPlantilla(num_copias, lineas_max, qty_pos)

        if not os.path.isdir('remitos'):
            os.mkdir('remitos')
        try:
            #Genero el PDF de salida seg�n la plantilla procesada
            salida = join('remitos',"{}-{}.pdf".format(cabrem.tipo_comprobante.nombre.replace(" ", "_"), f'{str(cabrem.ptovta).zfill(4)}{str(cabrem.numero).zfill(8)}'))
            ok = pyfpdf.GenerarPDF(salida)
        except:
            cArchivo = getFileName("remito", False)
            cArchivoPDF = cArchivo + '.pdf'
            salida = cArchivoPDF
            ok = pyfpdf.GenerarPDF(salida)
        #Abro el visor de PDF y muestro lo generado
        #(es necesario tener instalado Acrobat Reader o similar)
        imprimir = False #cambiar a True para que lo envie directo a laimpresora
        if mostrar:
            pyfpdf.MostrarPDF(salida, imprimir)

        self.remitoGenerado = salida
        
    @inicializar_y_capturar_excepciones
    def onNumeroEditingFinished(self, *args, **kwargs):
        try:
            remito = Remito.get(
                Remito.tipo_comprobante == self.view.tipo_comprobante.text(),
                Remito.ptovta == self.view.numero.lineEditPtoVta.text(),
                Remito.numero == self.view.numero.lineEditNumero.text()
            )
            self.view.forma_pago.setText(remito.forma_pago.detalle)
            self.view.observaciones.setText(remito.observaciones)
            self.id_remito = remito.idremito
            detalle = DetalleRemito.select().where(DetalleRemito.remito == remito.idremito)
            self.view.grilla.setRowCount(0)
            for det in detalle:
                item = [
                    det.producto.idarticulo,
                    det.detalle,
                    det.cantidad,
                    det.precio,
                    det.iddetalleremito
                ]
                self.view.grilla.AgregaItem(item)
            self.modifica = True
            self.SumaTodo()
        except Remito.DoesNotExist:
            self.modifica = False
            return
        
    @inicializar_y_capturar_excepciones
    def Validaciones(self, *args, **kwargs):
        lretorno = True
        if not self.view.cliente.valido:
            Ventanas.showAlert("Sistema", "Debe seleccionar un cliente valido")
            lretorno = False
        if not self.view.tipo_comprobante.valido:
            Ventanas.showAlert("Sistema", "Debe seleccionar un tipo de comprobante valido")
            lretorno = False
        
        for row in range(self.view.grilla.rowCount()):
            producto = self.view.grilla.ObtenerItem(fila=row, col='Producto')
            if not producto:
                self.view.grilla.removeRow(row)
            else:
                cantidad = self.view.grilla.ObtenerItemNumerico(fila=row, col='Cantidad')
                if cantidad == 0:
                    Ventanas.showAlert("Sistema", "La cantidad no puede ser 0")
                    lretorno = False
                precio = self.view.grilla.ObtenerItemNumerico(fila=row, col='Unitario')
                if precio == 0:
                    Ventanas.showAlert("Sistema", "El precio no puede ser 0")
                    lretorno = False
        return lretorno