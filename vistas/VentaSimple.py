# coding=utf-8
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QListWidget, QVBoxLayout

from decimal import Decimal

from libs.Botones import Boton, BotonCerrarFormulario, botonera_dialogo
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import Etiqueta, EtiquetaTitulo
from libs.Formulario import Formulario
from libs.Grillas import Grilla, _formato_importe
from libs.GroupBox import Agrupacion
from libs.Utiles import imagen, icono
from modelos.Formaspago import ComboFormapago


class VentaSimpleCantidadPrecioDialog(Formulario):
    def __init__(self, articulo, cantidad, precio):
        Formulario.__init__(self)
        self.articulo = articulo
        self.setupUi(self)
        self.textCantidad.setText(str(cantidad))
        self.textPrecio.setText(str(precio))

    def setupUi(self, Form):
        self.setWindowTitle("Cantidad y precio")
        self.declara_tamano(420, 160)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto=self.articulo.nombre)
        self.layoutPpal.addWidget(self.lblTitulo)

        self.layoutDatos = QGridLayout()
        self.textCantidad = EntradaTexto(placeholderText="Cantidad")
        self.textPrecio = EntradaTexto(placeholderText="Precio")
        self.layoutDatos.addWidget(Etiqueta(texto="Cantidad"), 0, 0)
        self.layoutDatos.addWidget(self.textCantidad, 0, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="Precio"), 1, 0)
        self.layoutDatos.addWidget(self.textPrecio, 1, 1)
        self.layoutPpal.addLayout(self.layoutDatos)

        # El sobrante va antes de la botonera, no al titulo. Es lo que
        # hacen las demas pantallas del proyecto (vistas/Stock.py,
        # vistas/Main.py): sin esto la botonera queda pegada al tope y el
        # vacio cae abajo.
        self.layoutPpal.addStretch(1)

        self.botones = botonera_dialogo()
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        self.layoutPpal.addWidget(self.botones)

        self.textCantidad.proximoWidget = self.textPrecio
        self.textCantidad.returnPressed.connect(self.textPrecio.setFocus)
        self.textPrecio.returnPressed.connect(self.accept)

    def valores(self):
        return self.textCantidad.text(), self.textPrecio.text()


class VentaSimpleAltaClienteDialog(Formulario):
    def __init__(self, busqueda):
        Formulario.__init__(self)
        self.busqueda = busqueda
        self.setupUi(self)
        self.textNombre.setText(busqueda)

    def setupUi(self, Form):
        self.setWindowTitle("Agregar cliente")
        self.declara_tamano(520, 220)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto="Agregar cliente")
        self.layoutPpal.addWidget(self.lblTitulo)

        self.layoutDatos = QGridLayout()
        self.textNombre = EntradaTexto(placeholderText="Nombre")
        self.textDocumento = EntradaTexto(placeholderText="CUIT/DNI")
        self.textDomicilio = EntradaTexto(placeholderText="Domicilio")
        self.layoutDatos.addWidget(Etiqueta(texto="Nombre"), 0, 0)
        self.layoutDatos.addWidget(self.textNombre, 0, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="CUIT/DNI"), 1, 0)
        self.layoutDatos.addWidget(self.textDocumento, 1, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="Domicilio"), 2, 0)
        self.layoutDatos.addWidget(self.textDomicilio, 2, 1)
        self.layoutPpal.addLayout(self.layoutDatos)

        # El sobrante va antes de la botonera, no al titulo. Es lo que
        # hacen las demas pantallas del proyecto (vistas/Stock.py,
        # vistas/Main.py): sin esto la botonera queda pegada al tope y el
        # vacio cae abajo.
        self.layoutPpal.addStretch(1)

        self.botones = botonera_dialogo()
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        self.layoutPpal.addWidget(self.botones)

        self.textNombre.proximoWidget = self.textDocumento
        self.textDocumento.proximoWidget = self.textDomicilio
        self.textDomicilio.returnPressed.connect(self.accept)

    def valores(self):
        return {
            "nombre": self.textNombre.text().strip(),
            "documento": self.textDocumento.text().strip(),
            "domicilio": self.textDomicilio.text().strip(),
        }


