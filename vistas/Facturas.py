# coding=utf-8
"""La pantalla de emision de comprobante.

Como esta armada
----------------
Tres columnas, y cada una contesta una pregunta distinta:

    izquierda  QUE  se esta emitiendo      (tipo, fecha, conceptos)
    centro     QUE  se esta vendiendo      (los renglones)
    derecha    CUANTO sale y COMO termino  (los totales y el CAE)

Antes era todo del mismo peso y en el mismo orden de arriba hacia abajo: el
cliente, el comprobante, los conceptos, el periodo, los articulos, los
totales y el CAE, todo con la misma caja. No habia forma de ver de un vistazo
que parte llena el operador y cual es el resultado.

Lo que cambia de lugar y lo que no
---------------------------------
Cambia el LUGAR de todo y el ASPECTO de los totales y del CAE. No cambia el
nombre de ningun atributo: el controlador tiene 154 referencias a
`self.view.*` sobre 30 atributos, y 11 archivos de test los tocan. Por eso
esto es una reorganizacion y no un rediseño desde cero.

Los totales pasaron de `EntradaTexto` deshabilitados a etiquetas, y con ellos
el CAE y el resultado. El controlador ya no los lee con `.value()`: ahora lee
`self.view.total_iva` y demas, que son numeros; las etiquetas son solo lo que
se ve. Ver `ActualizaTotales` y `MuestraAutorizacion`.
"""
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QVBoxLayout, QWidget)

from libs.Botones import Boton, BotonCerrarFormulario
from libs.Checkbox import CheckBox
from libs.ComboBox import FormaPago
from libs.EntradaTexto import EntradaTexto, Factura, TextEdit
from libs.Etiquetas import EtiquetaTitulo, Etiqueta
from libs.Fechas import Fecha
from libs.Formulario import Formulario
from libs.Grillas import Grilla
from libs.GroupBox import Agrupacion
from libs.Paginas import Pagina, TabPagina
from libs.Utiles import imagen, LeerIni, icono, a_entero
from modelos import Clientes, Tiporesp, Tipocomprobantes
from modelos.Clientes import Cliente
from modelos.Formaspago import ComboFormapago

# Los tres numeros que se muestran, y el que se elige mirando la pantalla.
COLOR_NUMERO = "#1F2933"
COLOR_APAGADO = "#52606D"
COLOR_TOTAL = "#1F2933"
COLOR_OK = "#1E7A45"


