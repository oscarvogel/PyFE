# coding=utf-8
from decimal import Decimal

from peewee import fn
from PyQt5.QtWidgets import QDialog, QMessageBox

from controladores.ControladorBase import ControladorBase
from controladores.venta_simple_totales import RenglonVenta, calcular_totales
from libs import Ventanas
from libs.Utiles import LeerIni, inicializar_y_capturar_excepciones
from modelos.Articulos import Articulo
from modelos.Clientes import Cliente
from vistas.VentaSimple import VentaSimpleAltaArticuloDialog, VentaSimpleAltaClienteDialog, \
    VentaSimpleCantidadPrecioDialog, VentaSimpleSeleccionClienteDialog, VentaSimpleView


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

        cliente = self.resolver_cliente_desde_busqueda(busqueda)
        if not cliente:
            if not self.confirmar_alta("Venta", "Cliente no encontrado. Desea agregarlo?"):
                return
            cliente = self.solicitar_alta_cliente(busqueda)
            if not cliente:
                return

        self.cargar_cliente_en_vista(cliente)

    def confirmar_alta(self, titulo, mensaje):
        respuesta = QMessageBox.question(
            self.view,
            titulo,
            mensaje,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        return respuesta == QMessageBox.Yes

    def cargar_cliente_en_vista(self, cliente):
        self.cliente = cliente
        self.view.checkConsumidorFinal.setChecked(False)
        self.view.textCliente.setText("{} - {}".format(cliente.idcliente, cliente.nombre))
        documento = cliente.cuit if str(cliente.cuit).replace("-", "").strip("0") else str(cliente.dni or "")
        self.view.textDocumento.setText(documento)

    def solicitar_alta_cliente(self, busqueda):
        dialogo = VentaSimpleAltaClienteDialog(busqueda)
        dialogo.exec_()
        if dialogo.result() != QDialog.Accepted:
            return None

        datos = dialogo.valores()
        nombre = datos["nombre"]
        if not nombre:
            Ventanas.showAlert("Venta", "Ingrese el nombre del cliente")
            return None

        documento = datos["documento"].replace("-", "").replace(" ", "")
        cuit = ""
        dni = 0
        if documento:
            if len(documento) == 11:
                cuit = datos["documento"]
            elif documento.isdigit():
                dni = int(documento)

        return Cliente.create(
            nombre=nombre,
            domicilio=datos["domicilio"],
            localidad=1,
            cuit=cuit,
            dni=dni,
            tipodocu=0,
            tiporesp=3,
            formapago=1,
            percepcion=1,
        )

    def resolver_cliente_desde_busqueda(self, busqueda):
        clientes = self.buscar_clientes(busqueda)
        if not clientes:
            return None
        if len(clientes) == 1:
            return clientes[0]
        return self.seleccionar_cliente(clientes)

    def seleccionar_cliente(self, clientes):
        dialogo = VentaSimpleSeleccionClienteDialog(clientes)
        dialogo.exec_()
        if dialogo.result() != QDialog.Accepted:
            return None
        return dialogo.cliente

    def buscar_cliente(self, busqueda):
        clientes = self.buscar_clientes(busqueda)
        return clientes[0] if clientes else None

    def buscar_clientes(self, busqueda):
        texto = str(busqueda).strip()
        posible_id = texto.split(" - ", 1)[0]

        if posible_id.isdigit():
            try:
                return [Cliente.get_by_id(posible_id)]
            except Exception:
                pass

        cuit = texto.replace("-", "").replace(" ", "")
        try:
            cliente = Cliente.select().where(Cliente.cuit == texto).first()
            if cliente:
                return [cliente]
            cliente = Cliente.select().where(fn.REPLACE(Cliente.cuit, "-", "") == cuit).first()
            if cliente:
                return [cliente]
        except Exception:
            pass

        if texto.isdigit():
            try:
                cliente = Cliente.select().where(Cliente.dni == int(texto)).first()
                if cliente:
                    return [cliente]
            except Exception:
                pass

        return list(Cliente.select().where(Cliente.nombre.contains(texto)).order_by(Cliente.nombre))

    @inicializar_y_capturar_excepciones
    def agregar_articulo(self, *args, **kwargs):
        busqueda = self.view.textArticulo.text().strip()
        if not busqueda:
            Ventanas.showAlert("Venta", "Ingrese un producto")
            return

        articulo = self.buscar_articulo(busqueda)
        if not articulo:
            if not self.confirmar_alta("Venta", "Producto no encontrado. Desea agregarlo?"):
                return
            articulo = self.solicitar_alta_articulo(busqueda)
            if not articulo:
                return

        try:
            cantidad = Decimal(self.view.textCantidad.text() or "1")
        except Exception:
            Ventanas.showAlert("Venta", "La cantidad debe ser numerica")
            return

        if cantidad <= 0:
            Ventanas.showAlert("Venta", "La cantidad debe ser mayor a cero")
            return

        datos_renglon = self.solicitar_cantidad_y_precio(articulo, cantidad)
        if not datos_renglon:
            return

        cantidad, precio = datos_renglon
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

    def solicitar_cantidad_y_precio(self, articulo, cantidad):
        dialogo = VentaSimpleCantidadPrecioDialog(
            articulo=articulo,
            cantidad=cantidad,
            precio=Decimal(str(articulo.preciopub)),
        )
        dialogo.exec_()
        if dialogo.result() != QDialog.Accepted:
            return None

        cantidad_texto, precio_texto = dialogo.valores()
        try:
            cantidad = Decimal(cantidad_texto or "1")
            precio = Decimal(precio_texto or "0")
        except Exception:
            Ventanas.showAlert("Venta", "Cantidad y precio deben ser numericos")
            return None

        if cantidad <= 0:
            Ventanas.showAlert("Venta", "La cantidad debe ser mayor a cero")
            return None
        if precio < 0:
            Ventanas.showAlert("Venta", "El precio no puede ser negativo")
            return None

        return cantidad, precio

    def solicitar_alta_articulo(self, busqueda):
        dialogo = VentaSimpleAltaArticuloDialog(busqueda)
        dialogo.exec_()
        if dialogo.result() != QDialog.Accepted:
            return None

        datos = dialogo.valores()
        nombre = datos["nombre"]
        if not nombre:
            Ventanas.showAlert("Venta", "Ingrese el nombre del articulo")
            return None

        try:
            precio = Decimal(datos["precio"] or "0")
            iva = Decimal(datos["iva"] or "21")
        except Exception:
            Ventanas.showAlert("Venta", "Precio e IVA deben ser numericos")
            return None

        if precio < 0:
            Ventanas.showAlert("Venta", "El precio no puede ser negativo")
            return None

        tipoiva = "01" if iva == Decimal("21") else "01"
        return Articulo.create(
            nombre=nombre,
            nombreticket=nombre[:30],
            preciopub=precio,
            costo=precio,
            tipoiva=tipoiva,
            codbarra=datos["codbarra"],
        )

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
