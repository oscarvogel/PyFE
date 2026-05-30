# coding=utf-8
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QCheckBox, QDialogButtonBox, QGridLayout, QHBoxLayout, QListWidget, QVBoxLayout

from libs.Botones import Boton, BotonCerrarFormulario
from libs.EntradaTexto import EntradaTexto
from libs.Etiquetas import Etiqueta, EtiquetaTitulo
from libs.Formulario import Formulario
from libs.Grillas import Grilla
from libs.GroupBox import Agrupacion
from libs.Utiles import imagen
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
        self.resize(420, 160)

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

        self.botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
        self.resize(520, 220)

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

        self.botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
        self.resize(520, 220)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto="Agregar articulo")
        self.layoutPpal.addWidget(self.lblTitulo)

        self.layoutDatos = QGridLayout()
        self.textNombre = EntradaTexto(placeholderText="Nombre")
        self.textPrecio = EntradaTexto(placeholderText="Precio")
        self.textIva = EntradaTexto(placeholderText="IVA")
        self.textCodigoBarra = EntradaTexto(placeholderText="Codigo de barras")
        self.textPrecio.setText("0.00")
        self.textIva.setText("21")
        self.layoutDatos.addWidget(Etiqueta(texto="Nombre"), 0, 0)
        self.layoutDatos.addWidget(self.textNombre, 0, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="Precio"), 1, 0)
        self.layoutDatos.addWidget(self.textPrecio, 1, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="IVA"), 2, 0)
        self.layoutDatos.addWidget(self.textIva, 2, 1)
        self.layoutDatos.addWidget(Etiqueta(texto="Codigo barras"), 3, 0)
        self.layoutDatos.addWidget(self.textCodigoBarra, 3, 1)
        self.layoutPpal.addLayout(self.layoutDatos)

        self.botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
    def __init__(self, clientes):
        Formulario.__init__(self)
        self.clientes = list(clientes)
        self.cliente = None
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("Seleccionar cliente")
        self.resize(560, 320)

        self.layoutPpal = QVBoxLayout(Form)
        self.lblTitulo = EtiquetaTitulo(texto="Seleccionar cliente")
        self.layoutPpal.addWidget(self.lblTitulo)

        self.listaClientes = QListWidget()
        for cliente in self.clientes:
            documento = cliente.cuit if str(cliente.cuit).replace("-", "").strip("0") else str(cliente.dni or "")
            self.listaClientes.addItem("{} - {} - {}".format(cliente.idcliente, cliente.nombre, documento))
        if self.clientes:
            self.listaClientes.setCurrentRow(0)
        self.listaClientes.itemDoubleClicked.connect(self.accept)
        self.layoutPpal.addWidget(self.listaClientes)

        self.botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        self.layoutPpal.addWidget(self.botones)

    def accept(self):
        fila = self.listaClientes.currentRow()
        if fila >= 0:
            self.cliente = self.clientes[fila]
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
        self.textArticulo = EntradaTexto(placeholderText="Codigo, nombre o codigo de barras")
        self.textCantidad = EntradaTexto(placeholderText="Cantidad")
        self.textCantidad.setText("1")
        self.btnAgregar = Boton(texto="Agregar", imagen=imagen("new.png"), tamanio=QSize(16, 16), autodefault=False)
        self.layoutArticulo.addWidget(Etiqueta(texto="Producto"), 0, 0)
        self.layoutArticulo.addWidget(self.textArticulo, 0, 1)
        self.layoutArticulo.addWidget(Etiqueta(texto="Cantidad"), 0, 2)
        self.layoutArticulo.addWidget(self.textCantidad, 0, 3)
        self.layoutArticulo.addWidget(self.btnAgregar, 0, 4)
        self.agrupaArticulo.setLayout(self.layoutArticulo)
        self.layoutPpal.addWidget(self.agrupaArticulo)

        self.gridVenta = Grilla(tamanio=10)
        self.gridVenta.ArmaCabeceras(cabeceras=["Cant.", "Codigo", "Detalle", "Unitario", "IVA", "SubTotal"])
        self.gridVenta.enabled = True
        self.gridVenta.columnasHabilitadas = [0, 1, 2, 3, 4]
        self.layoutPpal.addWidget(self.gridVenta)

        self.layoutTotales = QHBoxLayout()
        self.cboFormaPago = ComboFormapago()
        self.cboFormaPago.setCurrentIndex(self.cboFormaPago.findData("1"))
        self.textTotal = EntradaTexto(tamanio=16, enabled=False)
        self.textTotal.setText("0.00")
        self.layoutTotales.addWidget(Etiqueta(texto="Forma de pago"))
        self.layoutTotales.addWidget(self.cboFormaPago)
        self.layoutTotales.addWidget(Etiqueta(texto="Total"))
        self.layoutTotales.addWidget(self.textTotal)
        self.layoutPpal.addLayout(self.layoutTotales)

        self.layoutBotones = QHBoxLayout()
        self.btnEmitir = Boton(texto="Emitir factura", imagen=imagen("save.png"), autodefault=False)
        self.btnPresupuesto = Boton(texto="Guardar presupuesto", imagen=imagen("new.png"), autodefault=False)
        self.btnBorrar = Boton(texto="Borrar renglon", imagen=imagen("delete.png"), tamanio=QSize(32, 32), autodefault=False)
        self.btnCerrar = BotonCerrarFormulario(autodefault=False)
        self.layoutBotones.addWidget(self.btnEmitir)
        self.layoutBotones.addWidget(self.btnPresupuesto)
        self.layoutBotones.addWidget(self.btnBorrar)
        self.layoutBotones.addWidget(self.btnCerrar)
        self.layoutPpal.addLayout(self.layoutBotones)
