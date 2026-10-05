# coding=utf-8
"""Los controladores de stock: consultar, ajustar y auditar.

La logica esta en libs/stock.py. Aca esta lo que es de pantalla: que columnas
se ven, que mensaje se tira y a quien se le avisa. Un controlador que calcula
stock es un controlador que no se puede probar sin base y sin Qt.
"""

import xlsxwriter
from PyQt5.QtWidgets import QApplication

from controladores.ControladorBase import ControladorBase
from libs import Ventanas, stock
from libs.Utiles import (AbrirArchivo, GuardarArchivo, LeerIni,
                         inicializar_y_capturar_excepciones)
from modelos.Articulos import Articulo
from modelos.Cabfact import Cabfact
from modelos.MovStock import MovStock
from modelos.Remitos import Remito
from vistas.Stock import AjustesStockView, MovimientosStockView, StockView


# Que dice la columna 'Estado'. Sin esto habria que leer el numero y compararlo
# con el minimo de cabeza, y con el stock en negativo eso no se lee de un
# vistazo: -3 y 3 se ven casi igual.
SIN_STOCK = "Sin stock"
NEGATIVO = "Negativo"
FALTA = "Falta"
OK = "OK"
SIN_CONTROLAR = "Sin controlar"

COLUMNAS_EXCEL = ("Codigo", "Producto", "Unidad", "Stock", "Minimo", "Estado")
ANCHOS_EXCEL = (10, 32, 10, 14, 12, 14)


def estado_de(articulo, cantidad):
    if not stock.controla(articulo):
        return SIN_CONTROLAR
    if cantidad < 0:
        return NEGATIVO
    minimo = articulo.stockminimo
    if minimo and minimo > 0 and cantidad < minimo:
        return FALTA
    if cantidad == 0:
        return SIN_STOCK
    return OK


def _comprobante_de(movimiento):
    """El numero del comprobante que causo el movimiento, o vacio.

    Sin esto, el reporte de movimientos dice "VENTA -3" y no dice de que
    factura: un faltante de 3 no se puede explicar, y el reporte existe
    justamente para eso.
    """
    if movimiento.idcabfact_id:
        cabfact = Cabfact.get_or_none(
            Cabfact.idcabfact == movimiento.idcabfact_id)
        if cabfact:
            return "Factura {}".format(cabfact.numero)
    if movimiento.idremito_id:
        remito = Remito.get_or_none(Remito.idremito == movimiento.idremito_id)
        if remito:
            return "Remito {}".format(remito.numero)
    if movimiento.idpcabecera_id:
        return "Compra {}".format(movimiento.idpcabecera_id)
    return ""


