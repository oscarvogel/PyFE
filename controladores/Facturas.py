# coding=utf-8
import decimal
import logging
import os

import peewee
import threading

from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication
from os.path import join

from controladores.ControladorBase import ControladorBase
from controladores.FCE import WsFECred
from controladores.FE import FEv1, PyQRv1
from controladores.FacturaBranding import aplicar_marca_factura, cargar_config_marca_factura, obtener_formato_factura
from libs import Ventanas, Constantes
from libs import fpdf_compat
from libs.instalacion import cuit_emisor
from libs.Utiles import (LeerIni, validar_cuit, FechaMysql, ubicacion_sistema,
                         inicializar_y_capturar_excepciones, DeCodifica, imagen,
                         getFileName, FormatoFecha, formato_cuit, a_entero)
from modelos.Articulos import Articulo
from modelos.Cabfact import Cabfact
from modelos.Clientes import Cliente
from modelos.CpbteRelacionado import CpbteRel
from modelos.Detfact import Detfact
from modelos.Formaspago import Formapago
from modelos.Impuestos import Impuesto
from modelos.ParametrosSistema import ParamSist
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
            if a_entero(LeerIni(clave='cat_iva', key='WSFEv1'), 1) == 6:
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


        self.view.textSubTotal.setText(str(round(subtotal, self.decimales)))
        self.view.lineEditTributos.setText(str(round(dgrgral, self.decimales)))
        self.view.lineEditTotalIVA.setText(str(round(ivagral, self.decimales)))
        self.view.lineEditTotal.setText(str(round(totalgral + ivagral + dgrgral, 2)))

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
                                  self.view.lineditCAE.text() or "(sin CAE)"),
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
        total = self.view.lineEditTotal.text()
        tributos = self.view.lineEditTributos.text()
        total_iva = self.view.lineEditTotalIVA.text()
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
            "imp_total": total,
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
            self.view.lineditCAE.setText(aviso["cae"])
            self.view.lineEditResultado.setText(aviso["resultado"])
            self.view.fechaVencCAE.setFecha(aviso["vencimiento"], format="Ymd")
        return ok

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
        formpago = Formapago.get_by_id(self.view.cboFormaPago.text())
        # if self.view.cboFormaPago.text() == 'Contado':
        #     cabfact.saldo = 0.00
        # else:
        #     cabfact.saldo = self.view.lineEditTotal.value()
        if formpago.ctacte:
            cabfact.saldo = self.view.lineEditTotal.value()
        else:
            cabfact.saldo = 0
        cabfact.tipoiva = self.cliente.tiporesp.idtiporesp
        cabfact.cajero = 1 #por defecto cajero
        # cabfact.formapago = 1 if self.view.cboFormaPago.text() == 'Contado' else 2
        cabfact.formapago = formpago.idformapago
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
        return True

    def _pdf_generado(self, salida, ok, pyfpdf, cabfact):
        """Existe el PDF? Si no, avisar con el CAE y devolver False.

        Que exista el archivo es lo unico que prueba que se genero. Antes
        ImprimeFactura devolvia True siempre: si la plantilla fallaba (por
        ejemplo porque la libreria de PDF no es la que espera el proyecto) la
        factura quedaba IGUAL autorizada en ARCA, pero sin documento. El
        usuario cerraba creyendo que habia hecho todo y el cliente no recibia
        nada, que es el peor resultado posible porque una factura autorizada
        no se puede deshacer.

        Se avisa con el CAE porque es lo que hace falta para volver a imprimir
        la factura despues, desde Reimprimir factura.
        """
        # El archivo es lo que prueba que se genero, y es lo UNICO que
        # prueba, porque con fpdf2 GenerarPDF devuelve None: Template.render()
        # esta anotado -> None, escribe el archivo y no devuelve nada. Pedir
        # ese valor de retorno hacia que TODAS las facturas se reportaran como
        # fallidas, con el PDF generado al lado. Con fpdf 1.7 render() si
        # devolvia algo, por eso el chequeo se escribio con `ok and ...` y no
        # se noto el cambio al migrar a fpdf2.
        #
        # La excepcion es un False explicito: si la libreria dice que fallo,
        # se avisa aunque el archivo exista. Con fpdf2 eso no pasa (el
        # envoltorio se come la excepcion y devuelve None igual), pero si
        # alguna vez GenerarPDF vuelve a devolver algo, el False sigue siendo
        # una senal que hay que respetar.
        #
        # Aceptar None con archivo no es arriesgado: la salida es
        # `facturas/<tipo>-<numero>.pdf`, determinista por numero de
        # comprobante, y ARCA no reutiliza numeros. Un archivo con ese nombre
        # es siempre el PDF de esa factura, y el escenario del archivo previo
        # es el de una reimpresion, donde tener el viejo es lo que se quiere.
        if ok is False:
            pass
        elif os.path.isfile(salida):
            return True

        Ventanas.showError(
            LeerIni('nombre_sistema'),
            "La factura se autorizo pero no se pudo generar el PDF.",
            que_hacer="La factura {} con CAE {} ya esta autorizada en ARCA y no "
                      "se puede deshacer. Para volver a armar el PDF, corre "
                      "Diagnostico desde Configuracion y despues usa Reimprimir "
                      "factura. No la vuelvas a emitir: ARCA no permite dos "
                      "comprobantes iguales.".format(
                          getattr(cabfact, "numero", "?"),
                          self._cae_de_pantalla()),
            detalle="ProcesarPlantilla: {}\nArchivo esperado: {}\n"
                    "Excepcion: {}\nTraceback: {}".format(
                        ok,
                        salida,
                        DeCodifica(getattr(pyfpdf, "Excepcion", "") or ""),
                        DeCodifica(getattr(pyfpdf, "Traceback", "") or "")))
        return False

    def _cae_de_pantalla(self):
        """El CAE que se esta mostrando, o un texto si todavia no esta."""
        try:
            return self.view.lineditCAE.text() or "(sin CAE en pantalla)"
        except Exception:
            return "(sin CAE en pantalla)"

    @inicializar_y_capturar_excepciones
    def ImprimeFactura(self, idcabecera = None, mostrar = True, *args, **kwargs):
        if not idcabecera:
            return
        cabfact = Cabfact().get_by_id(idcabecera)
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

        det = Detfact().select().where(Detfact.idcabfact == cabfact.idcabfact)
        for d in det:
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
            ok = pyfpdf.CargarFormato(ubicacion_sistema() + "/plantillas/factura-fce.csv")
        else:
            #Cargo el formato desde el archivo CSV(opcional)
            #(carga todos los campos a utilizar desde la planilla)
            # ok = pyfpdf.CargarFormato(ubicacion_sistema() + "/plantillas/factura.csv")
            config_marca = cargar_config_marca_factura()
            formato = obtener_formato_factura(os.getcwd(), config_marca, "plantillas/factura_qr.csv")
            ok = pyfpdf.CargarFormato(str(formato))
            aplicar_marca_factura(pyfpdf, os.getcwd(), config_marca)
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
        _alineados = fpdf_compat.normalizar_plantilla(pyfpdf)
        if _alineados:
            logging.debug("plantilla: %s campos con alineacion antigua (D/I)",
                          _alineados)
        num_copias = a_entero(LeerIni(clave='num_copias', key='FACTURA'), 1) #original, duplicado y triplicado
        lineas_max = 24 #cantidad de linas de items por página
        qty_pos = "izq" #(cantidad a la izquierda de la descripción del artículo)
        #Proceso la plantilla
        ok = pyfpdf.ProcesarPlantilla(num_copias, lineas_max, qty_pos)
        if not ok:
            logging.error("ProcesarPlantilla fallo para la factura %s: %s",
                          cabfact.numero, getattr(pyfpdf, "Excepcion", ""))

        if not os.path.isdir('facturas'):
            os.mkdir('facturas')
        try:
            #Genero el PDF de salida segun la plantilla procesada
            salida = join('facturas',"{}-{}.pdf".format(cabfact.tipocomp.nombre.replace(" ", "_"), cabfact.numero))
            ok = pyfpdf.GenerarPDF(salida)
        except:
            cArchivo = getFileName("factura", False)
            cArchivoPDF = cArchivo + '.pdf'
            salida = cArchivoPDF
            ok = pyfpdf.GenerarPDF(salida)

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
        if not self._pdf_generado(salida, ok, pyfpdf, cabfact):
            self.facturaGenerada = None
            return False

        #Abro el visor de PDF y muestro lo generado
        #(es necesario tener instalado Acrobat Reader o similar)
        imprimir = False #cambiar a True para que lo envie directo a laimpresora
        if mostrar:
            pyfpdf.MostrarPDF(salida, imprimir)

        self.facturaGenerada = salida
        return True

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