class VentaSimpleAltaArticuloDialog(Formulario):
    def __init__(self, busqueda):
        Formulario.__init__(self)
        self.busqueda = busqueda
        self.setupUi(self)
        self.textNombre.setText(busqueda)

    def setupUi(self, Form):
        self.setWindowTitle("Agregar articulo")
        self.declara_tamano(520, 220)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto="Agregar articulo")
        self.layoutPpal.addWidget(self.lblTitulo)

        self.layoutDatos = QGridLayout()
        self.textNombre = EntradaTexto(placeholderText="Nombre")
        self.textPrecio = EntradaTexto(placeholderText="Precio")
        self.textIva = EntradaTexto(placeholderText="IVA")
        self.textCodigoBarra = EntradaTexto(placeholderText="Código de barras")
        self.textPrecio.setText("0.00")
        self.textIva.setText("21")
        self.layoutDatos.addWidget(Etiqueta(texto="Nombre"), 0, 0)
        self.layoutDatos.addWidget(self.textNombre, 0, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="Precio"), 1, 0)
        self.layoutDatos.addWidget(self.textPrecio, 1, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="IVA"), 2, 0)
        self.layoutDatos.addWidget(self.textIva, 2, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="Código barras"), 3, 0)
        self.layoutDatos.addWidget(self.textCodigoBarra, 3, 1)
        self.layoutPpal.addLayout(self.layoutDatos)

        # El sobrante va antes de la botonera, no al titulo. Es lo que
        # hacen las demas pantallas del proyecto (vistas/Stock.py,
        # vistas/Main.py): sin esto la botonera queda pegada al tope y el
        # vacio cae abajo.
        self.layoutPpal.addStretch(1)

        self.botones = botonera_dialogo()
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        self.layoutPpal.addWidget(self.botones)

        self.textNombre.proximoWidget = self.textPrecio
        self.textPrecio.proximoWidget = self.textIva
        self.textIva.proximoWidget = self.textCodigoBarra
        self.textCodigoBarra.returnPressed.connect(self.accept)

    def valores(self):
        return {
            "nombre": self.textNombre.text().strip(),
            "precio": self.textPrecio.text().strip(),
            "iva": self.textIva.text().strip(),
            "codbarra": self.textCodigoBarra.text().strip(),
        }


class VentaSimpleSeleccionClienteDialog(Formulario):
    """Elegir un cliente de los que coinciden con lo que se escribio.

    Recibe COMO buscar, no la lista: el buscador se vuelve a consultar cada vez
    que se escribe, que es lo que hace falta cuando hay miles de clientes. Con
    la lista ya armada no habia forma de acotar sin cerrar el dialogo y volver
    a escribir desde la venta.
    """

    def __init__(self, buscador, busqueda=""):
        Formulario.__init__(self)
        self.buscador = buscador          # callable(texto) -> (clientes, total)
        self.busqueda_inicial = busqueda
        self.clientes = []
        self.total = 0
        self.cliente = None
        self.setupUi(self)
        self.buscar(busqueda)

    def setupUi(self, Form):
        self.setWindowTitle("Seleccionar cliente")
        self.resize(560, 420)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto="Seleccionar cliente")
        self.layoutPpal.addWidget(self.lblTitulo)

        self.txtBuscar = EntradaTexto(
            placeholderText="Buscar por nombre, CUIT o DNI")
        self.txtBuscar.setObjectName("txtBuscar")
        self.txtBuscar.setText(self.busqueda_inicial)
        self.txtBuscar.textChanged.connect(self.buscar)
        self.txtBuscar.returnPressed.connect(self._elegir_para_entrar)
        self.layoutPpal.addWidget(self.txtBuscar)

        self.listaClientes = QListWidget()
        self.listaClientes.itemDoubleClicked.connect(self.accept)
        self.layoutPpal.addWidget(self.listaClientes)

        # Sin esto no hay forma de saber si la lista esta completa o recortada:
        # con 800 coincidencias y 100 filas, ver 100 no dice si falta nada.
        self.lblCuenta = Etiqueta("")
        self.lblCuenta.setObjectName("lblCuenta")
        self.layoutPpal.addWidget(self.lblCuenta)

        self.botones = botonera_dialogo()
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        self.layoutPpal.addWidget(self.botones)

    def buscar(self, texto):
        """Vuelve a consultar y redibuja la lista."""
        self.clientes = []
        self.listaClientes.clear()

        texto = str(texto or "").strip()
        if not texto:
            # Volcar todos los clientes no es una busqueda: es una pantalla
            # imposible de usar, y ademas esconde que hay que acotar.
            self.lblCuenta.setText("Escribi para buscar entre los clientes.")
            return

        self.clientes, self.total = self.buscador(texto)
        for cliente in self.clientes:
            documento = cliente.cuit if str(cliente.cuit).replace("-", "").strip("0") else str(cliente.dni or "")
            self.listaClientes.addItem("{} - {} - {}".format(
                cliente.idcliente, cliente.nombre, documento))
        # Igual que en articulos: con una sola se marca sola, con varias no.
        # Dos clientes con nombres parecidos existen, y elegir el de arriba
        # sin que nadie lo elija es cobrarle al cliente equivocado.
        if len(self.clientes) == 1:
            self.listaClientes.setCurrentRow(0)

        if self.total > len(self.clientes):
            self.lblCuenta.setText(
                "Mostrando {} de {} coincidencias. Seguí escribiendo para acotar.".format(
                    len(self.clientes), self.total))
        elif self.total > 1:
            self.lblCuenta.setText(
                "{} coincidencias. Elegí una con las flechas o el mouse.".format(
                    self.total))
        else:
            self.lblCuenta.setText(
                "{} coincidencia{}".format(self.total, "" if self.total == 1 else "s"))

    def _elegir_para_entrar(self):
        """Enter elige lo marcado. Sin nada marcado, no hace nada.

        Antes tomaba la fila 0 por las dudas, que con varias coincidencias
        era decidirle al operador a cuál cliente se le cobra.
        """
        if self.listaClientes.currentRow() < 0:
            return
        self.accept()

    def accept(self):
        fila = self.listaClientes.currentRow()
        if fila < 0 or fila >= len(self.clientes):
            return
        self.cliente = self.clientes[fila]
        Formulario.accept(self)