class StockController(ControladorBase):

    def __init__(self):
        super(StockController, self).__init__()
        self.view = StockView()
        self.conectarWidgets()
        self.CargaStock()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnAjustar.clicked.connect(self.Ajustar)
        self.view.btnMovimientos.clicked.connect(self.VerMovimientos)
        self.view.btnMarcar.clicked.connect(self.MarcarProductos)
        self.view.btnExcel.clicked.connect(self.onClickExcel)
        self.view.txtBuscar.textChanged.connect(self.CargaStock)
        self.view.chkSoloFaltantes.stateChanged.connect(self.CargaStock)
        self.view.chkIncluirSinControlar.stateChanged.connect(self.CargaStock)
        self.view.gridDatos.doubleClicked.connect(self.Ajustar)

    def CargaStock(self, *args, **kwargs):
        solo_faltantes = self.view.chkSoloFaltantes.isChecked()
        incluir_sin_controlar = self.view.chkIncluirSinControlar.isChecked()
        busqueda = self.view.txtBuscar.text().strip().lower()

        # controlados=False trae tambien los productos sin marcar, y el
        # filtro los saca si la casilla esta sin tildar: asi el operador
        # decide si los ve, en vez de que desaparezcan sin aviso.
        stocks = stock.stock_de_todos(controlados=False)

        filas = []
        for a in Articulo.select().order_by(Articulo.nombre):
            if not stock.controla(a) and not incluir_sin_controlar:
                continue
            cantidad = stocks.get(a.idarticulo, stock.CERO)
            estado = estado_de(a, cantidad)
            if solo_faltantes and estado not in (FALTA, NEGATIVO, SIN_STOCK):
                continue
            if busqueda and busqueda not in (a.nombre or "").lower():
                continue
            filas.append([a.idarticulo, a.nombre, a.unidad_id,
                          str(cantidad), str(a.stockminimo), estado])

        self.view.Mostrar(filas)

    @inicializar_y_capturar_excepciones
    def Ajustar(self, *args, **kwargs):
        idarticulo = self.view.ProductoElegido()
        if idarticulo:
            try:
                idarticulo = int(idarticulo)
            except (TypeError, ValueError):
                idarticulo = None

        ventana = AjustesStockController(producto_id=idarticulo)
        ventana.view.exec_()
        # Al volver, el stock cambio: si no se recarga, la pantalla queda
        # mostrando el numero viejo y el operador Cree que no se grabo.
        self.CargaStock()

    @inicializar_y_capturar_excepciones
    def VerMovimientos(self, *args, **kwargs):
        idarticulo = self.view.ProductoElegido()
        try:
            idarticulo = int(idarticulo) if idarticulo else None
        except (TypeError, ValueError):
            idarticulo = None
        ventana = MovimientosStockController(producto_id=idarticulo)
        ventana.view.exec_()

    @inicializar_y_capturar_excepciones
    def MarcarProductos(self, *args, **kwargs):
        """Marca como controlados los que faltan, previa confirmacion.

        Es un cambio de comportamiento de TODOS esos articulos de una vez, asi
        que avisa y dice cuantos son. Marcar de a uno obliga a entrar veinte
        veces al ABM de Productos, y el que se saltea uno se da cuenta semanas
        despues, cuando el stock de ese producto no baja nunca.
        """
        pendientes = stock.sin_controlar()
        if not pendientes:
            Ventanas.showAlert("Stock", "Todos los productos ya controlan stock")
            return

        if not Ventanas.showConfirmation(
                "Marcar productos",
                "Se va a controlar el stock de {} producto/s.\n\n"
                "A partir de ahora cada venta de esos productos descuenta "
                "stock.".format(len(pendientes)),
                textoOk="Marcar", textoCancelar="Cancelar"):
            return

        stock.marcar_como_controlados()
        self.CargaStock()

    @inicializar_y_capturar_excepciones
    def onClickExcel(self, *args, **kwargs):
        archivo = GuardarArchivo(filter="*.XLSX", directory="excel/",
                                 filename="stock")
        if not archivo:
            return

        stocks = stock.stock_de_todos(controlados=False)
        libro = xlsxwriter.Workbook(str(archivo))
        try:
            hoja = libro.add_worksheet()
            for col, (titulo, ancho) in enumerate(zip(COLUMNAS_EXCEL,
                                                      ANCHOS_EXCEL)):
                hoja.write(0, col, titulo)
                hoja.set_column(col, col, ancho)

            fila = 1
            articulos = list(Articulo.select().order_by(Articulo.nombre))
            for n, a in enumerate(articulos, 1):
                # La barra de progreso no se ve mientras exporta una lista
                # corta, pero con 5.000 productos el 'no responde' es real.
                if n % 200 == 0:
                    QApplication.processEvents()
                cantidad = stocks.get(a.idarticulo, stock.CERO)
                hoja.write(fila, 0, a.idarticulo)
                hoja.write(fila, 1, a.nombre)
                hoja.write(fila, 2, a.unidad_id)
                hoja.write(fila, 3, float(cantidad))
                hoja.write(fila, 4, float(a.stockminimo or 0))
                hoja.write(fila, 5, estado_de(a, cantidad))
                fila += 1
        finally:
            libro.close()

        AbrirArchivo(str(archivo))