class FacturaView(Formulario):

    # Esta pantalla necesita mas que el piso general de Formulario (900x560).
    # Con tres columnas, 1180 deja 540 px para la grilla de articulos, y las
    # cinco columnas de importe y cantidad se comen 510: la de Detalle, que es
    # la que el operador lee, queda de 30 px con el nombre partido en tres
    # lineas. Con 1340 entra.
    ANCHO_MINIMO = 1340
    ALTO_MINIMO = 780

    # Ancho de las columnas laterales. La central toma lo que sobre.
    ANCHO_IZQUIERDA = 300
    ANCHO_DERECHA = 290

    def __init__(self):
        Formulario.__init__(self)
        self.setupUi(self)

        # Los valores van aca, en la vista, y no en los campos. Antes los
        # totales eran `EntradaTexto` y el controlador leia `.value()`, que
        # es un numero con signo y de cultura: 1234.5. Ahora el numero esta
        # aca, formateado, y el campo es solo lo que se ve.
        self.total_subtotal = 0.0
        self.total_tributos = 0.0
        self.total_iva = 0.0
        self.total_final = 0.0
        self.cae = ""
        self.resultado = ""
        self.vencimiento_cae = ""
        # El vencimiento va dos veces: como se ve ("14/10/2026") y como se
        # guarda ("20261014"). Antes el mismo dato estaba en un `Fecha` de Qt
        # con un formato de entrada y otro de salida, y habia dos lugares que
        # loodian.
        self.vencimiento_cae_sql = ""
        self.numero_factura = ""

    # -- Lo que se ve ------------------------------------------------------

    def setupUi(self, Form):
        self.layoutPpal = QVBoxLayout(Form)
        self.setWindowTitle("Emisión de comprobante electrónico")
        self.resize(self.ANCHO_MINIMO, self.ALTO_MINIMO)
        self.layoutPpal.setContentsMargins(22, 16, 22, 16)
        self.layoutPpal.setSpacing(14)

        self._armaCabecera()
        self._armaCliente()
        self._armaCuerpo()
        self._armaBotones()

    def _armaCabecera(self):
        """El titulo y, al lado, en que estado esta la factura.

        El estado va arriba porque es la unica pregunta que no se responde
        mirando la pantalla: si emitio o no. Antes el CAE --la respuesta--
        estaba en una caja gris abajo a la izquierda, al lado del boton.
        """
        fila = QHBoxLayout()
        self.lblTitulo = EtiquetaTitulo(texto="Nueva factura")
        fila.addWidget(self.lblTitulo)
        fila.addStretch(1)

        self.lblEstado = QLabel("Sin autorizar")
        self.lblEstado.setStyleSheet(
            "background-color: #F0F4F9; color: #52606D;"
            "border: 1px solid #A9BACD; border-radius: 11px;"
            "padding: 3px 12px; font-size: 12px;")
        fila.addWidget(self.lblEstado)
        self.layoutPpal.addLayout(fila)

    def _armaCliente(self):
        """El cliente a todo el ancho, con el nombre como titular.

        El nombre del cliente es lo primero que hay que confirmar de que se
        esta facturando a la persona correcta, y antes era una `Etiqueta` mas
        al lado del campo de codigo, con el mismo tamano que el domicilio.
        """
        self.agrupaCliente = Agrupacion(titulo="Cliente")
        self.layoutCliente = QVBoxLayout(self.agrupaCliente)
        self.layoutCliente.setSpacing(6)

        self.lblNombreCliente = Etiqueta()
        self.lblNombreCliente.setStyleSheet(
            "font-size: 17px; font-weight: 600; color: #1F2933;")
        self.layoutCliente.addWidget(self.lblNombreCliente)

        grilla = QGridLayout()
        grilla.setHorizontalSpacing(16)
        grilla.setVerticalSpacing(6)

        # Fila 1: codigo, domicilio, documento.
        self.lblCodigoCliente = self._etiquetaCampo("Código de cliente")
        self.validaCliente = Clientes.Valida()
        self.validaCliente.widgetNombre = self.lblNombreCliente
        self.validaCliente.setFixedWidth(140)
        # La lupa al lado. Con 800 clientes el operador no conoce el codigo, y
        # un F2 sin pista no se descubre: la lupa se ve.
        self.btnBuscarCliente = Boton(texto="", imagen=icono('buscar'),
                                      autodefault=False)
        self.btnBuscarCliente.setFixedWidth(36)
        self.btnBuscarCliente.setToolTip(
            "Buscar el cliente por nombre (o con Enter en el código)")
        grilla.addWidget(self.lblCodigoCliente, 0, 0)
        grilla.addWidget(self.validaCliente, 0, 1)
        grilla.addWidget(self.btnBuscarCliente, 0, 2)

        self.lblDomicilio = self._etiquetaCampo("Domicilio")
        self.lineEditDomicilio = EntradaTexto(
            placeholderText="Domicilio del cliente")
        grilla.addWidget(self.lblDomicilio, 0, 3, QtAlinea())
        grilla.addWidget(self.lineEditDomicilio, 0, 4, 1, 3)

        self.lblDocumento = self._etiquetaCampo(u"Nº Doc")
        self.lineEditDocumento = EntradaTexto(placeholderText="CUIT/CUIL/DNI")
        grilla.addWidget(self.lblDocumento, 0, 7)
        grilla.addWidget(self.lineEditDocumento, 0, 8)
        grilla.setColumnStretch(4, 1)
        self.layoutCliente.addLayout(grilla)

        # Fila 2: condicion frente al IVA y forma de pago. La forma de pago
        # estaba dentro del grupo "Conceptos a incluir", que es de otra cosa.
        grilla2 = QGridLayout()
        grilla2.setHorizontalSpacing(16)
        grilla2.setVerticalSpacing(6)

        self.lblTipoIVA = self._etiquetaCampo("Condición frente al IVA")
        self.cboTipoIVA = Tiporesp.Combo()
        self.cboTipoIVA.setFixedWidth(200)
        grilla2.addWidget(self.lblTipoIVA, 0, 0)
        grilla2.addWidget(self.cboTipoIVA, 0, 1)

        self.lblFormaPago = self._etiquetaCampo("Forma de pago")
        self.cboFormaPago = ComboFormapago()
        self.cboFormaPago.setFixedWidth(220)
        grilla2.addWidget(self.lblFormaPago, 0, 2)
        grilla2.addWidget(self.cboFormaPago, 0, 3)

        self.lblSinCtaCte = Etiqueta(texto="")
        self.lblSinCtaCte.setStyleSheet("color: #6B7885; font-size: 12px;")
        grilla2.addWidget(self.lblSinCtaCte, 0, 4, 1, 4)
        grilla2.setColumnStretch(4, 1)
        self.layoutCliente.addLayout(grilla2)
        self.layoutPpal.addWidget(self.agrupaCliente)

    def _armaCuerpo(self):
        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(12)

        # -- Izquierda: que se esta emitiendo ---------------------------
        izquierda = QVBoxLayout()
        izquierda.setSpacing(12)

        self.agrupaComprobante = Agrupacion(titulo="Comprobante")
        layComprobante = QGridLayout(self.agrupaComprobante)
        layComprobante.setHorizontalSpacing(10)
        layComprobante.setVerticalSpacing(6)

        # Tipo y fecha en filas propias, por lo mismo que el periodo: en una
        # sola linea, dentro de los 300 px de la columna izquierda, Qt recorta
        # el `QDateEdit` y "04/10/2026" se ve "04/10/2". Una fecha truncada
        # parece una fecha valida, que es peor que no verla.
        self.lblComprobante = self._etiquetaCampo("Tipo")
        self.cboComprobante = Tipocomprobantes.ComboTipoComp(
            tiporesp=a_entero(LeerIni(clave='cat_iva', key='WSFEv1'), 1))
        layComprobante.addWidget(self.lblComprobante, 0, 0, QtAlinea())
        layComprobante.addWidget(self.cboComprobante, 0, 1)

        self.lblFecha = self._etiquetaCampo("Fecha")
        self.lineEditFecha = Fecha()
        self.lineEditFecha.setFecha()
        layComprobante.addWidget(self.lblFecha, 1, 0, QtAlinea())
        layComprobante.addWidget(self.lineEditFecha, 1, 1)
        layComprobante.setColumnStretch(1, 1)
        izquierda.addWidget(self.agrupaComprobante)

        # El numero de la factura y el del comprobante relacionado tambien en
        # fila propia cada uno: con los dos juntos el titulo se parte.
        # `Factura` es un layout, no un widget, y `addLayout` de una vertical
        # lo toma entero.
        self.layoutFactura = Factura(titulo=u"Nº factura", enabled=False)
        izquierda.addLayout(self.layoutFactura)
        self.layoutCpbteRelacionado = Factura(titulo="Cpbte Rel", enabled=False)
        izquierda.addLayout(self.layoutCpbteRelacionado)

        self.agrupaConceptos = Agrupacion(titulo="Conceptos a incluir")
        self.layoutConceptos = QHBoxLayout(self.agrupaConceptos)
        self.layoutConceptos.setSpacing(18)
        self.checkBoxProductos = CheckBox(texto="Productos")
        self.checkBoxServicios = CheckBox(texto="Servicios")
        self.layoutConceptos.addWidget(self.checkBoxProductos)
        self.layoutConceptos.addWidget(self.checkBoxServicios)
        self.layoutConceptos.addStretch(1)
        izquierda.addWidget(self.agrupaConceptos)

        # El periodo facturado solo aplica a Factura C. Antes estaba siempre
        # visible, con dos de las tres fechas deshabilitadas, ocupando el mismo
        # lugar que los conceptos. Ahora se muestra y se oculta.
        #
        # Y van en fila propia cada una: en una linea con las tres, dentro de
        # los 300 px de la columna izquierda, Qt recorta el `QDateEdit` y la
        # fecha se ve "04/10" en vez de "04/10/2026". No avisa de nada: la
        # fecha truncada parece una fecha valida.
        self.agrupaPeriodo = Agrupacion(titulo="Período facturado")
        self.layoutPeriodo = QGridLayout(self.agrupaPeriodo)
        self.layoutPeriodo.setHorizontalSpacing(10)
        self.layoutPeriodo.setVerticalSpacing(6)
        self.lblDesde = self._etiquetaCampo("Desde")
        self.lblHasta = self._etiquetaCampo("Hasta")
        self.lblVencimiento = self._etiquetaCampo("Vto. pago")
        self.fechaDesde = Fecha()
        self.fechaDesde.setFecha()
        self.fechaHasta = Fecha()
        self.fechaHasta.setFecha()
        self.vencPago = Fecha()
        self.vencPago.setFecha()
        for fila, (etiqueta, campo) in enumerate((
                (self.lblDesde, self.fechaDesde),
                (self.lblHasta, self.fechaHasta),
                (self.lblVencimiento, self.vencPago))):
            self.layoutPeriodo.addWidget(etiqueta, fila, 0, QtAlinea())
            self.layoutPeriodo.addWidget(campo, fila, 1)
        # La fecha se lleva el ancho que sobra: con la columna en 1 la
        # etiqueta queda justa y el campo se achica.
        self.layoutPeriodo.setColumnStretch(1, 1)
        izquierda.addWidget(self.agrupaPeriodo)

        izquierda.addStretch(1)
        contenedorIzq = QWidget()
        contenedorIzq.setLayout(izquierda)
        contenedorIzq.setFixedWidth(self.ANCHO_IZQUIERDA)
        cuerpo.addWidget(contenedorIzq)

        # -- Centro: los renglones --------------------------------------
        centro = QVBoxLayout()
        self._armaPaginas()
        centro.addWidget(self.paginaDatos)
        cuerpo.addLayout(centro, 1)

        # -- Derecha: totales, autorizacion y la accion -----------------
        derecha = QVBoxLayout()
        derecha.setSpacing(6)
        derecha.addWidget(self._linea())

        # Los totales van alineados a la derecha y con tamano de numero, no
        # como campos de formulario. El total es lo unico que el operador
        # viene a ver y no se podia distinguir de los otros tres.
        self.lblTotalSubtotalTexto = Etiqueta(texto="Subtotal")
        self.textSubTotal = self._etiquetaNumero("0,00")
        derecha.addLayout(self._filaTotal(self.lblTotalSubtotalTexto,
                                          self.textSubTotal))

        self.lblTributos = Etiqueta(texto="Otros tributos")
        self.lineEditTributos = self._etiquetaNumero("0,00")
        derecha.addLayout(self._filaTotal(self.lblTributos,
                                          self.lineEditTributos))

        self.lblTotalIVA = Etiqueta(texto="IVA")
        self.lineEditTotalIVA = self._etiquetaNumero("0,00")
        derecha.addLayout(self._filaTotal(self.lblTotalIVA,
                                          self.lineEditTotalIVA))

        derecha.addSpacing(10)
        derecha.addWidget(self._linea(fuerte=True))

        self.lblTotalFactura = Etiqueta(texto="Total")
        self.lineEditTotal = self._etiquetaNumero("$ 0,00", grande=True)
        derecha.addLayout(self._filaTotal(self.lblTotalFactura,
                                          self.lineEditTotal, grande=True))

        derecha.addSpacing(18)
        self.lblTituloAutorizacion = QLabel("Autorización")
        self.lblTituloAutorizacion.setStyleSheet(
            "color: #52606D; font-size: 12px;")
        derecha.addWidget(self.lblTituloAutorizacion)

        # El numero, el CAE y el vencimiento, juntos y arriba. Antes eran tres
        # campos de texto deshabilitados en un grupo que parecia uno de los
        # muchos, abajo a la izquierda, al lado del boton.
        self.lblNumeroFactura = QLabel("")
        self.lblNumeroFactura.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: #1F2933;")
        derecha.addWidget(self.lblNumeroFactura)

        self.lblCAE = QLabel("")
        self.lblCAE.setStyleSheet(
            "font-size: 13px; color: %s; font-family: Consolas, monospace;"
            % COLOR_APAGADO)
        # Seleccionable: el CAE hay que poder copiarlo para mandarlo a un
        # cliente por mail, y con un QLabel plano no se copia.
        self.lblCAE.setTextInteractionFlags(Qt.TextSelectableByMouse)
        derecha.addWidget(self.lblCAE)

        self.lblVencCAE = QLabel("")
        self.lblVencCAE.setStyleSheet("font-size: 12px; color: #52606D;")
        derecha.addWidget(self.lblVencCAE)

        self.lblResultado = QLabel("")
        self.lblResultado.setStyleSheet("font-size: 12px; color: #52606D;")
        derecha.addWidget(self.lblResultado)

        derecha.addStretch(1)

        contenedorDer = QWidget()
        contenedorDer.setLayout(derecha)
        contenedorDer.setFixedWidth(self.ANCHO_DERECHA)
        cuerpo.addWidget(contenedorDer)

        self.layoutPpal.addLayout(cuerpo, 1)

    def _armaBotones(self):
        """La accion principal abajo a la derecha, y no media pantalla.

        Antes "Emitir" y "Cerrar" ocupaban la mitad del ancho cada uno, con el
        mismo peso. Cerrar es "salir sin hacer nada"; emitir manda a ARCA.
        """
        fila = QHBoxLayout()
        fila.addStretch(1)

        self.btnNuevaFactura = Boton(texto="Nueva factura",
                                     imagen=icono('nueva-venta'),
                                     autodefault=False)
        self.btnNuevaFactura.setVisible(False)
        fila.addWidget(self.btnNuevaFactura)

        self.btnImprimir = Boton(texto="Imprimir", imagen=icono('imprimir'),
                                 autodefault=False, estilo='primario')
        self.btnImprimir.setMinimumHeight(44)
        self.btnImprimir.setVisible(False)
        fila.addWidget(self.btnImprimir)

        self.btnGrabarFactura = Boton(texto="Emitir factura",
                                      imagen=icono('guardar'),
                                      autodefault=False, estilo='primario')
        self.btnGrabarFactura.setMinimumHeight(44)
        fila.addWidget(self.btnGrabarFactura)

        self.btnCerrarFormulario = BotonCerrarFormulario(autodefault=False)
        fila.addWidget(self.btnCerrarFormulario)

        self.layoutBotones = fila
        self.layoutPpal.addLayout(fila)

    def _armaPaginas(self):
        self.paginaDatos = Pagina()
        self.tabArticulo = TabPagina()
        self.tabAlicuotaIVA = TabPagina()
        self.tabOtrosTributos = TabPagina()
        self.tabObs = TabPagina()
        self.tabArticuloUI()
        self.tabAlicuotaIVAUI()
        self.tabOtrosTributosUI()
        self.tabObsUI()
        self.paginaDatos.addTab(self.tabArticulo, "Artículos")
        self.paginaDatos.addTab(self.tabAlicuotaIVA, "Alicuotas de IVA")
        self.paginaDatos.addTab(self.tabOtrosTributos, "Otros tributos")
        self.paginaDatos.addTab(self.tabObs, "Observaciones")

    # -- Ayuditas de armado ------------------------------------------------

    @staticmethod
    def _etiquetaCampo(texto):
        etiqueta = QLabel(texto)
        etiqueta.setStyleSheet("color: #52606D; font-size: 12px;")
        return etiqueta

    @staticmethod
    def _etiquetaNumero(texto, grande=False):
        etiqueta = QLabel(texto)
        if grande:
            etiqueta.setStyleSheet(
                "font-size: 26px; font-weight: 600; color: %s;" % COLOR_TOTAL)
        else:
            etiqueta.setStyleSheet(
                "font-size: 15px; font-weight: 500; color: %s;" % COLOR_NUMERO)
        from PyQt5.QtCore import Qt
        etiqueta.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return etiqueta

    @staticmethod
    def _filaTotal(etiqueta_texto, etiqueta_numero, grande=False):
        fila = QHBoxLayout()
        etiqueta_texto.setStyleSheet(
            "color: %s; font-size: %s;" % (
                COLOR_APAGADO, "15px" if grande else "13px"))
        fila.addWidget(etiqueta_texto)
        fila.addStretch(1)
        fila.addWidget(etiqueta_numero)
        return fila

    @staticmethod
    def _linea(fuerte=False):
        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)
        separador.setStyleSheet(
            "color: %s; background-color: %s; max-height: 1px;"
            % (COLOR_TOTAL if fuerte else "#C8D2DE",
               COLOR_TOTAL if fuerte else "#C8D2DE"))
        return separador

    # -- Lo que cambia la vista cuando cambia el estado -------------------

    def ActualizaTotales(self, subtotal, tributos, iva, total, decimales=2):
        """Guarda los numeros y los pinta.

        Los numeros quedan en la vista (`self.total_iva` y demas) porque el
        controlador los usa para guardar la cabecera: antes los leia con
        `.value()` del `EntradaTexto`, que ademas es un numero con cultura y
        signo. Las etiquetas son solo lo que se ve.
        """
        self.total_subtotal = round(float(subtotal), decimales)
        self.total_tributos = round(float(tributos), decimales)
        self.total_iva = round(float(iva), decimales)
        self.total_final = round(float(total), 2)
        self.textSubTotal.setText(_numero(self.total_subtotal))
        self.lineEditTributos.setText(_numero(self.total_tributos))
        self.lineEditTotalIVA.setText(_numero(self.total_iva))
        self.lineEditTotal.setText("$ " + _numero(self.total_final))

    def MuestraSinAutorizar(self):
        """Estado inicial: todavia no se pidio autorizacion."""
        self.lblEstado.setText("Sin autorizar")
        self.lblEstado.setStyleSheet(
            "background-color: #F0F4F9; color: #52606D;"
            "border: 1px solid #A9BACD; border-radius: 11px;"
            "padding: 3px 12px; font-size: 12px;")
        self.cae = ""
        self.resultado = ""
        self.vencimiento_cae = ""
        self.vencimiento_cae_sql = ""
        self.numero_factura = ""
        self.lblNumeroFactura.setText("Se solicita al emitir")
        self.lblNumeroFactura.setStyleSheet(
            "font-size: 13px; color: %s;" % COLOR_APAGADO)
        self.lblCAE.setText("")
        self.lblVencCAE.setText("")
        self.lblResultado.setText("")
        self.btnGrabarFactura.setVisible(True)
        self.btnImprimir.setVisible(False)
        self.btnNuevaFactura.setVisible(False)

    def MuestraAutorizacion(self, numero, cae, resultado, vencimiento,
                            autorizada=True, vencimiento_sql=""):
        """La factura quedo autorizada: el CAE pasa a ser el dato principal.

        `autorizada` esta en False para el caso de "no se pudo autorizar": el
        CAE no viene, pero el operador tiene que ver por que fallo, asi que el
        resultado se muestra en rojo y no se esconde.
        """
        self.numero_factura = numero or ""
        self.cae = cae or ""
        self.resultado = resultado or ""
        self.vencimiento_cae = vencimiento or ""
        self.vencimiento_cae_sql = vencimiento_sql or ""

        if autorizada and self.cae:
            self.lblEstado.setText("Autorizada")
            self.lblEstado.setStyleSheet(
                "background-color: #E4F3E8; color: %s;"
                "border: 1px solid #7FC79B; border-radius: 11px;"
                "padding: 3px 12px; font-size: 12px;" % COLOR_OK)
            self.lblNumeroFactura.setText(self.numero_factura)
            self.lblNumeroFactura.setStyleSheet(
                "font-size: 14px; font-weight: 600; color: #1F2933;")
            self.lblCAE.setText("CAE  " + self.cae)
            self.lblCAE.setStyleSheet(
                "font-size: 13px; color: %s; font-family: Consolas, monospace;"
                % COLOR_OK)
            self.lblVencCAE.setText(
                "Vence el {}".format(self.vencimiento_cae)
                if self.vencimiento_cae else "")
            self.lblResultado.setText("")
            self.btnGrabarFactura.setVisible(False)
            self.btnImprimir.setVisible(True)
            self.btnNuevaFactura.setVisible(True)
        else:
            self.lblEstado.setText("Rechazada")
            self.lblEstado.setStyleSheet(
                "background-color: #FDEEEE; color: #A32B2B;"
                "border: 1px solid #E0A3A3; border-radius: 11px;"
                "padding: 3px 12px; font-size: 12px;")
            self.lblNumeroFactura.setText("No se pudo autorizar")
            self.lblNumeroFactura.setStyleSheet(
                "font-size: 14px; font-weight: 600; color: #A32B2B;")
            self.lblCAE.setText("")
            self.lblResultado.setText(self.resultado)
            self.lblResultado.setStyleSheet("font-size: 12px; color: #A32B2B;")
            self.btnGrabarFactura.setVisible(True)
            self.btnImprimir.setVisible(False)
            self.btnNuevaFactura.setVisible(False)

    def MuestraPeriodo(self, visible):
        """El periodo facturado solo existe para Factura C.

        Con Factura A o B no tiene sentido mostrar tres fechas, dos de ellas
        deshabilitadas, al mismo peso que los conceptos.
        """
        self.agrupaPeriodo.setVisible(bool(visible))
        for campo in (self.lblDesde, self.lblHasta, self.lblVencimiento):
            campo.setVisible(bool(visible))
        self.fechaDesde.setVisible(bool(visible))
        self.fechaHasta.setVisible(bool(visible))
        self.vencPago.setVisible(bool(visible))

    # -- Las cuatro pestañas ----------------------------------------------

    def tabArticuloUI(self):
        layoutppal = QVBoxLayout()
        layoutppal.setContentsMargins(10, 10, 10, 10)
        layoutppal.setSpacing(10)
        self.gridFactura = Grilla(tamanio=10)
        cabeceras = [
            'Cant.', 'Codigo', 'Detalle', 'Unitario', 'IVA', 'SubTotal'
        ]
        # Los formatos van declarados: sin ellos la grilla no sabe que "Unitario"
        # o "SubTotal" son importes y los reparte como texto corto, con el
        # numero pegado al borde.
        #
        # `Detalle` es la unica columna de texto, y se queda con todo el
        # sobrante. Es la que mas importa --el operador tiene que ver QUE esta
        # vendiendo-- y con las otras cinco a su ancho fijo es la que queda.
        # Que elija la de texto mas larga en vez de "la primera de texto" hace
        # que gane "Detalle" y no "Nombre de algo", que en otras grillas suele
        # ser la mas larga.
        self.gridFactura.ArmaCabeceras(
            cabeceras=cabeceras,
            formatos=['Cantidad', 'Entero', 'String', 'Moneda', 'Moneda',
                      'Moneda'])
        self.gridFactura.columnasHabilitadas = (
            [0, 1, 2, 3] if a_entero(LeerIni(clave='cat_iva', key='WSFEv1'), 1) == 6
            else [0, 1, 2, 3, 4])
        self.gridFactura.columna_preferida = 'Detalle'

        item = [
            1, 1, '', 0, 21, 0
        ]
        self.gridFactura.AgregaItem(items=item)

        layoutppal.addWidget(self.gridFactura)
        layoutBotones = QHBoxLayout()
        # Agrega y Borrar NO son la accion principal de esta pantalla: la
        # principal es Emitir, abajo a la derecha.
        self.botonAgregaArt = Boton(texto="Agregar línea", imagen=icono('nuevo'),
                                    tamanio=QSize(16, 16), autodefault=False)
        self.botonBorrarArt = Boton(texto="Quitar línea", imagen=icono('borrar'),
                                    tamanio=QSize(16, 16), autodefault=False,
                                    estilo='peligro')
        layoutBotones.addWidget(self.botonAgregaArt)
        layoutBotones.addStretch(1)
        layoutBotones.addWidget(self.botonBorrarArt)
        layoutppal.addLayout(layoutBotones)
        self.tabArticulo.setLayout(layoutppal)

    def tabAlicuotaIVAUI(self):
        layoutppal = QVBoxLayout()
        layoutppal.setContentsMargins(10, 10, 10, 10)
        self.gridAlicuotasIVA = Grilla(tamanio=10)
        cabeceras = [
            'IVA', 'Alicuota', 'Base Imponible', 'Importe'
        ]
        self.gridAlicuotasIVA.ArmaCabeceras(
            cabeceras=cabeceras,
            formatos=['Moneda', 'Moneda', 'Moneda', 'Moneda'])
        layoutppal.addWidget(self.gridAlicuotasIVA)
        layoutBotones = QHBoxLayout()
        self.botonAgregaIVA = Boton(texto="Agregar", imagen=icono('nuevo'),
                                    tamanio=QSize(16, 16), autodefault=False)
        self.botonBorrarIVA = Boton(texto="Borrar", imagen=icono('borrar'),
                                    tamanio=QSize(16, 16), autodefault=False,
                                    estilo='peligro')
        layoutBotones.addWidget(self.botonAgregaIVA)
        layoutBotones.addStretch(1)
        layoutBotones.addWidget(self.botonBorrarIVA)
        layoutppal.addLayout(layoutBotones)
        self.tabAlicuotaIVA.setLayout(layoutppal)

    def tabOtrosTributosUI(self):
        layoutppal = QVBoxLayout()
        layoutppal.setContentsMargins(10, 10, 10, 10)
        self.gridAlicuotasTributos = Grilla(tamanio=10)
        cabeceras = [
            'Alicuota', 'Base Imponible', 'Importe'
        ]
        self.gridAlicuotasTributos.ArmaCabeceras(
            cabeceras=cabeceras,
            formatos=['Moneda', 'Moneda', 'Moneda'])
        layoutppal.addWidget(self.gridAlicuotasTributos)
        layoutBotones = QHBoxLayout()
        self.botonAgregaTributos = Boton(texto="Agregar", imagen=icono('nuevo'),
                                         tamanio=QSize(16, 16), autodefault=False)
        self.botonBorrarTributos = Boton(texto="Borrar", imagen=icono('borrar'),
                                         tamanio=QSize(16, 16), autodefault=False,
                                         estilo='peligro')
        layoutBotones.addWidget(self.botonAgregaTributos)
        layoutBotones.addStretch(1)
        layoutBotones.addWidget(self.botonBorrarTributos)
        layoutppal.addLayout(layoutBotones)
        self.tabOtrosTributos.setLayout(layoutppal)

    def tabObsUI(self):
        layoutppal = QVBoxLayout()
        layoutppal.setContentsMargins(10, 10, 10, 10)
        self.editObs = TextEdit()
        layoutppal.addWidget(self.editObs)
        self.tabObs.setLayout(layoutppal)


def QtAlinea():
    """`Qt.AlignVCenter` para las etiquetas que van al lado de un campo."""
    from PyQt5.QtCore import Qt
    return Qt.AlignVCenter


def _numero(valor, decimales=2):
    """Un numero con el formato que usa la app: punto de miles y coma decimal.

    El original usaba `str(round(...))` y dejaba que Qt lo formateara, asi que
    el total de la derecha y el total que se guarda eran dos numeros distintos
    escritos de dos maneras. Ahora el numero y lo que se ve son lo mismo.
    """
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        valor = 0.0
    texto = "{:,.{d}f}".format(valor, d=decimales)
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