class VentaSimpleSeleccionArticuloDialog(Formulario):
    """Elegir un articulo del catalogo, sin tener que acordarse el nombre.

    Es el hermano de VentaSimpleSeleccionClienteDialog y existe por el mismo
    motivo: con el campo de producto vacio, Enter tiene que hacer algo util, y
    lo util es abrir el catalogo. Antes decia "Ingrese un producto", que es un
    aviso de que no se entendio que hacer.

    Recibe COMO buscar, no la lista, por la misma razon que el de clientes: el
    buscador se vuelve a consultar cada vez que se escribe, que es lo que hace
    falta cuando hay catalogo de verdad y no dos articulos de prueba.
    """

    def __init__(self, buscador, busqueda=""):
        Formulario.__init__(self)
        self.buscador = buscador          # callable(texto) -> (articulos, total)
        self.busqueda_inicial = busqueda
        self.articulos = []
        self.total = 0
        self.articulo = None
        self.setupUi(self)
        self.buscar(busqueda)

    def setupUi(self, Form):
        self.setWindowTitle("Seleccionar producto")
        self.resize(560, 420)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto="Seleccionar producto")
        self.layoutPpal.addWidget(self.lblTitulo)

        self.txtBuscar = EntradaTexto(
            placeholderText="Buscar por nombre, código o código de barras")
        self.txtBuscar.setObjectName("txtBuscar")
        self.txtBuscar.setText(self.busqueda_inicial)
        self.txtBuscar.textChanged.connect(self.buscar)
        self.txtBuscar.returnPressed.connect(self._elegir_para_entrar)
        self.layoutPpal.addWidget(self.txtBuscar)

        self.listaArticulos = QListWidget()
        self.listaArticulos.itemDoubleClicked.connect(self.accept)
        self.layoutPpal.addWidget(self.listaArticulos)

        # Igual que en el de clientes: con la lista recortada hay que poder
        # decir cuantas hay de verdad, o 100 filas no dicen si falta algo.
        self.lblCuenta = Etiqueta("")
        self.lblCuenta.setObjectName("lblCuenta")
        self.layoutPpal.addWidget(self.lblCuenta)

        self.botones = botonera_dialogo()
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        self.layoutPpal.addWidget(self.botones)

    def buscar(self, texto):
        """Vuelve a consultar y redibuja la lista."""
        self.articulos = []
        self.listaArticulos.clear()

        texto = str(texto or "").strip()
        if not texto:
            # Volcar el catalogo entero no es una busqueda. Ademas, con un
            # catalogo chico uno quiere ver todo, asi que se lo ofrece: los
            # primeros, avisando que hay mas.
            self.articulos, self.total = self.buscador("")
            for articulo in self.articulos:
                self.listaArticulos.addItem(self._texto(articulo))
            self.lblCuenta.setText(
                "Escribi para acotar. {} producto{} en el catalogo.".format(
                    self.total, "" if self.total == 1 else "s"))
            if self.articulos:
                self.listaArticulos.setCurrentRow(0)
            return

        self.articulos, self.total = self.buscador(texto)
        for articulo in self.articulos:
            self.listaArticulos.addItem(self._texto(articulo))
        # Con una sola coincidencia se marca sola: no hay nada que decidir y
        # Enter tiene que servir. Con varias NO: ver _elegir_para_entrar.
        if len(self.articulos) == 1:
            self.listaArticulos.setCurrentRow(0)

        if self.total > len(self.articulos):
            self.lblCuenta.setText(
                "Mostrando {} de {} coincidencias. Seguí escribiendo para "
                "acotar.".format(len(self.articulos), self.total))
        elif self.total > 1:
            # Sin esta frase el operador cree que el de arriba ya esta
            # elegido, y es justo lo que paso: escribia "w" y se llevaba el
            # primero de los dos WHEY CUTTER.
            self.lblCuenta.setText(
                "{} coincidencias. Elegí una con las flechas o el mouse.".format(
                    self.total))
        else:
            self.lblCuenta.setText(
                "{} coincidencia{}".format(
                    self.total, "" if self.total == 1 else "s"))

    def _texto(self, articulo):
        codigo = str(articulo.codbarra or "").strip()
        if codigo:
            return "{} - {} - {}".format(articulo.idarticulo, articulo.nombre,
                                        codigo)
        return "{} - {}".format(articulo.idarticulo, articulo.nombre)

    def _elegir_para_entrar(self):
        """Enter elige lo marcado, y solo si hay algo marcado.

        Antes se llamaba _aceptar_primero y hacia setCurrentRow(0) si no
        habia nada marcado. Con un catalogo donde dos productos se parecen
        (dos "WHEY CUTTER ..." que difieren en el sabor) eso era elegir por
        el operador: el que estaba de arriba. Ahora, sin nada marcado, Enter
        no hace nada y el operador tiene que elegir a proposito.
        """
        if self.listaArticulos.currentRow() < 0:
            return
        self.accept()

    def accept(self):
        """Aceptar requiere una fila elegida.

        Con varias coincidencias y nada marcado, Aceptar no cierra: si
        cerrara, el articulo quedaria en None y el controlador lo tomaria
        como "no elegiste nada", que no es lo que el operador quiso.
        """
        fila = self.listaArticulos.currentRow()
        if fila < 0 or fila >= len(self.articulos):
            return
        self.articulo = self.articulos[fila]
        Formulario.accept(self)


