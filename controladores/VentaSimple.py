# coding=utf-8
from decimal import Decimal

from peewee import fn

from controladores.ControladorBase import ControladorBase
from controladores.venta_simple_totales import RenglonVenta, calcular_totales
from libs import Ventanas
from libs.Utiles import LeerIni, inicializar_y_capturar_excepciones
from modelos.Articulos import Articulo
from modelos.Clientes import Cliente
from vistas.VentaSimple import VentaSimpleView


class VentaSimpleController(ControladorBase):
    def __init__(self):
        super(VentaSimpleController, self).__init__()
        self.cliente = None
        self.view = VentaSimpleView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnAgregar.clicked.connect(self.agregar_articulo)
        self.view.btnEmitir.clicked.connect(self.emitir_factura)
        self.view.btnBorrar.clicked.connect(self.borrar_renglon)
        self.view.textArticulo.returnPressed.connect(self.agregar_articulo)
        self.view.textCantidad.returnPressed.connect(self.agregar_articulo)
        self.view.textCliente.returnPressed.connect(self.cargar_cliente_desde_busqueda)
        self.view.textCliente.editingFinished.connect(self.cargar_cliente_desde_busqueda)
        self.view.checkConsumidorFinal.stateChanged.connect(self.on_consumidor_final_changed)

    def on_consumidor_final_changed(self):
        if self.view.checkConsumidorFinal.isChecked():
            self.cliente = None
            self.view.textCliente.setText("")
            self.view.textDocumento.setText("")

    def cargar_cliente_desde_busqueda(self):
        busqueda = self.view.textCliente.text().strip()
        if not busqueda or self.view.checkConsumidorFinal.isChecked() and busqueda == "Consumidor Final":
            return

        cliente = self.buscar_cliente(busqueda)
        if not cliente:
            Ventanas.showAlert("Venta", "Cliente no encontrado")
            return

        self.cliente = cliente
        self.view.checkConsumidorFinal.setChecked(False)
        self.view.textCliente.setText("{} - {}".format(cliente.idcliente, cliente.nombre))
        documento = cliente.cuit if str(cliente.cuit).replace("-", "").strip("0") else str(cliente.dni or "")
        self.view.textDocumento.setText(documento)

    def buscar_cliente(self, busqueda):
        texto = str(busqueda).strip()
        posible_id = texto.split(" - ", 1)[0]

        if posible_id.isdigit():
            try:
                return Cliente.get_by_id(posible_id)
            except Exception:
                pass

        cuit = texto.replace("-", "").replace(" ", "")
        try:
            cliente = Cliente.select().where(Cliente.cuit == texto).first()
            if cliente:
                return cliente
            cliente = Cliente.select().where(fn.REPLACE(Cliente.cuit, "-", "") == cuit).first()
            if cliente:
                return cliente
        except Exception:
            pass

        if texto.isdigit():
            try:
                cliente = Cliente.select().where(Cliente.dni == int(texto)).first()
                if cliente:
                    return cliente
            except Exception:
                pass

        return Cliente.select().where(Cliente.nombre.contains(texto)).first()

    @inicializar_y_capturar_excepciones
    def agregar_articulo(self, *args, **kwargs):
        busqueda = self.view.textArticulo.text().strip()
        if not busqueda:
            Ventanas.showAlert("Venta", "Ingrese un producto")
            return

        articulo = self.buscar_articulo(busqueda)
        if not articulo:
            Ventanas.showAlert("Venta", "Producto no encontrado")
            return

        try:
            cantidad = Decimal(self.view.textCantidad.text() or "1")
        except Exception:
            Ventanas.showAlert("Venta", "La cantidad debe ser numerica")
            return

        if cantidad <= 0:
            Ventanas.showAlert("Venta", "La cantidad debe ser mayor a cero")
            return

        precio = Decimal(str(articulo.preciopub))
        iva = Decimal(str(articulo.tipoiva.iva))
        subtotal = cantidad * precio

        self.view.gridVenta.AgregaItem(items=[
            str(cantidad),
            str(articulo.idarticulo),
            articulo.nombre,
            str(precio),
            str(iva),
            str(subtotal),
        ])
        self.view.textArticulo.setText("")
        self.view.textCantidad.setText("1")
        self.recalcular_total()

    def buscar_articulo(self, busqueda):
        try:
            return Articulo.get_by_id(busqueda)
        except Exception:
            pass

        try:
            return Articulo.get(Articulo.codbarra == busqueda)
        except Exception:
            pass

        return Articulo.select().where(Articulo.nombre.contains(busqueda)).first()

    def obtener_renglones(self):
        renglones = []
        for fila in range(self.view.gridVenta.rowCount()):
            renglones.append(RenglonVenta(
                codigo=str(self.view.gridVenta.ObtenerItem(fila=fila, col="Codigo")),
                detalle=str(self.view.gridVenta.ObtenerItem(fila=fila, col="Detalle")),
                cantidad=Decimal(str(self.view.gridVenta.ObtenerItem(fila=fila, col="Cant."))),
                precio_unitario=Decimal(str(self.view.gridVenta.ObtenerItem(fila=fila, col="Unitario"))),
                iva=Decimal(str(self.view.gridVenta.ObtenerItem(fila=fila, col="IVA"))),
            ))
        return renglones

    def recalcular_total(self):
        responsable_inscripto = int(LeerIni(clave="cat_iva", key="WSFEv1")) == 1
        totales = calcular_totales(self.obtener_renglones(), responsable_inscripto)
        self.view.textTotal.setText(str(totales.total))

    def borrar_renglon(self):
        fila = self.view.gridVenta.currentRow()
        if fila >= 0:
            self.view.gridVenta.removeRow(fila)
            self.recalcular_total()

    def emitir_factura(self):
        renglones = self.obtener_renglones()
        if not renglones:
            Ventanas.showAlert("Venta", "Agregue al menos un producto")
            return

        from controladores.Facturas import FacturaController

        factura = FacturaController()
        cliente_id = None
        if not self.view.checkConsumidorFinal.isChecked():
            if not self.cliente:
                self.cargar_cliente_desde_busqueda()
            if not self.cliente:
                Ventanas.showAlert("Venta", "Seleccione un cliente valido")
                return
            cliente_id = self.cliente.idcliente

        factura.cargar_venta_simple(
            cliente_id=cliente_id,
            renglones=renglones,
            forma_pago_id=self.view.cboFormaPago.text(),
        )
        factura.exec_()