class AjustesStockController(ControladorBase):
    """Contar y corregir el stock de un producto.

    Es un controlador y no un boton en la vista porque tiene reglas que
    aplicar: la observacion es obligatoria y la cantidad no puede ser cero. Si
    estuvieran en la vista, el boton de Grabar estaria guardando movimientos
    sin explicacion, que es justo lo que hace impossible entender un faltante
    despues.
    """

    def __init__(self, producto_id=None, producto_observacion=None):
        super(AjustesStockController, self).__init__()
        self.view = AjustesStockView()
        self.conectarWidgets()
        if producto_id:
            self.CargaProducto(producto_id, producto_observacion)

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnGrabar.clicked.connect(self.Grabar)
        self.view.txtCantidad.textChanged.connect(self.previsualiza)
        self.view.txtProducto.textChanged.connect(self.alCambiarProducto)

    def alCambiarProducto(self, *args, **kwargs):
        """Si el operador escribe un codigo a mano, el stock actual y el
        nombre se recalculan. Si no, el formulario muestra el stock de otro
        producto y el ajuste se guarda sobre el que se creia."""
        texto = self.view.txtProducto.text().strip()
        if not texto.isdigit():
            return
        articulo = Articulo.get_or_none(Articulo.idarticulo == int(texto))
        if articulo is not None:
            self.view.lblNombre.setText(articulo.nombre or "")
            self.view.txtStockActual.setText(str(stock.stock_de(articulo)))
        self.previsualiza()

    def CargaProducto(self, idarticulo, nombre=None):
        articulo = Articulo.get_or_none(Articulo.idarticulo == idarticulo)
        if articulo is None:
            return
        self.view.txtProducto.setText(str(idarticulo))
        self.view.lblNombre.setText(nombre or articulo.nombre or "")
        actual = stock.stock_de(articulo)
        self.view.txtStockActual.setText(str(actual))
        self.previsualiza()

    def previsualiza(self, *args, **kwargs):
        """Muestra cuanto va a quedar, antes de grabar.

        Un ajuste es un numero que se suma o se resta a otro, y de cabeza es
        dificil saber si el signo quedo bien. Verlo evita el ajuste al reves.
        """
        actual = self._stock_actual()
        cantidad = self._cantidad()
        if cantidad is None:
            self.view.lblResultado.setText("")
            return
        self.view.lblResultado.setText(
            "El stock quedaría en {}".format(actual + cantidad))

    def _stock_actual(self):
        texto = self.view.txtStockActual.text().strip()
        try:
            from decimal import Decimal
            return Decimal(texto or 0)
        except Exception:
            return stock.CERO

    def _cantidad(self):
        texto = self.view.txtCantidad.text().strip()
        if not texto:
            return None
        try:
            from decimal import Decimal, InvalidOperation
            return Decimal(texto)
        except (InvalidOperation, ValueError):
            return None

    @inicializar_y_capturar_excepciones
    def Grabar(self, *args, **kwargs):
        idarticulo = self.view.txtProducto.text().strip()
        if not idarticulo.isdigit():
            Ventanas.showAlert("Stock", "Elegí un producto")
            return

        articulo = Articulo.get_or_none(Articulo.idarticulo == int(idarticulo))
        if articulo is None:
            Ventanas.showAlert("Stock", "El producto no existe")
            return
        if not stock.controla(articulo):
            Ventanas.showAlert(
                "Stock",
                "«{}» no tiene el control de stock activado.\n\n"
                "Activalo en Productos si querés que sus ventas lo "
                "descuenten.".format(articulo.nombre))
            return

        cantidad = self._cantidad()
        if cantidad is None:
            Ventanas.showAlert("Stock", "La cantidad tiene que ser un número")
            return
        if cantidad == 0:
            Ventanas.showAlert("Stock", "La cantidad no puede ser cero")
            return

        # Sin observacion no se puede arreglar despues. Un movimiento que
        # dice "ajuste" y nada mas no dice si fue un conteo, una rotura o una
        # carga mal hecha, y el siguiente que vea el faltante no tiene por
        # donde empezar.
        observacion = self.view.txtObservacion.text().strip()
        if not observacion:
            Ventanas.showAlert(
                "Stock",
                "Contá por qué se ajusta.\n\nSin eso, un faltante más "
                "adelante no tiene explicación.")
            return

        movimiento = stock.registra_ajuste(articulo.idarticulo, cantidad,
                                          observacion=observacion)
        if movimiento is None:
            Ventanas.showAlert("Stock", "No se pudo grabar el ajuste")
            return

        Ventanas.showAlert(
            "Stock",
            "«{}» quedó en {}".format(articulo.nombre,
                                      stock.stock_de(articulo.idarticulo)))
        self.view.Cerrar()


