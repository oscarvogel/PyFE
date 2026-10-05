# coding=utf-8
import decimal
import logging
import os

import peewee
import threading
from datetime import date

from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication
from os.path import join

from controladores.ControladorBase import ControladorBase
from controladores.FCE import WsFECred
from controladores.FE import FEv1, PyQRv1
from controladores.FacturaBranding import aplicar_marca_factura, cargar_config_marca_factura, obtener_formato_factura
from libs import Ventanas, Constantes
from libs import fpdf_compat
from libs import stock
from libs.instalacion import cuit_emisor
from libs.visor import abrir_pdf
from libs.Utiles import (LeerIni, validar_cuit, FechaMysql, ubicacion_sistema,
                         inicializar_y_capturar_excepciones, DeCodifica, imagen,
                         getFileName, FormatoFecha, formato_cuit, a_entero,
                         escribir_pdf)
from modelos.Articulos import Articulo
from modelos.Cabfact import Cabfact
from modelos.Clientes import Cliente
from modelos.CpbteRelacionado import CpbteRel
from modelos.Detfact import Detfact
from modelos.Formaspago import Formapago
from modelos.Impuestos import Impuesto
from modelos.ModeloBase import db
from modelos.ParametrosSistema import ParamSist
from modelos.Tipocomprobantes import TipoComprobante
from modelos.Tipoiva import Tipoiva
from pyafipws.pyfepdf import FEPDF
from vistas.Busqueda import UiBusqueda

from vistas.Facturas import FacturaView


