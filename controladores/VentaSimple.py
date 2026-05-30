# coding=utf-8
from decimal import Decimal

from controladores.ControladorBase import ControladorBase
from controladores.venta_simple_totales import RenglonVenta, calcular_totales
from libs import Ventanas
from libs.Utiles import LeerIni, inicializar_y_capturar_excepciones
from modelos.Articulos import Articulo
from vistas.VentaSimple import VentaSimpleView


class VentaSimpleController(ControladorBase):
    def __init__(self):
        super(VentaSimpleController, self).__init__()
        self.view = VentaSimpleView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.cerrarformulario)
        self.view.btnAgregar.clicked.connect(self.agregar_articulo)
        self.view.btnEmitir.clicked.connect(self.emitir_factura)

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

        cantidad = Decimal(self.view.textCantidad.text() or "1")
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

    def emitir_factura(self):
        Ventanas.showAlert("Venta", "La emision desde venta simple se conecta en la siguiente tarea")