class MovimientosStockController(ControladorBase):
    """De donde sale cada numero de stock.

    Esta pantalla no agrega informacion: es la que permite entender un
    faltante. Sin ella, "faltan 3" no tiene respuesta, y la unica forma de
    averiguarlo es reconstruir a mano lo que paso mirando facturas una por
    una.
    """

    def __init__(self, producto_id=None):
        super(MovimientosStockController, self).__init__()
        self.view = MovimientosStockView()
        self.conectarWidgets()
        if producto_id:
            self.CargaProducto(producto_id)
        else:
            self.Buscar()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnBuscarProducto.clicked.connect(self.BuscarProducto)
        self.view.btnExcel.clicked.connect(self.onClickExcel)
        self.view.txtProducto.textChanged.connect(self.Buscar)

    def CargaProducto(self, idarticulo, nombre=None):
        """Producto elegido, por el buscador o escribiendo el codigo.

        Los dos argumentos los manda `_buscar_producto` (vistas/Stock.py). El
        nombre es opcional porque desde el buscador se lo pasa y desde
        `__init__` se lo pasa `CargaProducto(idarticulo)` solo, y un metodo que
        acepta uno solo revienta con TypeError cuando se aprieta F2.
        """
        articulo = Articulo.get_or_none(Articulo.idarticulo == idarticulo)
        self.view.txtProducto.setText(str(idarticulo))
        self.view.lblNombreProducto.setText(
            str(nombre) if nombre else (articulo.nombre if articulo else ""))
        self.Buscar()

    def BuscarProducto(self, *args, **kwargs):
        self.view.F2Producto(self.CargaProducto)

    @inicializar_y_capturar_excepciones
    def Buscar(self, *args, **kwargs):
        desde = self.view.desdeFecha.date().toPyDate()
        hasta = self.view.hastaFecha.date().toPyDate()
        producto = self.view.txtProducto.text().strip()

        consulta = MovStock.select().where(
            MovStock.fecha.between(desde, hasta))
        if producto.isdigit():
            consulta = consulta.where(
                MovStock.idarticulo == int(producto))
        consulta = consulta.order_by(MovStock.fecha.desc(),
                                     MovStock.idmovstock.desc())

        filas = []
        for m in consulta:
            filas.append([
                m.fecha, m.idarticulo_id,
                self._nombre(m.idarticulo_id),
                m.origen, str(m.cantidad),
                _comprobante_de(m),
                m.observacion,
                "Si" if m.anula_id else "",
            ])
        self.view.Mostrar(filas)

    def _nombre(self, idarticulo):
        articulo = Articulo.get_or_none(Articulo.idarticulo == idarticulo)
        return articulo.nombre if articulo else ""

    @inicializar_y_capturar_excepciones
    def onClickExcel(self, *args, **kwargs):
        archivo = GuardarArchivo(filter="*.XLSX", directory="excel/",
                                 filename="movimientos de stock")
        if not archivo:
            return

        libro = xlsxwriter.Workbook(str(archivo))
        try:
            hoja = libro.add_worksheet()
            titulos = ("Fecha", "Codigo", "Producto", "Origen", "Cantidad",
                       "Comprobante", "Observacion", "Anulado")
            for col, titulo in enumerate(titulos):
                hoja.write(0, col, titulo)
                hoja.set_column(col, col, 14 if col < 4 else 26)

            fila = 1
            for m in self._consulta():
                hoja.write(fila, 0, str(m.fecha))
                hoja.write(fila, 1, m.idarticulo_id)
                hoja.write(fila, 2, self._nombre(m.idarticulo_id))
                hoja.write(fila, 3, m.origen)
                hoja.write(fila, 4, float(m.cantidad))
                hoja.write(fila, 5, _comprobante_de(m))
                hoja.write(fila, 6, m.observacion)
                hoja.write(fila, 7, "Si" if m.anula_id else "")
                fila += 1
        finally:
            libro.close()

        AbrirArchivo(str(archivo))

    def _consulta(self):
        """La misma consulta que arma la grilla, para el Excel.

        Va en un metodo y no se reescribe: si el Excel y la pantalla tuvieran
        filtros distintos, el archivo exportado seria de otro periodo que el
        que se ve, y el que lo usa para conciliar no tendria por que sospechar
        nada.
        """
        desde = self.view.desdeFecha.date().toPyDate()
        hasta = self.view.hastaFecha.date().toPyDate()
        producto = self.view.txtProducto.text().strip()
        consulta = MovStock.select().where(
            MovStock.fecha.between(desde, hasta))
        if producto.isdigit():
            consulta = consulta.where(MovStock.idarticulo == int(producto))
        return consulta.order_by(MovStock.fecha.desc(),
                                 MovStock.idmovstock.desc())