class _EmisionWorker(QObject):
    """Corre _autorizar() en un hilo aparte y avisa por senales.

    Va en su propia clase y no como metodo del controlador porque Qt necesita
    un QObject con vida propia: si el worker se crea como variable local y se
    pierde la referencia, se lo garbage-collectea a mitad de la emision y la
    factura queda en un estado imposible de explicar.

    SIN padre, a proposito. Qt no deja mover a otro hilo un QObject que tenga
    padre:

        QObject::moveToThread: Cannot move objects with a parent

    y lo dice en la consola, sin exception: si se le pasa la vista como padre,
    el worker se queda en el hilo principal, las llamadas a ARCA siguen
    corriendo aca, y la ventana se sigue congelando igual. Parece que funciona
    y no funciona. La vida la sostiene self._worker en el controlador.
    """

    # Emitidas desde el hilo de trabajo, recibidas en el principal. Qt encola
    # sola las que se cruzan entre hilos, asi que no hace falta lock.
    etapa = pyqtSignal(str)
    terminado = pyqtSignal(bool, object)

    def __init__(self, controlador, datos, parent=None):
        super(_EmisionWorker, self).__init__(parent)
        self._controlador = controlador
        self._datos = datos
        self.resultado = (False, {"error": "No se pudo emitir."})

    @pyqtSlot()
    def run(self):
        # Avisar por senal, no llamar a self._etapa(): _etapa toca el dialogo
        # de progreso, que pertenece al hilo de la interfaz.
        self.resultado = self._controlador._autorizar(
            self._datos, avisar=self.etapa.emit)
        ok, aviso = self.resultado
        self.terminado.emit(ok, aviso)


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
        # Enter y el boton de lupa abren el buscador. El boton y no solo F2
        # porque un F2 sin pista no se descubre: el operador ve la lupa.
        self.view.validaCliente.returnPressed.connect(self.buscar_cliente)
        self.view.btnBuscarCliente.clicked.connect(self.buscar_cliente)
        self.view.checkBoxServicios.stateChanged.connect(self.HabilitaVencimientos)
        # El periodo aparece y desaparece con el tipo de comprobante, asi que
        # hay que reaccionar al cambio y no solo a los servicios.
        self.view.cboComprobante.currentIndexChanged.connect(
            self.HabilitaVencimientos)
        self.view.btnCerrarFormulario.clicked.connect(self.view.Cerrar)
        self.view.botonAgregaArt.clicked.connect(self.AgregaArt)
        self.view.gridFactura.keyPressed.connect(self.onKeyPressedGridFactura)
        self.view.btnGrabarFactura.clicked.connect(self.GrabaFactura)
        self.view.lineEditDocumento.editingFinished.connect(self.onEditingFinishedDocumento)
        self.view.botonBorrarArt.clicked.connect(self.onClickbotonBorraArt)
        self.view.cboComprobante.currentIndexChanged.connect(self.onCurrentIndexChanged)

    @inicializar_y_capturar_excepciones
    def buscar_cliente(self, *args, **kwargs):
        """Abre el buscador de clientes, con Enter o con F2.

        El campo de cliente valida el codigo solo, que sirve cuando el
        operador conoce el codigo. Con 800 clientes no es el caso: tiene que
        poder buscar por nombre, como en la venta rapida.
        """
        if self._buscando_cliente:
            return
        self._buscando_cliente = True
        try:
            ventana = UiBusqueda()
            ventana.modelo = Cliente
            ventana.cOrden = Cliente.nombre
            ventana.limite = 100
            ventana.campos = ["idcliente", "nombre", "domicilio", "cuit"]
            ventana.campoBusqueda = Cliente.nombre
            ventana.campoRetorno = Cliente.idcliente
            ventana.campoRetornoDetalle = Cliente.nombre
            ventana.CargaDatos()
            ventana.exec_()
            if ventana.lRetval:
                self.view.validaCliente.setText(str(ventana.ValorRetorno))
                self.CargaDatosCliente()
        finally:
            # Con try/finally: si el dialogo explota, el candado se libera y
            # la pantalla no queda inservible hasta reiniciar.
            self._buscando_cliente = False

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
                if ParamSist.ObtenerParametro("EMITE_FCE") == "S":
                    wsfecred = WsFECred()
                    obligado, minimo = wsfecred.ConsultarMontoObligado(cliente.cuit.replace('-',''), cuit_emisor())
                    if obligado and not self.informo:
                        Ventanas.showAlert("Sistema", "Se debe emitir FCE al cliente desde un monto de {}".format(minimo))
                self.informo = True
            else:
                self.view.lineEditDocumento.setText(str(cliente.dni))
                self.view.lineEditDocumento.setInputMask("99999999")
            if a_entero(LeerIni(clave='cat_iva', key='WSFEv1'), 1) == 1: #si es Resp insc el contribuyente veo si teiene que emitira A o B
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
        # tipos = Tipocomprobantes.ComboTipoComp(tiporesp=a_entero(LeerIni(clave='cat_iva', key='WSFEv1'), 1))
        # tipo_cpte = [k for (k, v) in tipos.valores.iteritems() if v == self.view.cboComprobante.text()][0]
        tipo_cpte = self.view.cboComprobante.text()
        nro = FEv1().UltimoComprobante(tipo=tipo_cpte,
                                       ptovta=self.view.layoutFactura.lineEditPtoVta.text())
        self.tipo_cpte = tipo_cpte
        self.view.layoutFactura.lineEditNumero.setText(str(int(nro)+1).zfill(8))
        self.SumaTodo()

    def HabilitaVencimientos(self):
        """El periodo facturado solo existe para Factura C.

        Antes el grupo estaba siempre visible, con dos de las tres fechas
        deshabilitadas, ocupando el mismo lugar que los conceptos. Con
        Factura A o B no hay periodo que informar.
        """
        es_factura_c = str(self.view.cboComprobante.text()) == "11"
        con_servicios = self.view.checkBoxServicios.isChecked()
        self.view.MuestraPeriodo(es_factura_c)
        if es_factura_c:
            self.view.fechaDesde.setEnabled(con_servicios)
            self.view.fechaHasta.setEnabled(con_servicios)

    def AgregaArt(self):
        self.view.gridFactura.setRowCount(self.view.gridFactura.rowCount() + 1)
        self.view.gridFactura.ModificaItem(valor=1, fila=self.view.gridFactura.rowCount() + 1, col='Cant.')
        self.view.gridFactura.ModificaItem(valor=0, fila=self.view.gridFactura.rowCount() - 1, col='Unitario')
        self.view.gridFactura.ModificaItem(valor=21, fila=self.view.gridFactura.rowCount() - 1, col='IVA')
        self.SumaTodo()

    @staticmethod
    def _a_numero(valor):
        """Convierte a float aunque venga con el formato de la pantalla.

        La grilla guarda el numero aparte del texto (`UserRole`) y
        `ObtenerItem` lo devuelve crudo cuando existe. Pero cuando el operador
        **edita** una celda, Qt reemplaza el item por uno nuevo que solo tiene
        el texto, y ese texto va con separador de miles y coma decimal:
        "500,00". `float("500,00")` es ValueError, y reventaba al guardar la
        factura con un error que no dice nada de la celda que lo causo.

        Por eso todos los numeros que salen de la grilla pasan por aca.
        """
        if isinstance(valor, (int, float, decimal.Decimal)):
            return float(valor)
        texto = str(valor or "").strip().replace(".", "").replace(",", ".")
        if not texto:
            return 0.0
        try:
            return float(texto)
        except ValueError:
            raise ValueError("'{}' no es un numero".format(valor))

    def _normaliza_celda(self, fila, col):
        """Le deja el numero crudo a una celda recien editada.

        Al EDITAR, Qt reemplaza el item por uno nuevo que solo tiene el texto,
        y ese texto va con coma de miles. `ObtenerItem` lo devuelve tal cual y
        `float("500,00")` revienta. Se le guarda el numero con `setData` en la
        MISMA celda, sin reemplazarla.

        Ojo con no usar `ModificaItem` aca: hace `setItem` sobre una celda que
        esta en edicion, y Qt la dibuja avanzando hacia la fila siguiente --
        la fila se ve salir de la grilla mientras se tipea.
        """
        from PyQt5.QtCore import Qt

        grilla = self.view.gridFactura
        try:
            celda = grilla.item(fila, col)
        except Exception:
            return
        if celda is None:
            return
        texto = celda.text()
        if not str(texto).strip():
            return
        try:
            numero = self._a_numero(texto)
        except ValueError:
            return
        celda.setData(Qt.UserRole, numero)

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
            if self._a_numero(self.view.gridFactura.ObtenerItem(
                    fila=row, col='Unitario')) == 0:
                codigo = self.view.gridFactura.ObtenerItem(fila=row, col=1)
                if codigo:
                    art = Articulo.get_by_id(codigo)
                    self.view.gridFactura.ModificaItem(valor=art.preciopub,
                                               fila=self.view.gridFactura.currentRow(),
                                               col='Unitario')

        if key in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab]:
            # Al confirmar una celda editada, se la vuelve a escribir por
            # `ModificaItem` para que recupere el numero crudo. Qt la deja
            # solo con el texto, y ese texto va con coma de miles.
            if 0 <= col < self.view.gridFactura.columnCount() and row >= 0:
                self._normaliza_celda(row, col)
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
            if a_entero(LeerIni(clave='cat_iva', key='WSFEv1'), 1) == 6:
                self.view.gridFactura.ModificaItem(valor=21, fila=x, col='IVA')
            detalle = self.view.gridFactura.ObtenerItem(fila=x, col='Detalle')
            unitario = self._a_numero(self.view.gridFactura.ObtenerItem(fila=x, col='Unitario'))
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
            unitario = self._a_numero(self.view.gridFactura.ObtenerItem(fila=x, col='Unitario'))
            iva = self._a_numero(self.view.gridFactura.ObtenerItem(fila=x, col='IVA'))
            total = self._a_numero(cantidad) * self._a_numero(unitario)
            if a_entero(LeerIni(clave='cat_iva',
                           key='WSFEv1'), 1) == 1:  # si es Resp insc el contribuyente
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

            # if a_entero(LeerIni(clave='cat_iva',
            #                key='WSFEv1'), 1) == 1:  # si es Resp insc el contribuyente
            #     ivagral += total * iva / 100
            # totalgral += total
            subtotal += total

            self.view.gridFactura.ModificaItem(valor=total, fila=x, col='SubTotal')


        if a_entero(LeerIni(clave='cat_iva',
                       key='WSFEv1'), 1) == 1:  # si es Resp insc el contribuyente
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


        # Un solo lugar que calcula, guarda y pinta los tres totales. Antes
        # eran cuatro `setText` con `str(round(...))`, y el numero que se
        # guardaba en la cabecera era otro: `lineEditTotal.value()` devolvia
        # 1234.5 y lo que se veia era "1234.5" o "1234,50" segun como lo
        # formateara Qt. Ahora el numero vive en la vista y la etiqueta es
        # solo lo que se ve.
        self.view.ActualizaTotales(subtotal=subtotal, tributos=dgrgral,
                                   iva=ivagral,
                                   total=totalgral + ivagral + dgrgral,
                                   decimales=self.decimales)

    def cargar_venta_simple(self, cliente_id=None, renglones=None, forma_pago_id=None):
        if cliente_id:
            self.view.validaCliente.setText(str(cliente_id))
            self.CargaDatosCliente()

        if forma_pago_id:
            indice = self.view.cboFormaPago.findData(str(forma_pago_id))
            if indice >= 0:
                self.view.cboFormaPago.setCurrentIndex(indice)
            else:
                self.view.cboFormaPago.setText(str(forma_pago_id))

        self.view.gridFactura.setRowCount(0)
        for renglon in renglones or []:
            self.view.gridFactura.AgregaItem(items=[
                str(renglon.cantidad),
                str(renglon.codigo),
                renglon.detalle,
                str(renglon.precio_unitario),
                str(renglon.iva),
                str(renglon.cantidad * renglon.precio_unitario),
            ])

        self.SumaTodo()

    def cargar_desde_remito(self, remito_id):
        """Abre una factura con la mercaderia que ya salio con un remito.

        Lo unico que hace de mas que `cargar_venta_simple` es dejar anotado de
        que remito es, y esa es toda la razon de que este metodo exista: con
        `idremito` puesto, `GrabaFE` sabe que la mercaderia ya salio y no la
        vuelve a descontar. Sin esto habria que desvincularlo a mano, y nadie
        lo haria.
        """
        from decimal import Decimal

        from modelos.Remitos import DetalleRemito, Remito
        from controladores.venta_simple_totales import RenglonVenta

        remito = Remito.get_by_id(remito_id)
        detalles = list(DetalleRemito.select().where(
            DetalleRemito.remito == remito))

        self.idremito = remito.idremito
        self.cargar_venta_simple(
            cliente_id=remito.cliente_id,
            renglones=[
                RenglonVenta(
                    codigo=str(d.producto_id),
                    detalle=d.detalle or "",
                    cantidad=Decimal(str(d.cantidad or 0)),
                    precio_unitario=Decimal(str(d.precio or 0)),
                    iva=Decimal(str(d.tipo_iva.iva if d.tipo_iva_id else 21)),
                )
                for d in detalles
            ],
            forma_pago_id=remito.forma_pago_id,
        )
        return remito

    # Las etapas por las que pasa una emision, en el orden en que pasan. Se
    # muestran al usuario porque contra AFIP esto tarda, y una ventana muerta
    # sin explicacion hace pensar que la app se colgo.
    ETAPAS_EMISION = [
        "Comprobando los datos",
        "Preparando el numero de comprobante",
        "Autenticando en AFIP",
        "Conectando al servicio de facturacion",
        "Enviando la factura",
        "Obteniendo el CAE",
        "Guardando la factura",
    ]

    # Ventana de progreso abierta, si la hay. A nivel de clase para que
    # _etapa() no reviente si se llama a CreaFE() sin pasar por GrabaFactura.
    _progreso = None

    # El remito que documenta esta factura, si se esta facturando desde uno.
    # None es lo normal: la venta rapida factura sin remito, y ahi la factura
    # es la que descuenta el stock. Lo setea cargar_desde_remito() y es lo que
    # evita que una venta con remito baje el stock dos veces. Ver
    # libs/stock.py::aplica_factura, que es donde vive la regla.
    idremito = None

    # Candado del buscador de clientes. Ver buscar_cliente(): sin esto, al
    # abrirse el dialogo modal Qt le saca el foco al campo y eso vuelve a
    # entrar en el metodo con el primero todavia en la pila, abriendo un
    # segundo dialogo encima del primero. Es el mismo problema que resuelve
    # `_resolviendo_cliente` en la venta rapida.
    _buscando_cliente = False

    def GrabaFactura(self):
        """Emite la factura. Devuelve True si la factura quedo autorizada.

        Antes no devolvia nada y el unico que lo llamaba era el boton del
        formulario, que no necesita saber. Ahora tambien lo llama la venta
        rapida, que si: tiene que limpiar la pantalla si salio bien y
        dejarla con los renglones si salio mal.
        """
        if not self.Validacion():
            return False

        # Confirmacion antes de algo que no se puede deshacer: una factura
        # autorizada ante ARCA existe mas alla de esta app, y anularla es otro
        # tramite. El boton por defecto es cancelar.
        if not Ventanas.showConfirmation(
                "Emitir la factura",
                "La factura se va a autorizar ante ARCA y no se puede deshacer "
                "desde aca.\n\nRevise el importe y el cliente antes de confirmar.",
                textoOk="Emitir", textoCancelar="Volver a revisar"):
            return False

        self.view.btnGrabarFactura.setEnabled(False)
        self.SilenciarError = True
        try:
            # Los datos se leen ACa, en el hilo principal: la pantalla y la
            # base no se tocan desde el hilo de trabajo.
            datos = self._datos_emision()
            emitida = self._emitir_en_hilo(datos)
        finally:
            self.SilenciarError = False
            self.view.btnGrabarFactura.setEnabled(True)
            self._hilo = None
            self._worker = None
            self._progreso = None
        return emitida

    def _emitir_en_hilo(self, datos):
        """Emite en un hilo de trabajo y espera el resultado.

        Antes de arrancar el hilo, se cierran los datos de la pantalla y el
        boton queda deshabilitado, asi que no hay forma de que cambien
        mientras ARCA procesa. Es lo que hace seguro tomar la foto de los
        datos en un solo momento.

        Devuelve True solo si la factura quedo autorizada y guardada. Cada
        salida anticipada devuelve False, y el que se emite sin guardar
        tambien: autorizada sin guardar es un problema que hay que avisar, no
        una venta terminada.
        """
        estado = {"ok": False, "aviso": None}
        listo = threading.Event()

        def al_terminar(ok, aviso):
            # Llega al hilo principal: Qt encola las senales entre hilos.
            estado["ok"] = ok
            estado["aviso"] = aviso
            listo.set()

        with Ventanas.Progreso("Emitiendo la factura",
                               self.ETAPAS_EMISION) as barra:
            self._progreso = barra

            # Sin padre: ver la nota de la clase. La referencia la sostiene
            # self._worker hasta que el hilo termina.
            self._worker = _EmisionWorker(self, datos)
            self._worker.etapa.connect(barra.avanzar)
            self._worker.terminado.connect(al_terminar)

            self._hilo = QThread()
            self._worker.moveToThread(self._hilo)
            self._hilo.started.connect(self._worker.run)
            self._hilo.start()

            while not listo.wait(0.05):
                # El wait(0.05) devuelve solo y sigue ventilando la interfaz:
                # sin esto la ventana quedaria congelada, que es justo lo que
                # se vino a arreglar.
                QApplication.processEvents()
                if not self._hilo.isRunning():
                    break

            self._hilo.quit()
            self._hilo.wait(5000)      # 5 s sobran para un return limpio

        if estado["aviso"] is None:
            # El hilo murio sin devolver nada. Puede ser una caida de red o un
            # cierre de la ventana; en cualquier caso no se sabe si ARCA
            # autorizo, asi que NO se toca la base y se avisa con la duda
            # explícita, que es lo que hay que hacer con una factura dudosa.
            Ventanas.showError(
                LeerIni('nombre_sistema'),
                "No se pudo saber si la factura se autorizó.",
                que_hacer="Puede que ARCA la haya autorizado y el programa haya "
                          "cerrado antes de recibir la respuesta. NO la emita "
                          "de nuevo: entre en Comprobantes y vea si aparece. Si "
                          "aparece, reimprima el PDF desde Reimprimir factura; "
                          "si no aparece, llame y lo verificamos con el CAE.",
                detalle="El hilo de emisión terminó sin devolver resultado.")
            return False

        ok = self._aplicar_resultado(estado["ok"], estado["aviso"])

        if not ok:
            Ventanas.showError(
                LeerIni('nombre_sistema'),
                "No se pudo emitir la factura.",
                que_hacer="Revise el detalle. Si el problema es de "
                          "certificacion, corra Diagnostico desde "
                          "Configuracion. Si es un rechazo de ARCA, el codigo "
                          "de observacion esta en el detalle.",
                detalle=self._mensaje_error_emision())
            return False

        # Guardar la factura SIEMPRE en el hilo principal: peewee no es
        # thread-safe y esta es la unica parte que escribe en la base.
        with Ventanas.Progreso("Guardando la factura",
                               ["Guardando en la base"]) as barra:
            barra.avanzar("Guardando en la base")
            guardado = self.GrabaFE()
            if not guardado:
                Ventanas.showError(
                    LeerIni('nombre_sistema'),
                    "La factura se autorizó pero no se pudo guardar.",
                    que_hacer="La factura con CAE {} ya está autorizada en ARCA y "
                              "no se puede deshacer. Anótela y avise: se puede "
                              "cargar a mano, pero no la vuelva a emitir.".format(
                                  self.view.cae or "(sin CAE)"),
                    detalle=self._mensaje_error_emision())
                return False

        # La factura quedo autorizada y guardada: se cierra la pantalla, que ya
        # cumplio su parte. Cuando la pantalla nunca se mostro, cerrar una
        # ventana oculta no hace nada, y por eso se puede emitir desde la venta
        # rapida sin abrirla.
        self.view.Cerrar()
        return True

    def _etapa(self, nombre):
        """Avanza el progreso, si hay alguno abierto."""
        if self._progreso is not None:
            self._progreso.avanzar(nombre)

    def _mensaje_error_emision(self):
        partes = []
        rechazo = DeCodifica(getattr(self, "_error_afip", "") or "").strip()
        if rechazo:
            partes.append(rechazo)
        detalle = DeCodifica(getattr(self, "Excepcion", "") or "").strip()
        if not detalle:
            detalle = DeCodifica(getattr(self, "Traceback", "") or "").strip()
        if detalle:
            partes.append(detalle)
        if not partes:
            return "AFIP no respondio como se espera. Revise el log de errores."
        return "\n\n".join(partes)

    # -- Emision en dos hilos ------------------------------------------------
    #
    # La emision contra ARCA tarda y antes congelaba la ventana entera. Se
    # resuelve con un QThread, pero CreaFE no se puede mandar tal cual a otro
    # hilo porque mezcla tres cosas con reglas distintas:
    #
    #   - llamadas de red a ARCA: lentas, van bien en cualquier hilo
    #   - widgets: Qt no permite tocarlos desde otro hilo
    #   - la base: peewee NO es thread-safe
    #
    # Por eso quedo partida en tres partes. Lo unico que cruza al hilo es un
    # dict de datos planos:
    #
    #   _datos_emision()  corre en el hilo PRINCIPAL: lee la pantalla y la base
    #   _autorizar()      corre en el hilo de TRABAJO: solo habla con ARCA
    #   _aplicar()        corre en el hilo PRINCIPAL: escribe el resultado
    #
    # GrabaFE (que escribe la factura en la base) sigue en el hilo principal a
    # proposito, por lo de peewee.

    def _datos_emision(self):
        """Lee de la pantalla y de la base todo lo que hace falta para emitir.

        Corre en el hilo de la interfaz, a proposito. Devuelve datos planos: si
        se pasara el controlador entero al hilo de trabajo, ese terminaria
        tocando widgets y base desde alla, que es exactamente lo que no se
        puede hacer.
        """
        concepto_productos = self.view.checkBoxProductos.isChecked()
        concepto_servicios = self.view.checkBoxServicios.isChecked()
        documento = str(self.view.lineEditDocumento.text()).strip()
        # Los totales se leen de la vista, que los tiene en numero. Antes
        # eran `EntradaTexto` y se leia `.text()`, que devolvia "1234.5" con
        # punto decimal y sin miles: el PDF salia con el punto donde va la
        # coma.
        total = self.view.total_final
        tributos = self.view.total_tributos
        total_iva = self.view.total_iva
        fecha_cbte = self.view.lineEditFecha.getFechaSql()

        # La percepcion se lee de la base. Se resuelve aca y no en el hilo de
        # trabajo justamente por eso: peewee no es thread-safe.
        try:
            percepcion = self.cliente.percepcion
            percepcion_detalle = percepcion.detalle
            percepcion_alicuota = percepcion.porcentaje
        except Exception:
            percepcion_detalle = ""
            percepcion_alicuota = 0

        es_consumidor_final = self.cliente.tiporesp.idtiporesp == 3
        es_ri = a_entero(LeerIni(clave='cat_iva', key='WSFEv1'), 1) == 1

        if es_ri:
            imp_neto = str(round(float(total) - float(tributos)
                                - float(total_iva), 2))
        else:
            imp_neto = str(round(float(total), 2))

        datos = {
            "concepto_productos": concepto_productos,
            "concepto_servicios": concepto_servicios,
            "es_consumidor_final": es_consumidor_final,
            "documento": documento,
            "tipo_doc": self._tipo_documento(es_consumidor_final, documento),
            "tipo_cbte": self.tipo_cpte,
            "punto_vta": int(self.view.layoutFactura.lineEditPtoVta.value()),
            "cbt_desde": int(self.view.layoutFactura.lineEditNumero.value()),
            "imp_total": str(round(float(total), 2)),
            "imp_neto": imp_neto,
            "imp_iva": str(round(float(total_iva), 2)),
            "imp_trib": str(round(float(tributos), 2)),
            "imp_tot_conc": "0.00",
            "imp_op_ex": "0.00",
            "fecha_cbte": fecha_cbte,
            "moneda_id": "PES",
            "moneda_ctz": "1.000",
            "es_ri": es_ri,
            "netos": dict(self.netos or {}),
            "condicion_iva_receptor": self.cliente.tiporesp.condicion_iva_receptor_id,
            # Datos de NC/ND y FCE, que solo se usan en algunos comprobantes.
            "asociado_pto": self.view.layoutCpbteRelacionado.lineEditPtoVta.text(),
            "asociado_nro": self.view.layoutCpbteRelacionado.lineEditNumero.text(),
            "tiene_asociado": bool(self.view.layoutCpbteRelacionado.numero),
            "cbu": LeerIni("CBUFCE", key='FACTURA'),
            "alias": LeerIni("ALIASFCE", key='FACTURA'),
            "percepcion_detalle": percepcion_detalle,
            "percepcion_alicuota": percepcion_alicuota,
            "cuit": cuit_emisor(),
        }

        if concepto_productos and concepto_servicios:
            datos["concepto"] = "PRODUCTOYSERVICIOS"
        elif concepto_servicios:
            datos["concepto"] = "SERVICIOS"
        else:
            datos["concepto"] = "PRODUCTOS"

        # Fechas del periodo facturado, que solo existen si el comprobante es
        # de servicios.
        if datos["concepto"] in ("SERVICIOS", "PRODUCTOYSERVICIOS"):
            datos["fecha_serv_desde"] = self.view.fechaDesde.getFechaSql()
            datos["fecha_serv_hasta"] = self.view.fechaHasta.getFechaSql()
            datos["fecha_venc_pago"] = fecha_cbte
        else:
            datos["fecha_serv_desde"] = ""
            datos["fecha_serv_hasta"] = ""
            datos["fecha_venc_pago"] = ""

        if self.tipo_cpte in Constantes.COMPROBANTES_FCE:
            datos["fecha_venc_pago"] = fecha_cbte

        return datos

    @staticmethod
    def _tipo_documento(es_consumidor_final, documento):
        """96 = DNI, 80 = CUIT, 99 = sin identificar."""
        if es_consumidor_final:
            return 99 if documento in ("0", "") else 96
        return 80

    def _autorizar(self, datos, avisar=None):
        """Habla con ARCA. Corre en el hilo de trabajo.

        NO toca la base ni ningun widget: solo llamadas de red. `avisar` es la
        forma de contar las etapas sin tocar el dialogo de progreso, que
        pertenece al hilo de la interfaz.

        Devuelve (ok, resultado) con un dict de datos, nunca escribe en la
        pantalla.
        """
        if avisar is None:
            avisar = self._etapa

        aviso = {"ok": False, "cae": "", "resultado": "", "vencimiento": "",
                 "error": ""}

        avisar("Preparando el numero de comprobante")
        self.ObtieneNumeroFacturaSinVista(datos)

        wsfev1 = FEv1()
        avisar("Autenticando en ARCA")
        ta = wsfev1.Autenticar()
        if not ta:
            aviso["error"] = "ARCA no devolvio ticket de acceso."
            return False, aviso
        wsfev1.SetTicketAcceso(ta)
        wsfev1.Cuit = datos["cuit"]

        avisar("Conectando al servicio de facturacion")
        if LeerIni(clave='homo') == "S":
            conectado = wsfev1.Conectar("")
        else:
            conectado = wsfev1.Conectar(
                "", LeerIni(clave="url_prod", key="WSFEv1"), cacert=None)
        if not conectado:
            aviso["error"] = DeCodifica(wsfev1.ErrMsg) or \
                "No se pudo conectar con el servicio de facturacion."
            return False, aviso

        concepto = {
            "PRODUCTOS": wsfev1.PRODUCTOS,
            "SERVICIOS": wsfev1.SERVICIOS,
            "PRODUCTOYSERVICIOS": wsfev1.PRODUCTOYSERVICIOS,
        }[datos["concepto"]]

        avisar("Enviando la factura")
        ok = self.crear_factura_wsfe(
            wsfev1, concepto, datos["tipo_doc"],
            datos["documento"].replace("-", ""), datos["tipo_cbte"],
            datos["punto_vta"], datos["cbt_desde"], datos["cbt_desde"],
            datos["imp_total"], datos["imp_tot_conc"], datos["imp_neto"],
            datos["imp_iva"], datos["imp_trib"], datos["imp_op_ex"],
            datos["fecha_cbte"], datos["fecha_venc_pago"],
            datos["fecha_serv_desde"], datos["fecha_serv_hasta"],
            datos["moneda_id"], datos["moneda_ctz"])

        if not ok:
            aviso["error"] = DeCodifica(getattr(wsfev1, "ErrMsg", "")) or \
                "No se pudo armar el comprobante."
            return False, aviso

        # Agregar comprobantes asociados (si es una NC / ND).
        if datos["tipo_cbte"] in [2, 3, 7, 8, 12, 13]:
            wsfev1.AgregarCmpAsoc(datos["tipo_cbte"], datos["asociado_pto"],
                                  datos["asociado_nro"])

        if datos["tipo_cbte"] in Constantes.COMPROBANTES_FCE:
            wsfev1.AgregarOpcional(2101, datos["cbu"])
            wsfev1.AgregarOpcional(2102, datos["alias"])
            if datos["tiene_asociado"]:
                wsfev1.AgregarCmpAsoc(
                    91, datos["asociado_pto"], datos["asociado_nro"],
                    a_entero(LeerIni(clave='cat_iva', key='WSFEv1'), 1),
                    FechaMysql())

        if round(float(datos["imp_trib"]), 3) != 0:
            base_imp = round(float(datos["imp_total"])
                             - float(datos["imp_trib"])
                             - float(datos["imp_iva"]), 2)
            wsfev1.AgregarTributo(
                tributo_id=wsfev1.ID_IMP_PCIAL, desc=datos["percepcion_detalle"],
                base_imp=base_imp, alic=datos["percepcion_alicuota"],
                importe=str(round(float(datos["imp_trib"]), 2)))

        # Solo si es responsable inscripto se informa el detalle de IVA.
        if datos["es_ri"]:
            for alicuota, neto in datos["netos"].items():
                if neto != 0:
                    codigo = FEv1().TASA_IVA[str(float(alicuota))]
                    wsfev1.AgregarIva(codigo, round(neto, 2),
                                      round(neto * float(alicuota) / 100, 2))

        avisar("Obteniendo el CAE")
        cae = wsfev1.CAESolicitar()

        if wsfev1.ErrMsg:
            aviso["error"] = DeCodifica(wsfev1.ErrMsg).strip()
            return False, aviso

        if wsfev1.Resultado == "R":
            aviso["error"] = "ARCA rechazo la factura: {}".format(
                DeCodifica(wsfev1.Obs).strip())
            return False, aviso

        aviso["ok"] = True
        aviso["cae"] = cae
        aviso["resultado"] = wsfev1.Resultado
        aviso["vencimiento"] = wsfev1.Vencimiento
        return True, aviso

    def _aplicar_resultado(self, ok, aviso):
        """Escribe el resultado en la pantalla. Hilo principal."""
        self._error_afip = aviso.get("error", "") if not ok else ""
        if ok:
            # Un solo metodo que arma numero, CAE, vencimiento y estado. Antes
            # eran tres `setText` en un grupo gris abajo a la izquierda, al
            # lado del boton, y el operador no tenia forma de ver que la
            # factura ya habia salido sin buscarlo.
            self.view.MuestraAutorizacion(
                numero=aviso.get("numero", ""),
                cae=aviso["cae"],
                resultado=aviso["resultado"],
                vencimiento=self._vencimiento_legible(aviso.get("vencimiento", "")),
                vencimiento_sql=aviso.get("vencimiento", ""))
        else:
            self.view.MuestraAutorizacion(
                numero=aviso.get("numero", ""),
                cae="", resultado=aviso.get("resultado", ""),
                vencimiento="", autorizada=False)
        return ok

    @staticmethod
    def _vencimiento_legible(vencimiento):
        """'20261014' -> '14/10/2026'. Lo que se ve en la pantalla."""
        texto = str(vencimiento or "").strip()
        if len(texto) == 8 and texto.isdigit():
            return "{}/{}/{}".format(texto[6:8], texto[4:6], texto[0:4])
        return texto

    @staticmethod
    def _vencimiento_a_fecha(vencimiento):
        """'20261014' -> date(2026, 10, 14). Lo que se guarda en la cabecera.

        Antes salia de `fechaVencCAE.date().toPyDate()`, con un `Fecha` de Qt
        que ademas se llenaba con `format="Ymd"`. Con el vencimiento en un
        texto de la vista, la conversion se hace aca, en un solo lugar, y no
        hay dos formatos dando vueltas.
        """
        from datetime import datetime

        texto = str(vencimiento or "").strip()
        if len(texto) == 8 and texto.isdigit():
            try:
                return datetime.strptime(texto, "%Y%m%d").date()
            except ValueError:
                return None
        return None

    def ObtieneNumeroFacturaSinVista(self, datos):
        """Pide a ARCA el ultimo comprobante y deja el siguiente en la pantalla.

        Va separado de ObtieneNumeroFactura() porque este corre en el hilo de
        trabajo y no puede tocar widgets hasta volver al principal. La escritura
        en la pantalla se hace despues, en _aplicar_numero().
        """
        nro = FEv1().UltimoComprobante(tipo=datos["tipo_cbte"],
                                       ptovta=datos["punto_vta"])
        try:
            nro = int(nro)
        except (TypeError, ValueError):
            nro = 0
        datos["cbt_desde"] = nro + 1
        return nro + 1

    @inicializar_y_capturar_excepciones
    def CreaFE(self, *args, **kwargs):
        """Emite el comprobante. Se usa cuando se emite sin hilo."""
        datos = self._datos_emision()
        ok, aviso = self._autorizar(datos)
        return self._aplicar_resultado(ok, aviso)

    def onEditingFinishedDocumento(self):
        if self.cliente.tiporesp.idtiporesp != 3:
            if not validar_cuit(self.view.lineEditDocumento.text()):
                Ventanas.showAlert("Sistema", "ERROR: CUIT/CUIL no valido. Verifique!!!")

    @inicializar_y_capturar_excepciones
    def GrabaFE(self, *args, **kwargs):
        """Guarda la factura ya autorizada y descuenta el stock.

        Que va adentro de la transaccion y que no
        ----------------------------------------
        Adentro: la cabecera, los renglones, los comprobantes relacionados y
        los movimientos de stock. O se guarda todo o no se guarda nada.

        Afuera: ImprimeFactura. Una factura autorizada ante ARCA existe mas
        alla de esta app, y revertirla porque el PDF no salio seria peor que
        un PDF que hay que reimprimir. Antes cada `save()` era su propia
        transaccion: un renglon que fallaba dejaba la cabecera guardada con la
        mitad de los items, y con stock en el camino eso es una mercaderia que
        salio y no se sabe de donde.
        """
        self.view.layoutFactura.AssignNumero()
        cabfact = Cabfact()
        cabfact.tipocomp = self.tipo_cpte
        cabfact.cliente = self.cliente.idcliente
        cabfact.fecha = self.view.lineEditFecha.date().toPyDate()
        cabfact.numero = self.view.layoutFactura.numero
        cabfact.neto = sum([i for i in self.netos.values()])
        cabfact.netoa = self.netos[21]
        cabfact.netob = self.netos[10.5]
        cabfact.iva = self.view.total_iva
        cabfact.total = self.view.total_final
        formpago = Formapago.get_by_id(self.view.cboFormaPago.text())
        # if self.view.cboFormaPago.text() == 'Contado':
        #     cabfact.saldo = 0.00
        # else:
        #     cabfact.saldo = self.view.total_final
        if formpago.ctacte:
            cabfact.saldo = self.view.total_final
        else:
            cabfact.saldo = 0
        cabfact.tipoiva = self.cliente.tiporesp.idtiporesp
        cabfact.cajero = 1 #por defecto cajero
        # cabfact.formapago = 1 if self.view.cboFormaPago.text() == 'Contado' else 2
        cabfact.formapago = formpago.idformapago
        cabfact.percepciondgr = self.view.total_tributos
        cabfact.nombre = self.view.lblNombreCliente.text()
        cabfact.domicilio = self.view.lineEditDomicilio.text()
        cabfact.cae = self.view.cae
        # La fecha del vencimiento se convierte aca, en un solo lugar. Antes
        # salia de un `Fecha` de Qt que se llenaba con `format="Ymd"`, y el
        # mismo dato estaba en dos formatos dando vueltas por la pantalla.
        venc = self._vencimiento_a_fecha(self.view.vencimiento_cae_sql)
        cabfact.venccae = venc or date.today()
        cabfact.concepto = self.concepto
        cabfact.desde = self.view.fechaDesde.date().toPyDate()
        cabfact.hasta = self.view.fechaHasta.date().toPyDate()
        # El remito se guarda en la cabecera y no se deduce: es lo unico que
        # permite, mas adelante, saber que esa mercaderia ya salio y que la
        # factura no tiene que volver a descontarla.
        cabfact.idremito = self.idremito

        detalles = []
        with db.atomic():
            cabfact.save()

            for x in range(self.view.gridFactura.rowCount()):
                codigo = self.view.gridFactura.ObtenerItem(fila=x, col='Codigo')
                cantidad = self._a_numero(self.view.gridFactura.ObtenerItem(fila=x, col='Cant.'))
                importe = self._a_numero(self.view.gridFactura.ObtenerItem(fila=x, col='SubTotal'))
                iva = self._a_numero(self.view.gridFactura.ObtenerItem(fila=x, col='IVA'))
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
                    if self.view.total_tributos > 0:
                        detfact.montodgr = importe * float(self.cliente.percepcion.porcentaje) / 100
                    else:
                        detfact.montodgr = 0.00
                    detfact.montomuni = 0.00
                    detfact.descad = detalle
                    detfact.detalle = detalle[:40]
                    detfact.descuento = 0.00
                    detfact.save()
                    detalles.append(detfact)
                except peewee.DoesNotExist:
                    # Un renglon cuyo articulo no esta sigue sin guardarse,
                    # como antes. Lo que cambia es que no se guarda a medias:
                    # la transaccion revierte el conjunto.
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

            # El stock, adentro de la misma transaccion que la factura. Acá
            # va, y no en VentaSimple, porque las tres pantallas que emiten
            # pasan por este metodo: la rapida, la de emision y la que se
            # abre desde un remito.
            lado = TipoComprobante.get_or_none(
                TipoComprobante.codigo == self.tipo_cpte)
            if lado is not None:
                stock.aplica_factura(
                    detalles,
                    idcabfact=cabfact.idcabfact,
                    idremito=self.idremito,
                    lado=lado.lado,
                )

        # Afuera de la transaccion a proposito: la factura ya esta guardada y
        # autorizada. Un PDF que no sale se reimprime; una factura deshecha
        # hay que anularla con otro tramite.
        self.ImprimeFactura(idcabecera=cabfact.idcabfact)
        return True

    def _pdf_generado(self, salida, ok, pyfpdf, cabfact, motivo=None):
        """Se genero el PDF? Si no, avisar con el CAE y devolver False.

        El chequeo tiene que ser el resultado real de la escritura, no la
        existencia del archivo.

        Por que no alcanza con que el archivo este
        ------------------------------------------
        Antes se aceptaba que el archivo existiera. Con fpdf2 no se puede
        pedir el valor de retorno de `GenerarPDF` (`Template.render()` esta
        anotado -> None, escribe el archivo y no devuelve nada; el envoltorio
        de pyfepdf se come la excepcion), asi que la existencia del archivo
        era la unica prueba disponible. Y no alcanza: fpdf2 abre el archivo de
        salida en modo escritura antes de escribir una linea, asi que si el
        destino esta abierto en un visor, el archivo se trunca a CERO bytes y
        recien ahi falla. El comprobante anterior se perdia, quedaba un
        archivo vacio y, como existia, la app reportaba exito.

        Eso se reprodujo con Foxit PDF Reader abierto: `PermissionError` en
        `Path(name).write_bytes(self.buffer)`, archivo de 0 bytes, sin aviso.

        Ahora el PDF se arma a un temporal y se pasa al destino recien
        terminado (`escribir_pdf`), asi que `ok` es el resultado real de la
        escritura y el archivo anterior nunca se toca si algo falla.

        Se avisa con el CAE porque es lo que hace falta para volver a imprimir
        la factura despues, desde Reimprimir factura.
        """
        if ok:
            return True

        # Lo mas comun: un visor de PDF tiene el comprobante abierto y Windows
        # no deja reemplazarlo. Foxit lo hace siempre, porque ademas corre
        # como instancia unica.
        bloqueado = bool(motivo) and "no se pudo reemplazar" in motivo
        Ventanas.showError(
            LeerIni('nombre_sistema'),
            "La factura se autorizo pero no se pudo generar el PDF.",
            que_hacer=("Cerrá el comprobante {} que tenés abierto en el visor de "
                       "PDF y volvé a imprimirlo. No se toco el archivo "
                       "anterior. La factura {} con CAE {} ya esta autorizada en "
                       "ARCA y no se puede deshacer: no la vuelvas a emitir, ARCA "
                       "no permite dos comprobantes iguales.".format(
                           os.path.basename(salida),
                           getattr(cabfact, "numero", "?"),
                           self._cae_de_pantalla())
                       if bloqueado else
                       "La factura {} con CAE {} ya esta autorizada en ARCA y no "
                       "se puede deshacer. Para volver a armar el PDF, corre "
                       "Diagnostico desde Configuracion y despues usa Reimprimir "
                       "factura. No la vuelvas a emitir: ARCA no permite dos "
                       "comprobantes iguales.".format(
                           getattr(cabfact, "numero", "?"),
                           self._cae_de_pantalla())),
            detalle="ProcesarPlantilla: {}\nArchivo esperado: {}\n"
                    "Motivo: {}\nExcepcion: {}\nTraceback: {}".format(
                        ok,
                        salida,
                        motivo,
                        DeCodifica(getattr(pyfpdf, "Excepcion", "") or ""),
                        DeCodifica(getattr(pyfpdf, "Traceback", "") or "")))
        return False

    def _cae_de_pantalla(self):
        """El CAE que se esta mostrando, o un texto si todavia no esta."""
        try:
            return self.view.cae or "(sin CAE en pantalla)"
        except Exception:
            return "(sin CAE en pantalla)"

    @inicializar_y_capturar_excepciones
    def ImprimeFactura(self, idcabecera = None, mostrar = True, *args, **kwargs):
        """Imprime una factura ya guardada.

        No hace nada raro: carga el comprobante y se lo pasa a
        _armar_comprobante, que es el que arma el PDF. La vista previa del
        diseno usa ese mismo metodo con datos de mentira, para que lo que el
        cliente ve sea exactamente lo que sale impreso.
        """
        if not idcabecera:
            return
        cabfact = Cabfact().get_by_id(idcabecera)
        return self._armar_comprobante(cabfact, mostrar=mostrar)

    def _armar_comprobante(self, cabfact, salida=None, mostrar=True,
                           renglones=None):
        """Arma el PDF de un comprobante. No escribe nada en la base.

        `salida` es donde se escribe. Si no se pasa, va a
        facturas/<tipo>-<numero>.pdf, que es donde la deja una impresion normal.

        `renglones` son los items del comprobante. Si no se pasan, se buscan en
        detfact por el id del comprobante, como siempre. Se pasan solo para la
        vista previa del diseno, que arma un comprobante de mentira y no puede
        meter filas en la base de verdad.
        """
        print("imprimir factura {}".format(cabfact.numero))
        pyfpdf = FEPDF()
        #cuit del emisor
        pyfpdf.CUIT = cuit_emisor()
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
            iva_id = 5 #código para alícuota del 21 %
            base_imp = cabfact.netoa #importe neto sujeto a esta alícuota
            importe = cabfact.netoa * 21 / 100 #importe liquidado de iva
            ok = pyfpdf.AgregarIva(iva_id, base_imp, importe)

        if cabfact.netob != 0:
            iva_id = 4  # código para alícuota del 10.5 %
            base_imp = cabfact.netob  # importe neto sujeto a esta alícuota
            importe = cabfact.netob * 10.5 / 100  # importe liquidado de iva
            ok = pyfpdf.AgregarIva(iva_id, base_imp, importe)

        if cabfact.netoa == 0 and cabfact.netob == 0:
            iva_id = 3  # código para alícuota del 21 %
            base_imp = cabfact.netob  # importe neto sujeto a esta alícuota
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

        if renglones is None:
            renglones = Detfact().select().where(
                Detfact.idcabfact == cabfact.idcabfact)
        for d in renglones:
            #Agrego detalles de cada item de la factura:
            u_mtx = 0 #unidades
            cod_mtx = "" #código de barras
            codigo = d.idarticulo.idarticulo #codigo interno a imprimir(ej. "articulo")
            ds = d.descad.strip()
            qty = d.cantidad #cantidad
            umed = 7 #código de unidad de medida(ej. 7 para"unidades")
            precio = d.precio #precio neto(A) o iva incluido(B)
            bonif = 0 #importe de descuentos
            iva_id = FEv1().TASA_IVA[str(float(d.tipoiva.iva))] #códigopara alícuota del 21 %
            imp_iva = d.montoiva #importe liquidado deiva
            importe = d.precio * d.cantidad  #importe total del item
            despacho = "" #numero de despacho de importación
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
        # El CUIT del emisor va SOLO, sin el rotulo pegado y con guiones.
        #
        # Antes se imprimia 'CUIT: 20123456789' en un unico campo. Mal por dos
        # motivos: el rotulo mezclado con el dato hace que el campo no se pueda
        # leer como numero (y hay gente que los copia de la factura), y el
        # numero sin guiones no es como se muestra un CUIT en un comprobante
        # fiscal. El rotulo ahora va en su propio campo del formato (CUIT.L),
        # como ya pasa con Fecha, Direccion, Localidad, etc.
        # Pie de la pagina: credito de quien hizo el programa.
        # Va aca y no en el bloque del emisor, porque el bloque del
        # emisor identifica a QUIEN FACTURA, y ese es el cliente.
        ok = pyfpdf.AgregarDato("creditoSoftware", Constantes.CREDITO_SOFTWARE)
        ok = pyfpdf.AgregarDato("CUIT", formato_cuit(cuit_emisor()))
        ok = pyfpdf.AgregarDato("IIBB", LeerIni(clave='iibb', key='FACTURA'))
        ok = pyfpdf.AgregarDato("IVA", "Condicion frente al IVA: {}".format(LeerIni(clave='iva', key='FACTURA')))
        ok = pyfpdf.AgregarDato("INICIO", "Fecha inicio actividades: {}".format(LeerIni(clave='inicio', key='FACTURA')))

        pyqr = PyQRv1()
        pyqr.CrearArchivo()
        ver = 1
        fecha = FormatoFecha(cabfact.desde, formato='afip')
        cuit = ParamSist.ObtenerParametro("CUIT_EMPRESA").replace('-', '')
        if not cuit:
            cuit = cuit_emisor()
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
        url = pyqr.GenerarImagen(
            ver, fecha, cuit, pto_vta, tipo_cmp, nro_cmp,
            importe, moneda, ctz, tipo_doc_rec, nro_doc_rec,
            tipo_cod_aut, cod_aut
        )
        pyfpdf.AgregarDato("QR", pyqr.Archivo)

        if int(cabfact.tipocomp.codigo) in Constantes.COMPROBANTES_FCE: #si es una FCE
            pyfpdf.AgregarDato('CBUFCE', LeerIni('CBUFCE', key='FACTURA'))
            pyfpdf.AgregarDato('ALIASFCE', LeerIni('ALIASFCE', key='FACTURA'))
            pyfpdf.AgregarDato('nombre_condvta', Constantes.COND_VTA['T'])
            ruta_formato = ubicacion_sistema() + "/plantillas/factura-fce.csv"
            ok = pyfpdf.CargarFormato(ruta_formato)
        else:
            #Cargo el formato desde el archivo CSV(opcional)
            #(carga todos los campos a utilizar desde la planilla)
            # ok = pyfpdf.CargarFormato(ubicacion_sistema() + "/plantillas/factura.csv")
            config_marca = cargar_config_marca_factura()
            formato = obtener_formato_factura(os.getcwd(), config_marca, "plantillas/factura_qr.csv")
            ok = pyfpdf.CargarFormato(str(formato))
            aplicar_marca_factura(pyfpdf, os.getcwd(), config_marca)

        # Si el formato no cargo, NO se sigue de largo. CargarFormato se come la
        # excepcion y devuelve False, y antes el resultado no se miraba: se
        # armaba la plantilla con un formato vacio y el error terminaba
        # apareciendo lineas mas abajo como 'no se pudo generar el PDF', sin
        # relacion con la causa real, que era un archivo que no existe.
        if not ok:
            Ventanas.showError(
                LeerIni('nombre_sistema'),
                "No se encontro la plantilla de la factura.",
                que_hacer="Falta el archivo {}. Esta en el programa, asi que "
                          "lo mas probable es que la instalacion este "
                          "incompleta: vuelva a instalar.".format(
                              os.path.basename(str(ruta_formato))),
                detalle="CargarFormato devolvio False para {}".format(
                    ruta_formato))
            return False
        #Creo plantilla para esta factura(papel A4vertical):

        if LeerIni(clave='homo') == 'S':
            pyfpdf.AgregarCampo("homo", 'T', 150, 350, 0, 0,
                              size=70, rotate=45, foreground=0x808080, priority=-1, text="HOMOLOGACION")
        papel = "A4" #o "letter" para carta, "legal" para oficio
        orientacion = "portrait" #o landscape(apaisado)
        ok = pyfpdf.CrearPlantilla(papel, orientacion)
        # Las plantillas de pyfepdf alinean con "D" (derecha) e "I"
        # (izquierda), codigos que existian en fpdf 1.7 y que fpdf2 no
        # entiende. Sin esta traduccion el PDF no se genera y la factura queda
        # autorizada en ARCA sin documento. Ver libs/fpdf_compat.py.
        _alineados, _fuentes, _fondos = fpdf_compat.normalizar_plantilla(pyfpdf)
        if _alineados or _fuentes or _fondos:
            # Los fondos importan mas de lo que parecen: con los valores
            # heredados de fpdf 1.7 la factura salia con la pagina negra.
            logging.debug(
                "plantilla normalizada para fpdf2: %s alineaciones, %s fuentes, "
                "%s fondos heredados puestos en blanco",
                _alineados, _fuentes, _fondos)
        num_copias = a_entero(LeerIni(clave='num_copias', key='FACTURA'), 1) #original, duplicado y triplicado
        lineas_max = 24 #cantidad de linas de items por página
        qty_pos = "izq" #(cantidad a la izquierda de la descripción del artículo)
        #Proceso la plantilla
        ok = pyfpdf.ProcesarPlantilla(num_copias, lineas_max, qty_pos)
        if not ok:
            logging.error("ProcesarPlantilla fallo para la factura %s: %s",
                          cabfact.numero, getattr(pyfpdf, "Excepcion", ""))

        # El PDF se arma a un temporal y recien despues se pasa al destino. Si
        # el destino esta abierto en un visor, escribirlo directo lo trunca a
        # cero bytes y se pierde el comprobante anterior. Ver escribir_pdf.
        try:
            if salida is None:
                salida = join('facturas', "{}-{}.pdf".format(
                    cabfact.tipocomp.nombre.replace(" ", "_"), cabfact.numero))
            generado, salida, motivo = escribir_pdf(pyfpdf.GenerarPDF, salida)
        except Exception as error:
            # Si la ruta no se puede escribir, se cae al archivo que le
            # sugiera el sistema. Es lo que hacia antes, con la diferencia de
            # que la vista previa ya trae su propia ruta.
            cArchivo = getFileName("factura", False)
            salida = cArchivo + '.pdf'
            generado, salida, motivo = escribir_pdf(pyfpdf.GenerarPDF, salida)
        ok = generado

        # Que exista el archivo es lo unico que prueba que se genero.
        #
        # Antes se devolvia True siempre. Si la plantilla falla (por ejemplo
        # porque la libreria de PDF no es la que espera el proyecto) la
        # factura queda IGUAL autorizada en ARCA, pero sin documento: el
        # usuario cerraba creyendo que habia hecho todo y el cliente no
        # recibia nada. Es el peor resultado posible, porque una factura
        # autorizada no se puede deshacer.
        #
        # Aca se avisa, y se avisa con el CAE, que es lo que hace falta para
        # volver a imprimirla despues desde Reimprimir factura.
        if not self._pdf_generado(salida, ok, pyfpdf, cabfact, motivo):
            self.facturaGenerada = None
            return False

        #Abro el visor de PDF y muestro lo generado
        imprimir = False #cambiar a True para que lo envie directo a laimpresora
        if mostrar:
            abierto = abrir_pdf(salida, imprimir)
            if not abierto:
                Ventanas.showError(
                    LeerIni('nombre_sistema'),
                    "La factura se genero pero no se pudo abrir.",
                    que_hacer="El archivo esta en {}. Abrilo con doble click, "
                              "o probá con otro programa para los archivos PDF. "
                              "La factura {} no se vuelve a emitir.".format(
                                  os.path.abspath(salida), cabfact.numero),
                    detalle="No se pudo abrir con el navegador ni con el "
                            "visor del sistema: {}".format(salida))

        self.facturaGenerada = salida
        return True

    def Validacion(self):
        retorno = True
        if not self.view.validaCliente.text():
            Ventanas.showAlert(LeerIni('nombre_sistema'), "ERROR: No se ha especificado un cliente valido")
            retorno = False

        for x in range(self.view.gridFactura.rowCount()):
            iva = self._a_numero(self.view.gridFactura.ObtenerItem(fila=x, col='IVA'))
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

    def crear_factura_wsfe(self, wsfev1, concepto=1, tipo_doc=80, nro_doc='', tipo_cbte=1, punto_vta=0,
                           cbt_desde=0, cbt_hasta=0, imp_total=0.0, imp_tot_conc=0.0, imp_neto=0.0,
                           imp_iva=0.0, imp_trib=0.0, imp_op_ex=0.0, fecha_cbte='',
                           fecha_venc_pago=None, fecha_serv_desde=None, fecha_serv_hasta=None,
                           moneda_id='PES', moneda_ctz='1.000'):
        condicion_iva_receptor_id = self.cliente.tiporesp.condicion_iva_receptor_id
        return wsfev1.CrearFactura(
            concepto, tipo_doc, nro_doc, tipo_cbte, punto_vta,
            cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
            imp_iva, imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
            fecha_serv_desde, fecha_serv_hasta, moneda_id, moneda_ctz,
            cancela_misma_moneda_ext='N',
            condicion_iva_receptor_id=condicion_iva_receptor_id)

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