class VentaSimpleView(Formulario):
    def __init__(self):
        Formulario.__init__(self)
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Nueva venta")
        self.resize(980, 640)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto="Nueva venta")
        self.layoutPpal.addWidget(self.lblTitulo)

        self.agrupaCliente = Agrupacion(titulo="Cliente")
        self.layoutCliente = QGridLayout()
        self.checkConsumidorFinal = QCheckBox("Consumidor final")
        self.checkConsumidorFinal.setChecked(True)
        self.textCliente = EntradaTexto(placeholderText="Buscar cliente por nombre, CUIT o DNI")
        self.textDocumento = EntradaTexto(placeholderText="CUIT/DNI")
        self.layoutCliente.addWidget(self.checkConsumidorFinal, 0, 0)
        self.layoutCliente.addWidget(Etiqueta(texto="Cliente"), 0, 1)
        self.layoutCliente.addWidget(self.textCliente, 0, 2)
        self.layoutCliente.addWidget(Etiqueta(texto="Documento"), 0, 3)
        self.layoutCliente.addWidget(self.textDocumento, 0, 4)
        self.agrupaCliente.setLayout(self.layoutCliente)
        self.layoutPpal.addWidget(self.agrupaCliente)

        self.agrupaArticulo = Agrupacion(titulo="Agregar producto")
        self.layoutArticulo = QGridLayout()
        self.textArticulo = EntradaTexto(placeholderText="Código, nombre o código de barras")
        self.textCantidad = EntradaTexto(placeholderText="Cantidad")
        self.textCantidad.setText("1")
        self.btnAgregar = Boton(texto="Agregar", imagen=icono('nuevo'), tamanio=QSize(16, 16), autodefault=False)
        self.layoutArticulo.addWidget(Etiqueta(texto="Producto"), 0, 0)
        self.layoutArticulo.addWidget(self.textArticulo, 0, 1)
        self.layoutArticulo.addWidget(Etiqueta(texto="Cantidad"), 0, 2)
        self.layoutArticulo.addWidget(self.textCantidad, 0, 3)
        self.layoutArticulo.addWidget(self.btnAgregar, 0, 4)
        self.agrupaArticulo.setLayout(self.layoutArticulo)
        self.layoutPpal.addWidget(self.agrupaArticulo)

        self.gridVenta = Grilla(tamanio=10)
        # Se declara que hay en cada columna. Sirve para dos cosas: alinear el
        # encabezado igual que los datos (una columna de importes con el
        # titulo a la izquierda y los numeros a la derecha se ve rota) y
        # mostrar cada tipo con sus decimales. "Cant." queda angosta porque el
        # ancho se reparte segun el encabezado, y antes se comia media fila.
        #
        # La columna Stock va cuarta, entre Detalle y Unitario: es un dato del
        # producto y tiene que leerse pegado al producto. Insertarla al final
        #eria mas simple, pero la dejaria separada de lo que describe.
        #
        # OJO con `columnasHabilitadas`: son INDICES, no nombres. Al insertar
        # Stock en el medio, Unitario pasa de 3 a 4 e IVA de 4 a 5, asi que la
        # lista de editables se corre con ella. Stock queda fuera a proposito:
        # el stock es derivado de los movimientos, y si se pudiera escribir ahi
        # un numero se creeria que el inventario cambio sin que exista ningun
        # movimiento que lo diga.
        self.gridVenta.ArmaCabeceras(
            cabeceras=["Cant.", "Codigo", "Detalle", "Stock", "Unitario", "IVA",
                       "SubTotal"],
            formatos=["Cantidad", "String", "String", "Cantidad", "Moneda",
                      "Entero", "Moneda"])
        self.gridVenta.enabled = True
        self.gridVenta.columnasHabilitadas = [0, 1, 2, 4, 5]
        self.gridVenta.textoVacio = "Todavía no hay productos en la venta.\nBuscá uno arriba y presioná Agregar."
        self.layoutPpal.addWidget(self.gridVenta)

        self.layoutTotales = QHBoxLayout()
        self.cboFormaPago = ComboFormapago()
        self.cboFormaPago.setCurrentIndex(self.cboFormaPago.findData("1"))
        # Solo lectura y NO deshabilitado. `enabled=False` llama
        # `setEnabled(False)`, y Qt pinta un widget deshabilitado con la
        # paleta de inactivo: el total salia gris, como un campo de
        # formulario que no se puede tocar, al lado del boton
        # "Emitir factura". Ademas no deja seleccionar el texto, y un
        # operador que necesita pasarlo por whatsapp no lo puede copiar.
        #
        # `setReadOnly(True)` conserva lo que importa: no se puede
        # escribir a mano el total de una venta.
        self.textTotal = EntradaTexto(tamanio=16, alineacion="DERECHA")
        self.textTotal.setReadOnly(True)
        self.textTotal.setText(_formato_importe(Decimal("0")))
        self.layoutTotales.addWidget(Etiqueta(texto="Forma de pago"))
        self.layoutTotales.addWidget(self.cboFormaPago)
        self.layoutTotales.addWidget(Etiqueta(texto="Total"))
        self.layoutTotales.addWidget(self.textTotal)
        self.layoutPpal.addLayout(self.layoutTotales)

        self.layoutBotones = QHBoxLayout()
        # Jerarquia de la barra de accion: emitir es lo que el usuario vino a
        # hacer, borrar un renglon es lo que no quiere tocar por error y cerrar
        # es salir sin hacer nada. Antes los tres se veian iguales.
        self.btnEmitir = Boton(texto="Emitir factura", imagen=icono('guardar'),
                               autodefault=False, estilo="primario")
        self.btnPresupuesto = Boton(texto="Guardar presupuesto", imagen=icono('nuevo'),
                                    autodefault=False)
        self.btnBorrar = Boton(texto="Borrar renglón", imagen=icono('borrar'),
                               tamanio=QSize(32, 32), autodefault=False, estilo="peligro")
        self.btnCerrar = BotonCerrarFormulario(autodefault=False)
        self.layoutBotones.addWidget(self.btnEmitir)
        self.layoutBotones.addWidget(self.btnPresupuesto)
        self.layoutBotones.addStretch(1)
        self.layoutBotones.addWidget(self.btnBorrar)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.layoutPpal.addLayout(self.layoutBotones)
